from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal

import pytest
from sqlalchemy import select

from middleware.broker_adapters.base import BrokerOrderResult
from middleware.domain.enums import OrderStatus
from middleware.domain.events import BrokerOrderRequestPayload, TradingViewWebhookPayload
from middleware.infra.db import get_session_local
from middleware.infra.models import ExecutionReport, Order, SignalEvent, Tranche
from middleware.infra.settings import MiddlewareSettings, settings
from middleware.risk.binance_filters import BinanceSymbolRules
from middleware.services.trading_service import TradingService


class SimulatedProcessCrash(BaseException):
    """Interrupt control flow without translating a crash into a broker failure."""


@dataclass
class DurableDispatchBroker:
    name: str = "BINANCE_SPOT"
    crash_stage: str | None = None
    on_dispatch: Callable[[BrokerOrderRequestPayload], None] | None = None
    on_result: Callable[[BrokerOrderRequestPayload], None] | None = None
    requests: list[BrokerOrderRequestPayload] = field(default_factory=list)
    accepted: dict[str, BrokerOrderRequestPayload] = field(default_factory=dict)
    recovery_calls: int = 0

    def get_symbol_rules(self, symbol: str) -> BinanceSymbolRules:
        return BinanceSymbolRules(
            symbol=symbol.upper(),
            status="TRADING",
            base_asset=symbol.upper().removesuffix("USDT"),
            quote_asset="USDT",
            tick_size=Decimal("0.01"),
            min_price=Decimal("0.01"),
            max_price=Decimal("1000000"),
            step_size=Decimal("0.000001"),
            min_qty=Decimal("0.000001"),
            max_qty=Decimal("1000"),
            min_notional=Decimal("5"),
        )

    def submit_limit_order(self, payload: BrokerOrderRequestPayload) -> BrokerOrderResult:
        self.requests.append(payload)
        # A separate connection must see the intent and its audit trail before this write.
        with get_session_local()() as independent_session:
            order = independent_session.scalar(
                select(Order).where(Order.client_order_id == payload.client_order_id)
            )
            assert order is not None
            assert order.status == OrderStatus.SUBMITTED.value
            reports = independent_session.scalars(
                select(ExecutionReport).where(ExecutionReport.order_id == order.id)
            ).all()
            assert [report.status for report in reports] == [
                "received",
                "validated",
                "submitted",
            ]
        if self.on_dispatch is not None:
            self.on_dispatch(payload)
        if self.crash_stage == "before_acceptance":
            raise SimulatedProcessCrash()
        self.accepted[payload.client_order_id] = payload
        if self.crash_stage == "after_acceptance":
            raise SimulatedProcessCrash()
        if self.on_result is not None:
            self.on_result(payload)
        return self._filled_result(payload)

    def get_order_by_client_id(self, symbol: str, client_order_id: str) -> BrokerOrderResult:
        self.recovery_calls += 1
        payload = self.accepted.get(client_order_id)
        if payload is None:
            return BrokerOrderResult(
                accepted=False,
                status=OrderStatus.UNKNOWN,
                client_order_id=client_order_id,
                execution_uncertain=True,
                message="no confirmed broker order; manual investigation required",
            )
        assert payload.symbol == symbol
        return self._filled_result(payload)

    @staticmethod
    def _filled_result(payload: BrokerOrderRequestPayload) -> BrokerOrderResult:
        return BrokerOrderResult(
            accepted=True,
            status=OrderStatus.FILLED,
            broker_order_id=f"BROKER-{payload.client_order_id}",
            client_order_id=payload.client_order_id,
            filled_quantity=payload.quantity,
            avg_fill_price=payload.limit_price,
            message="confirmed fill",
        )


def _process(
    broker: DurableDispatchBroker,
    payload: TradingViewWebhookPayload,
    *,
    cfg: MiddlewareSettings = settings,
    bypass: bool = False,
):
    with get_session_local()() as session:
        return TradingService(session=session, cfg=cfg, broker_client=broker).process_webhook(
            payload, bypass_idempotency=bypass
        )


def _recover(broker: DurableDispatchBroker, order_id: int):
    with get_session_local()() as session:
        return TradingService(session=session, cfg=settings, broker_client=broker).recover_order(
            order_id
        )


