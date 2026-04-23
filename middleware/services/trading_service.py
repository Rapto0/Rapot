from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from middleware.broker_adapters.base import BrokerClient
from middleware.domain.constants import BUY_SIGNAL_CODES
from middleware.domain.enums import OrderStatus, Side
from middleware.domain.events import (
    BrokerOrderRequestPayload,
    ProcessSignalResponse,
    SimulateFillRequest,
    TradingViewWebhookPayload,
)
from middleware.infra.logging import get_logger
from middleware.infra.models import Order
from middleware.infra.settings import MiddlewareSettings
from middleware.repositories.execution_report_repository import ExecutionReportRepository
from middleware.repositories.order_repository import OrderRepository
from middleware.repositories.signal_repository import SignalRepository
from middleware.repositories.tranche_repository import TrancheRepository
from middleware.risk.checks import BuyRiskInput, RiskEngine, SellRiskInput
from middleware.risk.sizing import compute_buy_lots, compute_signal_budget
from middleware.risk.tick import TickPolicy

logger = get_logger(__name__)


@dataclass(slots=True)
class _OrderIntent:
    symbol: str
    side: Side
    signal_code: str
    requested_lots: int
    limit_price: Decimal
    budget_tl: Decimal | None
    target_tranche_id: int | None


class TradingService:
    def __init__(
        self,
        *,
        session: Session,
        cfg: MiddlewareSettings,
        broker_client: BrokerClient,
    ) -> None:
        self.session = session
        self.cfg = cfg
        self.broker_client = broker_client
        self.signal_repo = SignalRepository(session)
        self.order_repo = OrderRepository(session)
        self.tranche_repo = TrancheRepository(session)
        self.execution_repo = ExecutionReportRepository(session)
        self.risk = RiskEngine(cfg)
        self.tick_policy = TickPolicy(
            default_tick=cfg.default_tick_size,
            symbol_overrides=cfg.symbol_tick_overrides,
        )

    def process_webhook(
        self,
        payload: TradingViewWebhookPayload,
        *,
        bypass_idempotency: bool = False,
    ) -> ProcessSignalResponse:
        event_hash = self.signal_repo.build_event_hash(payload)
        if not bypass_idempotency:
            existing = self.signal_repo.get_by_event_hash(event_hash)
            if existing:
                existing_order = self.order_repo.get_by_signal_event_id(existing.id)
                return ProcessSignalResponse(
                    signal_event_id=existing.id,
                    order_id=existing_order.id if existing_order else None,
                    duplicate=True,
                    status=(
                        OrderStatus(existing_order.status)
                        if existing_order
                        and existing_order.status in OrderStatus._value2member_map_
                        else None
                    ),
                    message="duplicate signal ignored",
                    broker_order_id=existing_order.broker_order_id if existing_order else None,
                )

        idempotency_key = (
            event_hash
            if not bypass_idempotency
            else f"{event_hash}:replay:{int(datetime.now(UTC).timestamp() * 1000)}"
        )
        signal_event = self.signal_repo.create(payload, event_hash=event_hash)
        order_intent = self._build_intent(payload)
        order = self.order_repo.create(
            signal_event_id=signal_event.id,
            idempotency_key=idempotency_key,
            symbol=order_intent.symbol,
            side=order_intent.side,
            signal_code=order_intent.signal_code,
            requested_lots=order_intent.requested_lots,
            limit_price=order_intent.limit_price,
            budget_tl=order_intent.budget_tl,
            status=OrderStatus.RECEIVED,
            broker_name=self.broker_client.name,
            mode=self.cfg.execution_mode.value,
            target_tranche_id=order_intent.target_tranche_id,
        )
        self.execution_repo.add(
            order_id=order.id,
            event_type="lifecycle",
            status=OrderStatus.RECEIVED.value,
            message="order received",
            payload={"event_hash": event_hash},
        )

        risk_reason = self._run_risk(payload=payload, order_intent=order_intent)
        if risk_reason:
            self.order_repo.set_status(order, OrderStatus.REJECTED, rejection_reason=risk_reason)
            self.execution_repo.add(
                order_id=order.id,
                event_type="risk",
                status=OrderStatus.REJECTED.value,
                message=risk_reason,
                payload={"symbol": payload.symbol, "signalCode": payload.signalCode},
            )
            self.session.commit()
            return ProcessSignalResponse(
                signal_event_id=signal_event.id,
                order_id=order.id,
                duplicate=False,
                status=OrderStatus.REJECTED,
                message="signal rejected by risk checks",
                risk_reason=risk_reason,
            )

        self.order_repo.set_status(order, OrderStatus.VALIDATED)
        self.execution_repo.add(
            order_id=order.id,
            event_type="lifecycle",
            status=OrderStatus.VALIDATED.value,
            message="risk checks passed",
        )

        self.order_repo.set_status(order, OrderStatus.SUBMITTED)
        self.execution_repo.add(
            order_id=order.id,
            event_type="lifecycle",
            status=OrderStatus.SUBMITTED.value,
            message="dispatching to broker adapter",
        )

        broker_result = self.broker_client.submit_limit_order(
            BrokerOrderRequestPayload(
                symbol=order.symbol,
                side=Side(order.side),
                lots=order.requested_lots,
                limit_price=order.limit_price,
                signal_code=order.signal_code,
                idempotency_key=order.idempotency_key,
                metadata={
                    "signal_event_id": signal_event.id,
                    "source": payload.source,
                    "timeframe": payload.timeframe,
                    "is_realtime": payload.isRealtime,
                },
            )
        )

        if not broker_result.accepted:
            final_status = broker_result.status if broker_result.status else OrderStatus.FAILED
            self.order_repo.set_status(
                order,
                final_status,
                rejection_reason=broker_result.message or "broker rejected order",
            )
            order.broker_order_id = broker_result.broker_order_id
            self.execution_repo.add(
                order_id=order.id,
                event_type="broker",
                status=final_status.value,
                message=broker_result.message,
                payload=broker_result.raw_payload,
            )
            self.session.commit()
            return ProcessSignalResponse(
                signal_event_id=signal_event.id,
                order_id=order.id,
                duplicate=False,
                status=final_status,
                message="broker rejected order",
                risk_reason=order.rejection_reason,
                broker_order_id=broker_result.broker_order_id,
            )

        self.order_repo.apply_broker_ack(
            order,
            status=broker_result.status,
            broker_order_id=broker_result.broker_order_id,
            filled_lots=broker_result.filled_lots,
            avg_fill_price=broker_result.avg_fill_price,
        )
        self.execution_repo.add(
            order_id=order.id,
            event_type="broker",
            status=broker_result.status.value,
            message=broker_result.message,
            payload=broker_result.raw_payload,
        )

        if broker_result.filled_lots > 0 and broker_result.avg_fill_price is not None:
            self._apply_fill(
                order=order,
                fill_lots=broker_result.filled_lots,
                fill_price=broker_result.avg_fill_price,
            )

        self.session.commit()
        return ProcessSignalResponse(
            signal_event_id=signal_event.id,
            order_id=order.id,
            duplicate=False,
            status=OrderStatus(order.status),
            message="signal processed",
            broker_order_id=order.broker_order_id,
        )

    def replay_signal(
        self,
        payload: TradingViewWebhookPayload,
        *,
        bypass_idempotency: bool,
    ) -> ProcessSignalResponse:
        return self.process_webhook(payload, bypass_idempotency=bypass_idempotency)

    def simulate_fill(self, request: SimulateFillRequest) -> Order:
        order = self.order_repo.get(request.order_id)
        if order is None:
            raise ValueError(f"order not found: {request.order_id}")
        if order.broker_name != "MOCK":
            raise ValueError("simulate-fill is allowed only for MOCK broker")
        if order.status not in {
            OrderStatus.SUBMITTED.value,
            OrderStatus.ACKNOWLEDGED.value,
            OrderStatus.PARTIALLY_FILLED.value,
        }:
            raise ValueError("order is not in fillable state")

        remaining = max(0, int(order.requested_lots) - int(order.filled_lots))
        if remaining <= 0:
            raise ValueError("order has no remaining lots")

        requested_fill = request.filled_lots if request.filled_lots is not None else remaining
        fill_lots = min(remaining, int(requested_fill))
        fill_price = request.fill_price if request.fill_price is not None else order.limit_price

        total_after = int(order.filled_lots) + fill_lots
        next_status = (
            OrderStatus.FILLED
            if total_after >= int(order.requested_lots)
            else OrderStatus.PARTIALLY_FILLED
        )
        self.order_repo.apply_broker_ack(
            order,
            status=next_status,
            broker_order_id=order.broker_order_id,
            filled_lots=fill_lots,
            avg_fill_price=fill_price,
        )
        self.execution_repo.add(
            order_id=order.id,
            event_type="simulate_fill",
            status=next_status.value,
            message="admin simulate fill",
            payload={"fill_lots": fill_lots, "fill_price": str(fill_price)},
        )

        self._apply_fill(order=order, fill_lots=fill_lots, fill_price=fill_price)
        self.session.commit()
        return order

    def list_positions(self, symbol: str | None = None) -> list[dict]:
        if symbol:
            tranches = self.tranche_repo.list_open_tranches(symbol=symbol)
            if not tranches:
                return []
            weighted_num = sum(
                (Decimal(t.entry_price) * int(t.remaining_lots) for t in tranches), Decimal("0")
            )
            total_lots = sum(int(t.remaining_lots) for t in tranches)
            weighted_avg = weighted_num / Decimal(total_lots) if total_lots > 0 else None
            return [
                {
                    "symbol": symbol.upper(),
                    "open_tranche_count": len(tranches),
                    "total_remaining_lots": total_lots,
                    "weighted_avg_entry_price": weighted_avg,
                }
            ]
        return self.tranche_repo.list_positions()

    def list_tranches(self, symbol: str | None = None):
        return self.tranche_repo.list_open_tranches(symbol=symbol)

    def list_orders(self, *, limit: int = 100, symbol: str | None = None):
        return self.order_repo.list_orders(limit=limit, symbol=symbol)

    def list_signals(self, *, limit: int = 100, symbol: str | None = None):
        return self.signal_repo.list_signals(limit=limit, symbol=symbol)

    def _build_intent(self, payload: TradingViewWebhookPayload) -> _OrderIntent:
        symbol = payload.symbol.upper()
        if payload.side == Side.BUY:
            multiplier = self.cfg.signal_multipliers[payload.signalCode]
            budget = compute_signal_budget(self.cfg.base_budget_tl, multiplier)
            limit_price = self.tick_policy.buy_limit_price(symbol, payload.price, self.cfg.buy_bps)
            lots = compute_buy_lots(budget, limit_price)
            return _OrderIntent(
                symbol=symbol,
                side=payload.side,
                signal_code=payload.signalCode,
                requested_lots=lots,
                limit_price=limit_price,
                budget_tl=budget,
                target_tranche_id=None,
            )

        target = self.tranche_repo.oldest_open(symbol)
        limit_price = self.tick_policy.sell_limit_price(symbol, payload.price, self.cfg.sell_bps)
        lots = int(target.remaining_lots) if target else 0
        return _OrderIntent(
            symbol=symbol,
            side=payload.side,
            signal_code=payload.signalCode,
            requested_lots=lots,
            limit_price=limit_price,
            budget_tl=None,
            target_tranche_id=target.id if target else None,
        )

    def _run_risk(
        self, *, payload: TradingViewWebhookPayload, order_intent: _OrderIntent
    ) -> str | None:
        orders_today = self.order_repo.count_orders_today()
        realized_pnl_today = self.order_repo.get_realized_pnl_today()
        try:
            if payload.side == Side.BUY:
                open_count = self.tranche_repo.count_open(payload.symbol)
                symbol_exposure = self.tranche_repo.get_symbol_exposure_tl(payload.symbol)
                self.risk.validate_buy(
                    BuyRiskInput(
                        symbol=payload.symbol,
                        signal_code=payload.signalCode,
                        side=payload.side,
                        buy_lots=order_intent.requested_lots,
                        buy_limit_price=order_intent.limit_price,
                        open_tranche_count=open_count,
                        symbol_exposure_tl=symbol_exposure,
                        orders_today=orders_today,
                        realized_pnl_today=realized_pnl_today,
                    )
                )
            else:
                self.risk.validate_sell(
                    SellRiskInput(
                        symbol=payload.symbol,
                        signal_code=payload.signalCode,
                        side=payload.side,
                        sell_lots=order_intent.requested_lots,
                        open_tranche_exists=order_intent.target_tranche_id is not None,
                        orders_today=orders_today,
                        realized_pnl_today=realized_pnl_today,
                    )
                )
        except Exception as exc:
            return str(exc)
        return None

    def _apply_fill(self, *, order: Order, fill_lots: int, fill_price: Decimal) -> None:
        if fill_lots <= 0:
            return

        if order.signal_code in BUY_SIGNAL_CODES:
            fill_time = datetime.now(UTC)
            tranche = self.tranche_repo.apply_buy_fill(
                open_order_id=order.id,
                symbol=order.symbol,
                signal_code=order.signal_code,
                fill_lots=fill_lots,
                fill_price=fill_price,
                fill_time=fill_time,
                requested_lots=order.requested_lots,
            )
            self.execution_repo.add(
                order_id=order.id,
                event_type="tranche_update",
                status=order.status,
                message="buy fill applied to tranche",
                payload={
                    "tranche_id": tranche.id,
                    "filled_lots": tranche.filled_lots,
                    "remaining_lots": tranche.remaining_lots,
                    "entry_price": str(tranche.entry_price),
                },
            )
            return

        if order.target_tranche_id is None:
            self.execution_repo.add(
                order_id=order.id,
                event_type="tranche_update",
                status=order.status,
                message="sell fill skipped - missing target tranche",
                payload={"fill_lots": fill_lots},
            )
            return

        sell_result = self.tranche_repo.apply_sell_fill(
            close_order_id=order.id,
            target_tranche_id=order.target_tranche_id,
            fill_lots=fill_lots,
            fill_price=fill_price,
        )
        existing_realized = (
            Decimal(order.realized_pnl) if order.realized_pnl is not None else Decimal("0")
        )
        self.order_repo.set_realized_pnl(order, existing_realized + sell_result.realized_pnl)
        self.execution_repo.add(
            order_id=order.id,
            event_type="tranche_update",
            status=order.status,
            message="sell fill applied to tranche",
            payload={
                "tranche_id": sell_result.tranche.id,
                "applied_lots": sell_result.applied_lots,
                "remaining_lots": sell_result.tranche.remaining_lots,
                "realized_pnl": str(sell_result.realized_pnl),
            },
        )
