from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from middleware.broker_adapters.base import BrokerClient
from middleware.domain.constants import BUY_SIGNAL_CODES
from middleware.domain.enums import BrokerName, ExecutionMode, OrderStatus, Side
from middleware.domain.events import (
    BrokerOrderRequestPayload,
    ProcessSignalResponse,
    SimulateFillRequest,
    TradingViewWebhookPayload,
)
from middleware.infra.logging import get_logger
from middleware.infra.models import Order
from middleware.infra.settings import MiddlewareSettings
from middleware.infra.time import UTC
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
    requested_quantity: Decimal
    limit_price: Decimal
    budget_tl: Decimal | None
    quote_budget: Decimal | None
    base_asset: str | None
    quote_asset: str | None
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
        idempotency_key = (
            event_hash
            if not bypass_idempotency
            else f"{event_hash}:replay:{int(datetime.now(UTC).timestamp() * 1000)}"
        )
        with self.session.begin():
            if not bypass_idempotency:
                existing = self.signal_repo.get_by_event_hash(event_hash)
                if existing:
                    existing_order = self.order_repo.get_by_signal_event_id(existing.id)
                    if existing_order is not None:
                        logger.info(
                            "duplicate signal ignored",
                            extra={
                                "extra_fields": {
                                    "signal_event_id": existing.id,
                                    "order_id": existing_order.id,
                                    "symbol": payload.symbol,
                                    "signal_code": payload.signalCode,
                                }
                            },
                        )
                        return self._build_duplicate_response(existing.id)

            signal_event, signal_created = self.signal_repo.create_or_get(
                payload,
                event_hash=event_hash,
            )
            if not signal_created and not bypass_idempotency:
                existing_order = self.order_repo.get_by_signal_event_id(signal_event.id)
                if existing_order is not None:
                    logger.info(
                        "duplicate signal ignored after create-or-get",
                        extra={
                            "extra_fields": {
                                "signal_event_id": signal_event.id,
                                "order_id": existing_order.id,
                                "symbol": payload.symbol,
                                "signal_code": payload.signalCode,
                            }
                        },
                    )
                    return self._build_duplicate_response(signal_event.id)

            # Lock current symbol inventory rows for consistent risk/FIFO decisions under concurrency.
            self.tranche_repo.lock_symbol_open_tranches(payload.symbol)

            order_intent = self._build_intent(payload, for_update=True)
            order, order_created = self.order_repo.create_or_get(
                signal_event_id=signal_event.id,
                idempotency_key=idempotency_key,
                symbol=order_intent.symbol,
                side=order_intent.side,
                signal_code=order_intent.signal_code,
                requested_lots=order_intent.requested_lots,
                requested_quantity=order_intent.requested_quantity,
                limit_price=order_intent.limit_price,
                budget_tl=order_intent.budget_tl,
                quote_budget=order_intent.quote_budget,
                status=OrderStatus.RECEIVED,
                broker_name=self.broker_client.name,
                mode=self.cfg.execution_mode.value,
                base_asset=order_intent.base_asset,
                quote_asset=order_intent.quote_asset,
                target_tranche_id=order_intent.target_tranche_id,
            )
            if not order_created and not bypass_idempotency:
                return self._build_duplicate_response(signal_event.id)

            self.execution_repo.add(
                order_id=order.id,
                event_type="lifecycle",
                status=OrderStatus.RECEIVED.value,
                message="order received",
                payload={"event_hash": event_hash},
            )

            risk_reason = self._run_risk(payload=payload, order_intent=order_intent)
            if risk_reason:
                self.order_repo.set_status(
                    order, OrderStatus.REJECTED, rejection_reason=risk_reason
                )
                self.execution_repo.add(
                    order_id=order.id,
                    event_type="risk",
                    status=OrderStatus.REJECTED.value,
                    message=risk_reason,
                    payload={"symbol": payload.symbol, "signalCode": payload.signalCode},
                )
                logger.warning(
                    "signal rejected by risk",
                    extra={
                        "extra_fields": {
                            "signal_event_id": signal_event.id,
                            "order_id": order.id,
                            "symbol": payload.symbol,
                            "signal_code": payload.signalCode,
                            "reason": risk_reason,
                        }
                    },
                )
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
                    quantity=order.requested_quantity,
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
                logger.warning(
                    "broker rejected order",
                    extra={
                        "extra_fields": {
                            "signal_event_id": signal_event.id,
                            "order_id": order.id,
                            "symbol": payload.symbol,
                            "signal_code": payload.signalCode,
                            "broker": self.broker_client.name,
                            "status": final_status.value,
                        }
                    },
                )
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
                filled_quantity=broker_result.filled_quantity,
                avg_fill_price=broker_result.avg_fill_price,
            )
            self.execution_repo.add(
                order_id=order.id,
                event_type="broker",
                status=broker_result.status.value,
                message=broker_result.message,
                payload=broker_result.raw_payload,
            )

            if (
                broker_result.filled_lots > 0 or broker_result.filled_quantity > 0
            ) and broker_result.avg_fill_price is not None:
                self._apply_fill(
                    order=order,
                    fill_lots=broker_result.filled_lots,
                    fill_quantity=broker_result.filled_quantity,
                    fill_price=broker_result.avg_fill_price,
                )

            logger.info(
                "signal processed",
                extra={
                    "extra_fields": {
                        "signal_event_id": signal_event.id,
                        "order_id": order.id,
                        "symbol": payload.symbol,
                        "signal_code": payload.signalCode,
                        "status": order.status,
                        "broker": self.broker_client.name,
                    }
                },
            )

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
        with self.session.begin():
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
            fill_quantity = Decimal(fill_lots)
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
                filled_quantity=fill_quantity,
                avg_fill_price=fill_price,
            )
            self.execution_repo.add(
                order_id=order.id,
                event_type="simulate_fill",
                status=next_status.value,
                message="admin simulate fill",
                payload={
                    "fill_lots": fill_lots,
                    "fill_quantity": str(fill_quantity),
                    "fill_price": str(fill_price),
                },
            )

            self._apply_fill(
                order=order,
                fill_lots=fill_lots,
                fill_quantity=fill_quantity,
                fill_price=fill_price,
            )
            return order

    def list_positions(self, symbol: str | None = None) -> list[dict]:
        if symbol:
            tranches = self.tranche_repo.list_open_tranches(symbol=symbol)
            if not tranches:
                return []
            open_quantities = [
                (
                    Decimal(t.remaining_quantity)
                    if Decimal(t.remaining_quantity) > 0
                    else Decimal(int(t.remaining_lots))
                )
                for t in tranches
            ]
            weighted_num = sum(
                (
                    Decimal(t.entry_price) * quantity
                    for t, quantity in zip(tranches, open_quantities, strict=False)
                ),
                Decimal("0"),
            )
            total_lots = sum(int(t.remaining_lots) for t in tranches)
            total_quantity = sum(open_quantities, Decimal("0"))
            weighted_avg = weighted_num / total_quantity if total_quantity > 0 else None
            return [
                {
                    "symbol": symbol.upper(),
                    "open_tranche_count": len(tranches),
                    "total_remaining_lots": total_lots,
                    "total_remaining_quantity": total_quantity,
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

    def _build_intent(
        self, payload: TradingViewWebhookPayload, *, for_update: bool
    ) -> _OrderIntent:
        symbol = payload.symbol.upper()
        if self._is_binance_spot:
            return self._build_binance_spot_intent(payload, symbol=symbol, for_update=for_update)

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
                requested_quantity=Decimal(lots),
                limit_price=limit_price,
                budget_tl=budget,
                quote_budget=None,
                base_asset=None,
                quote_asset=None,
                target_tranche_id=None,
            )

        target = self.tranche_repo.oldest_open(symbol, for_update=for_update)
        limit_price = self.tick_policy.sell_limit_price(symbol, payload.price, self.cfg.sell_bps)
        lots = int(target.remaining_lots) if target else 0
        return _OrderIntent(
            symbol=symbol,
            side=payload.side,
            signal_code=payload.signalCode,
            requested_lots=lots,
            requested_quantity=Decimal(lots),
            limit_price=limit_price,
            budget_tl=None,
            quote_budget=None,
            base_asset=None,
            quote_asset=None,
            target_tranche_id=target.id if target else None,
        )

    def _build_binance_spot_intent(
        self, payload: TradingViewWebhookPayload, *, symbol: str, for_update: bool
    ) -> _OrderIntent:
        rules = self._get_binance_symbol_rules(symbol)
        if payload.side == Side.BUY:
            multiplier = self.cfg.signal_multipliers[payload.signalCode]
            quote_budget = self.cfg.binance_buy_quote_amount_usdt * multiplier
            limit_price = rules.round_buy_price(
                payload.price * (Decimal("1") + (Decimal(self.cfg.buy_bps) / Decimal("10000")))
            )
            quantity = rules.floor_quantity(quote_budget / limit_price)
            return _OrderIntent(
                symbol=symbol,
                side=payload.side,
                signal_code=payload.signalCode,
                requested_lots=0,
                requested_quantity=quantity,
                limit_price=limit_price,
                budget_tl=None,
                quote_budget=quote_budget,
                base_asset=rules.base_asset,
                quote_asset=rules.quote_asset,
                target_tranche_id=None,
            )

        target = self.tranche_repo.oldest_open(symbol, for_update=for_update)
        limit_price = rules.round_sell_price(
            payload.price * (Decimal("1") - (Decimal(self.cfg.sell_bps) / Decimal("10000")))
        )
        quantity = Decimal("0")
        if target is not None:
            quantity = (
                Decimal(target.remaining_quantity)
                if Decimal(target.remaining_quantity) > 0
                else Decimal(int(target.remaining_lots))
            )
            quantity = rules.floor_quantity(quantity)

        return _OrderIntent(
            symbol=symbol,
            side=payload.side,
            signal_code=payload.signalCode,
            requested_lots=0,
            requested_quantity=quantity,
            limit_price=limit_price,
            budget_tl=None,
            quote_budget=None,
            base_asset=rules.base_asset,
            quote_asset=rules.quote_asset,
            target_tranche_id=target.id if target else None,
        )

    def _run_risk(
        self, *, payload: TradingViewWebhookPayload, order_intent: _OrderIntent
    ) -> str | None:
        temporal_reason = self._run_temporal_guards(payload)
        if temporal_reason:
            return temporal_reason

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
                        buy_quantity=(
                            order_intent.requested_quantity if self._is_binance_spot else None
                        ),
                        buy_limit_price=order_intent.limit_price,
                        quote_budget=order_intent.quote_budget if self._is_binance_spot else None,
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
                        sell_quantity=(
                            order_intent.requested_quantity if self._is_binance_spot else None
                        ),
                        open_tranche_exists=order_intent.target_tranche_id is not None,
                        orders_today=orders_today,
                        realized_pnl_today=realized_pnl_today,
                    )
                )
        except Exception as exc:
            return str(exc)
        if self._is_binance_spot:
            return self._run_binance_spot_guards(payload=payload, order_intent=order_intent)
        return None

    def _run_binance_spot_guards(
        self, *, payload: TradingViewWebhookPayload, order_intent: _OrderIntent
    ) -> str | None:
        try:
            rules = self._get_binance_symbol_rules(order_intent.symbol)
        except Exception as exc:
            return str(exc)

        expected_quote = self.cfg.binance_quote_asset.upper()
        if rules.quote_asset.upper() != expected_quote:
            return (
                f"Binance symbol quote asset mismatch: expected {expected_quote}, "
                f"got {rules.quote_asset}"
            )

        filter_reason = rules.validate_limit_order(
            price=order_intent.limit_price,
            quantity=order_intent.requested_quantity,
        )
        if filter_reason:
            return filter_reason

        if (
            payload.side == Side.BUY
            and self.cfg.execution_mode == ExecutionMode.LIVE
            and self.cfg.binance_check_balance
        ):
            try:
                free_quote = self.broker_client.get_asset_balance(rules.quote_asset)  # type: ignore[attr-defined]
            except Exception as exc:
                return f"Binance balance check failed: {exc}"
            required_quote = order_intent.quote_budget or (
                order_intent.requested_quantity * order_intent.limit_price
            )
            if free_quote < required_quote:
                return (
                    f"insufficient Binance {rules.quote_asset} balance: "
                    f"free={free_quote}, required={required_quote}"
                )
        return None

    @property
    def _is_binance_spot(self) -> bool:
        return self.cfg.broker_name == BrokerName.BINANCE_SPOT

    def _get_binance_symbol_rules(self, symbol: str):
        get_rules = getattr(self.broker_client, "get_symbol_rules", None)
        if get_rules is None:
            raise RuntimeError("Binance broker adapter does not expose symbol rules")
        return get_rules(symbol)

    def _build_duplicate_response(self, signal_event_id: int) -> ProcessSignalResponse:
        existing_order = self.order_repo.get_by_signal_event_id(signal_event_id)
        return ProcessSignalResponse(
            signal_event_id=signal_event_id,
            order_id=existing_order.id if existing_order else None,
            duplicate=True,
            status=(
                OrderStatus(existing_order.status)
                if existing_order and existing_order.status in OrderStatus._value2member_map_
                else None
            ),
            message="duplicate signal ignored",
            broker_order_id=existing_order.broker_order_id if existing_order else None,
        )

    def _run_temporal_guards(self, payload: TradingViewWebhookPayload) -> str | None:
        if self.cfg.require_realtime_signals and not payload.isRealtime:
            return "isRealtime must be true when MW_REQUIRE_REALTIME_SIGNALS=true"

        now = datetime.now(UTC)
        bar_time = datetime.fromtimestamp(payload.barTime / 1000, tz=UTC)

        future_seconds = (bar_time - now).total_seconds()
        if future_seconds > self.cfg.max_signal_future_skew_seconds:
            return (
                "barTime is too far in the future "
                f"(>{self.cfg.max_signal_future_skew_seconds}s skew)"
            )

        if self.cfg.max_signal_age_seconds is not None:
            age_seconds = (now - bar_time).total_seconds()
            if age_seconds > self.cfg.max_signal_age_seconds:
                return (
                    "signal is older than allowed freshness window "
                    f"({self.cfg.max_signal_age_seconds}s)"
                )
        return None

    def _apply_fill(
        self, *, order: Order, fill_lots: int, fill_quantity: Decimal, fill_price: Decimal
    ) -> None:
        if fill_lots <= 0 and fill_quantity <= 0:
            return

        if order.signal_code in BUY_SIGNAL_CODES:
            fill_time = datetime.now(UTC)
            tranche = self.tranche_repo.apply_buy_fill(
                open_order_id=order.id,
                symbol=order.symbol,
                signal_code=order.signal_code,
                fill_lots=fill_lots,
                fill_quantity=fill_quantity,
                fill_price=fill_price,
                fill_time=fill_time,
                requested_lots=order.requested_lots,
                requested_quantity=order.requested_quantity,
            )
            self.execution_repo.add(
                order_id=order.id,
                event_type="tranche_update",
                status=order.status,
                message="buy fill applied to tranche",
                payload={
                    "tranche_id": tranche.id,
                    "filled_lots": tranche.filled_lots,
                    "filled_quantity": str(tranche.filled_quantity),
                    "remaining_lots": tranche.remaining_lots,
                    "remaining_quantity": str(tranche.remaining_quantity),
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
                payload={"fill_lots": fill_lots, "fill_quantity": str(fill_quantity)},
            )
            return

        sell_result = self.tranche_repo.apply_sell_fill(
            close_order_id=order.id,
            target_tranche_id=order.target_tranche_id,
            fill_lots=fill_lots,
            fill_quantity=fill_quantity,
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
                "applied_quantity": str(sell_result.applied_quantity),
                "remaining_lots": sell_result.tranche.remaining_lots,
                "remaining_quantity": str(sell_result.tranche.remaining_quantity),
                "realized_pnl": str(sell_result.realized_pnl),
            },
        )