@pytest.mark.parametrize("crash_stage", ["before_acceptance", "after_acceptance", "accounting"])
def test_dispatch_survives_crash_without_replay_resubmission(
    sample_buy_payload, monkeypatch, crash_stage
):
    settings.binance_buy_quote_amount_usdt = Decimal("100")
    settings.buy_bps = 0
    payload = TradingViewWebhookPayload.model_validate(sample_buy_payload)
    broker = DurableDispatchBroker(crash_stage=crash_stage)
    with get_session_local()() as session:
        service = TradingService(session=session, cfg=settings, broker_client=broker)
        if crash_stage == "accounting":
            record_result = service._record_broker_result

            def crash_after_accounting(*args, **kwargs):
                record_result(*args, **kwargs)
                raise SimulatedProcessCrash()

            monkeypatch.setattr(service, "_record_broker_result", crash_after_accounting)
        with pytest.raises(SimulatedProcessCrash):
            service.process_webhook(payload)
        assert session.in_transaction() is False

    duplicate = _process(broker, payload)
    assert duplicate.duplicate is True
    assert duplicate.status == OrderStatus.SUBMITTED
    assert len(broker.requests) == 1
    with get_session_local()() as session:
        assert session.scalars(select(Tranche)).all() == []

    first_recovery = _recover(broker, duplicate.order_id)
    second_recovery = _recover(broker, duplicate.order_id)
    expected_status = (
        OrderStatus.UNKNOWN if crash_stage == "before_acceptance" else OrderStatus.FILLED
    )
    assert first_recovery.status == second_recovery.status == expected_status
    assert len(broker.requests) == 1
    assert broker.recovery_calls == 2
    with get_session_local()() as session:
        tranches = session.scalars(select(Tranche)).all()
        if crash_stage == "before_acceptance":
            assert tranches == []
        else:
            assert len(tranches) == 1
            assert tranches[0].remaining_quantity == Decimal("0.002")


def test_during_dispatch_same_scope_symbol_is_reserved_and_other_work_can_progress(
    sample_buy_payload,
):
    settings.binance_buy_quote_amount_usdt = Decimal("100")
    settings.buy_bps = 0
    payload = TradingViewWebhookPayload.model_validate(sample_buy_payload)
    broker = DurableDispatchBroker()
    competing_responses = []

    def inspect_concurrent_requests(request: BrokerOrderRequestPayload) -> None:
        broker.on_dispatch = None
        competing_responses.append(_process(broker, payload))
        competing_responses.append(_process(broker, payload.model_copy(update={"barIndex": 20})))
        competing_responses.append(
            _process(
                broker,
                payload.model_copy(update={"symbol": "ETHUSDT", "ticker": "ETHUSDT"}),
            )
        )
        competing_responses.append(
            _process(
                broker,
                payload,
                cfg=settings.model_copy(update={"inventory_account_id": "independent-account"}),
            )
        )

    broker.on_dispatch = inspect_concurrent_requests
    original = _process(broker, payload)
    duplicate, conflict, other_symbol, other_scope = competing_responses
    assert original.status == OrderStatus.FILLED
    assert duplicate.duplicate is True
    assert duplicate.order_id == original.order_id
    assert duplicate.status == OrderStatus.SUBMITTED
    assert conflict.status == OrderStatus.REJECTED
    assert "must be recovered" in conflict.risk_reason
    assert other_symbol.status == other_scope.status == OrderStatus.FILLED
    assert len(broker.requests) == 3
    after_completion = _process(broker, payload.model_copy(update={"barIndex": 21}))
    assert after_completion.status == OrderStatus.FILLED


def test_original_replay_remains_idempotent_after_an_explicit_bypass(sample_buy_payload):
    payload = TradingViewWebhookPayload.model_validate(sample_buy_payload)
    broker = DurableDispatchBroker()

    original = _process(broker, payload)
    authorized_replay = _process(broker, payload, bypass=True)
    duplicate = _process(broker, payload)

    assert original.status == authorized_replay.status == OrderStatus.FILLED
    assert authorized_replay.order_id != original.order_id
    assert authorized_replay.client_order_id != original.client_order_id
    assert duplicate.duplicate is True
    assert duplicate.order_id == original.order_id
    assert len(broker.requests) == 2
    with get_session_local()() as session:
        event = session.get(SignalEvent, original.signal_event_id)
        assert len(event.orders) == 2


def test_concurrent_recovery_before_submit_response_does_not_double_inventory(sample_buy_payload):
    settings.binance_buy_quote_amount_usdt = Decimal("100")
    settings.buy_bps = 0
    payload = TradingViewWebhookPayload.model_validate(sample_buy_payload)
    broker = DurableDispatchBroker()

    def recover_before_original_response(request: BrokerOrderRequestPayload) -> None:
        with get_session_local()() as session:
            order = session.scalar(
                select(Order).where(Order.client_order_id == request.client_order_id)
            )
            order_id = order.id
        assert _recover(broker, order_id).status == OrderStatus.FILLED

    broker.on_result = recover_before_original_response
    original = _process(broker, payload)

    assert original.status == OrderStatus.FILLED
    assert len(broker.requests) == 1
    assert broker.recovery_calls == 1
    with get_session_local()() as session:
        tranches = session.scalars(select(Tranche)).all()
        assert len(tranches) == 1
        assert tranches[0].remaining_quantity == Decimal("0.002")
