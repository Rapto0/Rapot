from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from middleware.domain.enums import OrderStatus, Side
from middleware.infra.models import Order
from middleware.infra.time import UTC


@dataclass(frozen=True, slots=True)
class BrokerFillDelta:
    lots: int
    quantity: Decimal
    price: Decimal | None


class OrderRepository:
    def __init__(self, session: Session, *, inventory_scope: str):
        self.session = session
        self.inventory_scope = inventory_scope

    def create(
        self,
        *,
        signal_event_id: int,
        idempotency_key: str,
        symbol: str,
        side: Side,
        signal_code: str,
        requested_lots: int,
        requested_quantity: Decimal | None,
        limit_price: Decimal,
        budget_tl: Decimal | None,
        quote_budget: Decimal | None,
        status: OrderStatus,
        broker_name: str,
        mode: str,
        inventory_scope: str,
        client_order_id: str,
        base_asset: str | None = None,
        quote_asset: str | None = None,
        target_tranche_id: int | None = None,
        rejection_reason: str | None = None,
    ) -> Order:
        requested_quantity = (
            requested_quantity if requested_quantity is not None else Decimal(requested_lots)
        )
        entity = Order(
            signal_event_id=signal_event_id,
            idempotency_key=idempotency_key,
            symbol=symbol,
            side=side.value,
            signal_code=signal_code,
            requested_lots=requested_lots,
            filled_lots=0,
            requested_quantity=requested_quantity,
            filled_quantity=Decimal("0"),
            limit_price=limit_price,
            budget_tl=budget_tl,
            quote_budget=quote_budget,
            status=status.value,
            rejection_reason=rejection_reason,
            broker_name=broker_name,
            mode=mode,
            inventory_scope=inventory_scope,
            client_order_id=client_order_id,
            base_asset=base_asset,
            quote_asset=quote_asset,
            target_tranche_id=target_tranche_id,
            metadata_json={},
        )
        self.session.add(entity)
        self.session.flush()
        return entity

    def create_or_get(
        self,
        *,
        signal_event_id: int,
        idempotency_key: str,
        symbol: str,
        side: Side,
        signal_code: str,
        requested_lots: int,
        requested_quantity: Decimal | None,
        limit_price: Decimal,
        budget_tl: Decimal | None,
        quote_budget: Decimal | None,
        status: OrderStatus,
        broker_name: str,
        mode: str,
        inventory_scope: str,
        client_order_id: str,
        base_asset: str | None = None,
        quote_asset: str | None = None,
        target_tranche_id: int | None = None,
        rejection_reason: str | None = None,
    ) -> tuple[Order, bool]:
        existing = self.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing, False
        try:
            with self.session.begin_nested():
                order = self.create(
                    signal_event_id=signal_event_id,
                    idempotency_key=idempotency_key,
                    symbol=symbol,
                    side=side,
                    signal_code=signal_code,
                    requested_lots=requested_lots,
                    requested_quantity=requested_quantity,
                    limit_price=limit_price,
                    budget_tl=budget_tl,
                    quote_budget=quote_budget,
                    status=status,
                    broker_name=broker_name,
                    mode=mode,
                    inventory_scope=inventory_scope,
                    client_order_id=client_order_id,
                    base_asset=base_asset,
                    quote_asset=quote_asset,
                    target_tranche_id=target_tranche_id,
                    rejection_reason=rejection_reason,
                )
            return order, True
        except IntegrityError:
            existing = self.get_by_idempotency_key(idempotency_key)
            if existing is None:
                raise
            return existing, False

    def get(self, order_id: int, *, for_update: bool = False) -> Order | None:
        stmt = select(Order).where(
            Order.id == order_id,
            Order.inventory_scope == self.inventory_scope,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_signal_event_id(self, signal_event_id: int) -> Order | None:
        stmt = select(Order).where(
            Order.signal_event_id == signal_event_id,
            Order.inventory_scope == self.inventory_scope,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_idempotency_key(self, idempotency_key: str) -> Order | None:
        stmt = select(Order).where(
            Order.idempotency_key == idempotency_key,
            Order.inventory_scope == self.inventory_scope,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_orders(self, *, limit: int = 100, symbol: str | None = None) -> list[Order]:
        stmt = select(Order).where(Order.inventory_scope == self.inventory_scope)
        if symbol:
            stmt = stmt.where(Order.symbol == symbol.upper())
        stmt = stmt.order_by(Order.id.desc()).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def set_status(
        self,
        order: Order,
        status: OrderStatus,
        *,
        rejection_reason: str | None = None,
    ) -> None:
        order.status = status.value
        if rejection_reason:
            order.rejection_reason = rejection_reason
        order.updated_at = datetime.now(UTC)
        self.session.add(order)
        self.session.flush()

    def apply_broker_snapshot(
        self,
        order: Order,
        *,
        status: OrderStatus,
        broker_order_id: str | None,
        filled_lots: int,
        avg_fill_price: Decimal | None,
        filled_quantity: Decimal | None = None,
    ) -> BrokerFillDelta:
        previous_lots = int(order.filled_lots)
        previous_quantity = Decimal(order.filled_quantity)
        previous_avg_price = (
            Decimal(order.avg_fill_price) if order.avg_fill_price is not None else None
        )
        reported_lots = min(max(0, int(filled_lots)), int(order.requested_lots))
        reported_quantity = min(
            max(Decimal("0"), Decimal(filled_quantity or 0)),
            Decimal(order.requested_quantity),
        )
        cumulative_lots = max(previous_lots, reported_lots)
        cumulative_quantity = max(previous_quantity, reported_quantity)
        delta_lots = cumulative_lots - previous_lots
        delta_quantity = cumulative_quantity - previous_quantity

        delta_price = avg_fill_price
        if delta_quantity > 0 and avg_fill_price is not None and previous_quantity > 0:
            previous_notional = previous_quantity * (previous_avg_price or avg_fill_price)
            cumulative_notional = cumulative_quantity * avg_fill_price
            delta_price = (cumulative_notional - previous_notional) / delta_quantity

        current_status = OrderStatus(order.status)
        known_terminal = {
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.EXPIRED,
            OrderStatus.FAILED,
            OrderStatus.REJECTED,
        }
        if current_status == OrderStatus.FILLED or (
            current_status in known_terminal and status != OrderStatus.FILLED
        ):
            resolved_status = current_status
        else:
            resolved_status = status

        order.status = resolved_status.value
        if broker_order_id:
            order.broker_order_id = broker_order_id
        order.filled_lots = cumulative_lots
        order.filled_quantity = cumulative_quantity
        if avg_fill_price is not None and (
            delta_lots > 0 or delta_quantity > 0 or previous_avg_price is None
        ):
            order.avg_fill_price = avg_fill_price
        order.updated_at = datetime.now(UTC)
        self.session.add(order)
        self.session.flush()
        return BrokerFillDelta(lots=delta_lots, quantity=delta_quantity, price=delta_price)

    def set_realized_pnl(self, order: Order, realized_pnl: Decimal) -> None:
        order.realized_pnl = realized_pnl
        order.updated_at = datetime.now(UTC)
        self.session.add(order)
        self.session.flush()

    def count_orders_today(self) -> int:
        start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = select(func.count(Order.id)).where(
            Order.created_at >= start,
            Order.inventory_scope == self.inventory_scope,
        )
        return int(self.session.execute(stmt).scalar() or 0)

    def get_realized_pnl_today(self) -> Decimal:
        start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = select(func.coalesce(func.sum(Order.realized_pnl), 0)).where(
            Order.created_at >= start,
            Order.inventory_scope == self.inventory_scope,
            Order.side == Side.SELL.value,
            Order.realized_pnl.is_not(None),
        )
        value = self.session.execute(stmt).scalar()
        return Decimal(str(value or 0))
