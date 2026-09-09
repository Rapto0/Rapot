from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from middleware.broker_adapters.base import BrokerAssetBalance, BrokerClient, BrokerOrderResult
from middleware.domain.constants import BUY_SIGNAL_CODES
from middleware.domain.enums import ExecutionMode, OrderStatus, Side
from middleware.domain.events import (
    BrokerOrderRequestPayload,
    ProcessSignalResponse,
    TradingViewWebhookPayload,
)
from middleware.domain.idempotency import build_client_order_id
from middleware.infra.logging import get_logger
from middleware.infra.models import Order
from middleware.infra.settings import MiddlewareSettings
from middleware.infra.time import UTC, datetime_from_unix_ms
from middleware.repositories.execution_report_repository import ExecutionReportRepository
from middleware.repositories.order_repository import BrokerFillDelta, OrderRepository
from middleware.repositories.signal_repository import SignalRepository
from middleware.repositories.tranche_repository import TrancheRepository
from middleware.risk.checks import BuyRiskInput, RiskEngine, SellRiskInput

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
        self.inventory_scope = cfg.inventory_scope
        self.signal_repo = SignalRepository(session)
        self.order_repo = OrderRepository(session, inventory_scope=self.inventory_scope)
        self.tranche_repo = TrancheRepository(
            session,
            inventory_scope=self.inventory_scope,
            mode=cfg.execution_mode.value,
        )
        self.execution_repo = ExecutionReportRepository(session)
        self.risk = RiskEngine(cfg)

    def process_webhook(
        self,
        payload: TradingViewWebhookPayload,
        *,
        bypass_idempotency: bool = False,
    ) -> ProcessSignalResponse:
        event_hash = self.signal_repo.build_event_hash(payload)
        scoped_event_hash = hashlib.sha256(
            f"{self.inventory_scope}:{event_hash}".encode()
        ).hexdigest()
        idempotency_key = (
            scoped_event_hash
            if not bypass_idempotency
            else f"{scoped_event_hash}:replay:{uuid4().hex[:16]}"
        )
        client_order_id = build_client_order_id(idempotency_key)
        with self.session.begin():
            # Serialize risk and inventory decisions, including symbols without any tranche yet.
            self.order_repo.lock_daily_risk_scope()
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
                inventory_scope=self.inventory_scope,
                client_order_id=client_order_id,
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

            risk_reason = self._run_risk(
                payload=payload,
                order_intent=order_intent,
                current_order_id=order.id,
            )
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
                    client_order_id=order.client_order_id,
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
                message="durable dispatch intent saved; broker outcome may require recovery",
            )

            order_id = order.id
            broker_request = BrokerOrderRequestPayload(
                symbol=order.symbol,
                side=Side(order.side),
                lots=order.requested_lots,
                quantity=order.requested_quantity,
                limit_price=order.limit_price,
                signal_code=order.signal_code,
                idempotency_key=order.idempotency_key,
                client_order_id=order.client_order_id or client_order_id,
                metadata={
                    "signal_event_id": signal_event.id,
                    "source": payload.source,
                    "timeframe": payload.timeframe,
                    "is_realtime": payload.isRealtime,
                },
            )

        # A broker may reuse an already-filled clientOrderId. Commit the local intent before
        # any remote write so a crash/replay can only query this order, never submit it again.
        broker_result = self.broker_client.submit_limit_order(broker_request)

        with self.session.begin():
            self.order_repo.lock_daily_risk_scope()
            self.session.expire_all()
            order = self.order_repo.get(order_id, for_update=True)
            if order is None:
                raise LookupError("persisted dispatch order not found")
            self.tranche_repo.lock_symbol_open_tranches(order.symbol)
            self._record_broker_result(order, broker_result, event_type="broker")

            logger.info(
                "signal processed",
                extra={
                    "extra_fields": {
                        "signal_event_id": order.signal_event_id,
                        "order_id": order.id,
                        "symbol": payload.symbol,
                        "signal_code": payload.signalCode,
                        "status": order.status,
                        "broker": self.broker_client.name,
                    }
                },
            )

            return ProcessSignalResponse(
                signal_event_id=order.signal_event_id,
                order_id=order.id,
                duplicate=False,
                status=OrderStatus(order.status),
                message=self._result_message(order),
                risk_reason=order.rejection_reason,
                broker_order_id=order.broker_order_id,
                client_order_id=order.client_order_id,
            )

    def replay_signal(
        self,
        payload: TradingViewWebhookPayload,
        *,
        bypass_idempotency: bool,
    ) -> ProcessSignalResponse:
        return self.process_webhook(payload, bypass_idempotency=bypass_idempotency)

    def recover_order(self, order_id: int) -> ProcessSignalResponse:
        with self.session.begin():
            order = self.order_repo.get(order_id)
            if order is None:
                raise LookupError("order not found")
            if not order.client_order_id:
                raise ValueError("legacy order has no client order id")
            symbol = order.symbol
            client_order_id = order.client_order_id

        broker_result = self.broker_client.get_order_by_client_id(symbol, client_order_id)

        with self.session.begin():
            self.order_repo.lock_daily_risk_scope()
            self.session.expire_all()
            order = self.order_repo.get(order_id, for_update=True)
            if order is None:
                raise LookupError("order not found")
            self.tranche_repo.lock_symbol_open_tranches(order.symbol)
            self._record_broker_result(order, broker_result, event_type="recovery")

            return ProcessSignalResponse(
                signal_event_id=order.signal_event_id,
                order_id=order.id,
                duplicate=False,
                status=OrderStatus(order.status),
                message=self._result_message(order),
                risk_reason=order.rejection_reason,
                broker_order_id=order.broker_order_id,
                client_order_id=order.client_order_id,
            )

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
                    "mode": self.cfg.execution_mode.value,
                    "inventory_scope": self.inventory_scope,
                    "open_tranche_count": len(tranches),
                    "total_remaining_lots": total_lots,
                    "total_remaining_quantity": total_quantity,
                    "weighted_avg_entry_price": weighted_avg,
                }
            ]
        return self.tranche_repo.list_positions()

    def list_tranches(self, symbol: str | None = None):
        return self.tranche_repo.list_open_tranches(symbol=symbol)

    def reconcile_symbol(self, symbol: str) -> dict:
        normalized = symbol.upper()
        rules = self._get_binance_symbol_rules(normalized)
        tranches = self.tranche_repo.list_open_tranches(symbol=normalized)
        open_quantities = [
            (
                Decimal(tranche.remaining_quantity)
                if Decimal(tranche.remaining_quantity) > 0
                else Decimal(int(tranche.remaining_lots))
            )
            for tranche in tranches
        ]
        middleware_quantity = sum(open_quantities, Decimal("0"))
        balance = self._get_broker_asset_balances(rules.base_asset)

        tolerance = rules.step_size
        total_delta = balance.total - middleware_quantity
        free_delta = balance.free - middleware_quantity
        total_matches = abs(total_delta) <= tolerance
        sell_ready = balance.free + tolerance >= middleware_quantity

        messages: list[str] = []
        if total_matches:
            messages.append("Binance total base balance matches middleware open tranches")
        elif total_delta < 0:
            messages.append("Binance total base balance is lower than middleware open tranches")
        else:
            messages.append("Binance total base balance is higher than middleware open tranches")

        if not sell_ready:
            messages.append("Binance free base balance is lower than middleware sellable quantity")

        if total_matches and sell_ready:
            status = "OK"
            recommended_action = "No inventory repair is required"
        elif total_matches:
            status = "LOCKED_BALANCE"
            recommended_action = "Inspect open Binance orders before attempting another sell"
        else:
            status = "MISMATCH"
            recommended_action = (
                "Compare verified Binance trades, deposits, withdrawals, and all inventory "
                "scopes before making a manual correction"
            )

        return {
            "symbol": normalized,
            "mode": self.cfg.execution_mode.value,
            "inventory_scope": self.inventory_scope,
            "base_asset": rules.base_asset,
            "quote_asset": rules.quote_asset,
            "status": status,
            "tolerance_quantity": tolerance,
            "middleware_open_tranche_count": len(tranches),
            "middleware_remaining_quantity": middleware_quantity,
            "binance_free_quantity": balance.free,
            "binance_locked_quantity": balance.locked,
            "binance_total_quantity": balance.total,
            "total_delta_quantity": total_delta,
            "free_delta_quantity": free_delta,
            "sell_ready": sell_ready,
            "repair_policy": "REPORT_ONLY",
            "automatic_repair_supported": False,
            "recommended_action": recommended_action,
            "messages": messages,
        }

    def list_orders(self, *, limit: int = 100, symbol: str | None = None):
        return self.order_repo.list_orders(limit=limit, symbol=symbol)

    def list_signals(self, *, limit: int = 100, symbol: str | None = None):
        return self.signal_repo.list_signals(limit=limit, symbol=symbol)

    def _build_intent(
        self, payload: TradingViewWebhookPayload, *, for_update: bool
    ) -> _OrderIntent:
        symbol = payload.symbol.upper()
        return self._build_binance_spot_intent(payload, symbol=symbol, for_update=for_update)

    def _build_binance_spot_intent(
        self, payload: TradingViewWebhookPayload, *, symbol: str, for_update: bool
    ) -> _OrderIntent:
        rules = self._get_binance_symbol_rules(symbol)
        if payload.side == Side.BUY:
            quote_budget = self.cfg.quote_budget_for_signal(payload.signalCode)
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

        limit_price = rules.round_sell_price(
            payload.price * (Decimal("1") - (Decimal(self.cfg.sell_bps) / Decimal("10000")))
        )
        target = None
        quantity = Decimal("0")
        for candidate in self.tranche_repo.list_open_tranches(symbol=symbol):
            if for_update:
                candidate = self.tranche_repo.get(candidate.id, for_update=True)
                if candidate is None:
                    continue
            remaining = (
                Decimal(candidate.remaining_quantity)
                if Decimal(candidate.remaining_quantity) > 0
                else Decimal(int(candidate.remaining_lots))
            )
            candidate_quantity = rules.floor_quantity(remaining)
            # Retain dust in inventory, but let the next sellable tranche progress in FIFO order.
            if target is None:
                target, quantity = candidate, candidate_quantity
            if rules.validate_limit_order(price=limit_price, quantity=candidate_quantity) is None:
                target, quantity = candidate, candidate_quantity
                break

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
        self,
        *,
        payload: TradingViewWebhookPayload,
        order_intent: _OrderIntent,
        current_order_id: int,
    ) -> str | None:
        temporal_reason = self._run_temporal_guards(payload)
        if temporal_reason:
            return temporal_reason

        pending_order = self.order_repo.get_pending_for_symbol(
            order_intent.symbol, exclude_order_id=current_order_id
        )
        if pending_order is not None:
            return f"pending order {pending_order.id} must be recovered before another symbol order"
        orders_today = self.order_repo.count_submitted_orders_today(
            exclude_order_id=current_order_id
        )
        realized_pnl_today = self.order_repo.get_realized_pnl_today()
        try:
            if payload.side == Side.BUY:
                open_count = self.tranche_repo.count_open(payload.symbol)
                symbol_exposure = self.tranche_repo.get_symbol_exposure_usdt(payload.symbol)
                self.risk.validate_buy(
                    BuyRiskInput(
                        symbol=payload.symbol,
                        signal_code=payload.signalCode,
                        side=payload.side,
                        buy_lots=order_intent.requested_lots,
                        buy_quantity=order_intent.requested_quantity,
                        buy_limit_price=order_intent.limit_price,
                        quote_budget=order_intent.quote_budget,
                        open_tranche_count=open_count,
                        symbol_exposure_usdt=symbol_exposure,
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
                        sell_quantity=order_intent.requested_quantity,
                        open_tranche_exists=order_intent.target_tranche_id is not None,
                        orders_today=orders_today,
                        realized_pnl_today=realized_pnl_today,
                    )
                )
        except Exception as exc:
            return str(exc)
        return self._run_binance_spot_guards(payload=payload, order_intent=order_intent)

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

    def _get_binance_symbol_rules(self, symbol: str):
        get_rules = getattr(self.broker_client, "get_symbol_rules", None)
        if get_rules is None:
            raise RuntimeError("Binance broker adapter does not expose symbol rules")
        return get_rules(symbol)

    def _get_broker_asset_balances(self, asset: str) -> BrokerAssetBalance:
        get_balances = getattr(self.broker_client, "get_asset_balances", None)
        if get_balances is not None:
            return get_balances(asset)

        get_free_balance = getattr(self.broker_client, "get_asset_balance", None)
        if get_free_balance is not None:
            return BrokerAssetBalance(
                asset=asset.upper(),
                free=get_free_balance(asset),
                locked=Decimal("0"),
            )

        raise RuntimeError("broker adapter does not expose account balances")

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
            client_order_id=existing_order.client_order_id if existing_order else None,
        )

    @staticmethod
    def _result_message(order: Order) -> str:
        if order.status == OrderStatus.UNKNOWN.value:
            return "broker result is uncertain; use admin recovery"
        if order.status in {
            OrderStatus.CANCELLED.value,
            OrderStatus.EXPIRED.value,
            OrderStatus.FAILED.value,
        }:
            return "broker order finalized"
        return "signal processed"

    def _record_broker_result(
        self,
        order: Order,
        broker_result: BrokerOrderResult,
        *,
        event_type: str,
    ) -> None:
        try:
            reported_lots = Decimal(broker_result.filled_lots)
            reported_quantity = Decimal(broker_result.filled_quantity)
            reported_price = (
                Decimal(broker_result.avg_fill_price)
                if broker_result.avg_fill_price is not None
                else None
            )
            commissions = {
                asset.upper(): Decimal(amount)
                for asset, amount in broker_result.commission_by_asset.items()
            }
        except (ArithmeticError, AttributeError, TypeError, ValueError):
            self._record_uncertain_snapshot(
                order,
                broker_result,
                event_type=event_type,
                reason="broker reported invalid accounting values",
            )
            return
        reported_numbers = [reported_lots, reported_quantity, *commissions.values()]
        if reported_price is not None:
            reported_numbers.append(reported_price)
        if any(not value.is_finite() for value in reported_numbers):
            self._record_uncertain_snapshot(
                order,
                broker_result,
                event_type=event_type,
                reason="broker reported non-finite accounting values",
            )
            return
        broker_result.filled_quantity = reported_quantity
        broker_result.avg_fill_price = reported_price
        previous_commissions = {
            asset.upper(): Decimal(amount) for asset, amount in order.commission_json.items()
        }
        invalid_fill = (
            reported_lots != reported_lots.to_integral_value()
            or reported_lots < 0
            or broker_result.filled_quantity < 0
            or reported_lots > order.requested_lots
            or broker_result.filled_quantity > order.requested_quantity
            or (reported_price is not None and reported_price <= 0)
            or any(not asset or amount < 0 for asset, amount in commissions.items())
            or any(
                commissions.get(asset, Decimal("0")) < amount
                for asset, amount in previous_commissions.items()
            )
        )
        if invalid_fill:
            self._record_uncertain_snapshot(
                order,
                broker_result,
                event_type=event_type,
                reason="broker reported fill outside the requested amount",
            )
            return
        broker_result.filled_lots = int(reported_lots)

        has_fill = broker_result.filled_lots > 0 or broker_result.filled_quantity > 0
        if has_fill and not broker_result.commission_complete:
            self._record_uncertain_snapshot(
                order,
                broker_result,
                event_type=event_type,
                reason="broker fill commissions could not be verified",
            )
            return
        accounting_reason = self._validate_commission_delta(
            order,
            broker_result,
            commissions=commissions,
            previous_commissions=previous_commissions,
        )
        if accounting_reason:
            self._record_uncertain_snapshot(
                order,
                broker_result,
                event_type=event_type,
                reason=accounting_reason,
            )
            return
        if has_fill and broker_result.avg_fill_price is None:
            self._record_uncertain_snapshot(
                order,
                broker_result,
                event_type=event_type,
                reason="broker reported a fill without an average fill price",
            )
            return

        fill_delta = self.order_repo.apply_broker_snapshot(
            order,
            status=broker_result.status,
            broker_order_id=broker_result.broker_order_id,
            filled_lots=broker_result.filled_lots,
            filled_quantity=broker_result.filled_quantity,
            avg_fill_price=broker_result.avg_fill_price,
            commission_by_asset=commissions,
            commission_complete=broker_result.commission_complete,
        )
        unresolved_terminal = order.status in {
            OrderStatus.CANCELLED.value,
            OrderStatus.EXPIRED.value,
            OrderStatus.FAILED.value,
        }
        if not broker_result.accepted or broker_result.execution_uncertain:
            order.rejection_reason = broker_result.message or "broker did not accept order"
        elif not unresolved_terminal:
            order.rejection_reason = None

        self.execution_repo.add(
            order_id=order.id,
            event_type=event_type,
            status=broker_result.status.value,
            message=broker_result.message,
            payload={
                **broker_result.raw_payload,
                "cumulative_filled_lots": broker_result.filled_lots,
                "cumulative_filled_quantity": str(broker_result.filled_quantity),
                "applied_delta_lots": fill_delta.lots,
                "applied_delta_quantity": str(fill_delta.quantity),
                "cumulative_commission_by_asset": {
                    asset: str(amount) for asset, amount in commissions.items()
                },
                "applied_commission_delta_by_asset": {
                    asset: str(amount) for asset, amount in fill_delta.commission_by_asset.items()
                },
                "commission_complete": broker_result.commission_complete,
            },
        )

        if (fill_delta.lots > 0 or fill_delta.quantity > 0) and fill_delta.price is not None:
            self._apply_accounted_fill(order=order, fill_delta=fill_delta)

    def _validate_commission_delta(
        self,
        order: Order,
        broker_result: BrokerOrderResult,
        *,
        commissions: dict[str, Decimal],
        previous_commissions: dict[str, Decimal],
    ) -> str | None:
        gross_delta = max(
            Decimal("0"),
            broker_result.filled_quantity - Decimal(order.filled_quantity),
        )
        commission_delta = {
            asset: amount - previous_commissions.get(asset, Decimal("0"))
            for asset, amount in commissions.items()
            if amount > previous_commissions.get(asset, Decimal("0"))
        }
        if gross_delta <= 0 and commission_delta:
            return "commission changed without a new fill; manual reconciliation is required"

        base_asset = (order.base_asset or "").upper()
        quote_asset = (order.quote_asset or "").upper()
        base_fee = commission_delta.get(base_asset, Decimal("0"))
        quote_fee = commission_delta.get(quote_asset, Decimal("0"))
        gross_quote = Decimal("0")
        if gross_delta > 0 and broker_result.avg_fill_price is not None:
            previous_quantity = Decimal(order.filled_quantity)
            if previous_quantity > 0 and order.avg_fill_price is None:
                return "previous fill has no average price; manual reconciliation is required"
            previous_quote = previous_quantity * Decimal(order.avg_fill_price or 0)
            gross_quote = (
                broker_result.filled_quantity * broker_result.avg_fill_price - previous_quote
            )
            if not gross_quote.is_finite() or gross_quote <= 0:
                return "cumulative fill value does not increase with the new fill"
        if order.signal_code in BUY_SIGNAL_CODES and base_fee >= gross_delta > 0:
            return "base-asset commission consumes the complete buy fill"

        if order.signal_code not in BUY_SIGNAL_CODES and gross_delta > 0:
            if broker_result.avg_fill_price is not None and quote_fee > gross_quote:
                return "quote-asset commission exceeds the sell proceeds"
            if base_fee > 0 and order.target_tranche_id is not None:
                target = self.tranche_repo.get(order.target_tranche_id, for_update=True)
                available = (
                    Decimal(target.remaining_quantity) if target is not None else Decimal("0")
                )
                if gross_delta + base_fee > available:
                    return "base-asset sell commission exceeds tracked inventory"
        return None

    def _apply_accounted_fill(self, *, order: Order, fill_delta: BrokerFillDelta) -> None:
        base_asset = (order.base_asset or "").upper()
        quote_asset = (order.quote_asset or "").upper()
        base_commission = fill_delta.commission_by_asset.get(base_asset, Decimal("0"))
        quote_commission = fill_delta.commission_by_asset.get(quote_asset, Decimal("0"))
        gross_quantity = fill_delta.quantity
        gross_notional = gross_quantity * fill_delta.price

        if order.signal_code in BUY_SIGNAL_CODES:
            inventory_quantity = gross_quantity - base_commission
            quote_value = gross_notional + quote_commission
        else:
            inventory_quantity = gross_quantity + base_commission
            quote_value = gross_notional - quote_commission

        if inventory_quantity <= 0 or quote_value < 0:
            raise ValueError("commission-adjusted fill is invalid")
        effective_price = quote_value / inventory_quantity
        self._apply_fill(
            order=order,
            fill_lots=fill_delta.lots,
            fill_quantity=inventory_quantity,
            fill_price=effective_price,
        )

    def _record_uncertain_snapshot(
        self,
        order: Order,
        broker_result: BrokerOrderResult,
        *,
        event_type: str,
        reason: str,
    ) -> None:
        known_terminal = {
            OrderStatus.FILLED.value,
            OrderStatus.CANCELLED.value,
            OrderStatus.EXPIRED.value,
            OrderStatus.FAILED.value,
        }
        if order.status not in known_terminal:
            self.order_repo.set_status(order, OrderStatus.UNKNOWN, rejection_reason=reason)
        if broker_result.broker_order_id:
            order.broker_order_id = broker_result.broker_order_id
        self.execution_repo.add(
            order_id=order.id,
            event_type=event_type,
            status=OrderStatus.UNKNOWN.value,
            message=reason,
            payload=broker_result.raw_payload,
        )

    def _run_temporal_guards(self, payload: TradingViewWebhookPayload) -> str | None:
        if self.cfg.require_realtime_signals and not payload.isRealtime:
            return "isRealtime must be true when MW_REQUIRE_REALTIME_SIGNALS=true"

        now = datetime.now(UTC)
        bar_time = datetime_from_unix_ms(payload.barTime)

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
