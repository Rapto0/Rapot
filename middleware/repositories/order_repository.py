from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from middleware.domain.enums import OrderStatus, Side
from middleware.infra.models import Order


class OrderRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        *,
        signal_event_id: int,
        idempotency_key: str,
        symbol: str,
        side: Side,
        signal_code: str,
        requested_lots: int,
        limit_price: Decimal,
        budget_tl: Decimal | None,
        status: OrderStatus,
        broker_name: str,
        mode: str,
        target_tranche_id: int | None = None,
        rejection_reason: str | None = None,
    ) -> Order:
        entity = Order(
            signal_event_id=signal_event_id,
            idempotency_key=idempotency_key,
            symbol=symbol,
            side=side.value,
            signal_code=signal_code,
            requested_lots=requested_lots,
            filled_lots=0,
            limit_price=limit_price,
            budget_tl=budget_tl,
            status=status.value,
            rejection_reason=rejection_reason,
            broker_name=broker_name,
            mode=mode,
            target_tranche_id=target_tranche_id,
            metadata_json={},
        )
        self.session.add(entity)
        self.session.flush()
        return entity

    def get(self, order_id: int) -> Order | None:
        stmt = select(Order).where(Order.id == order_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_signal_event_id(self, signal_event_id: int) -> Order | None:
        stmt = select(Order).where(Order.signal_event_id == signal_event_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_orders(self, *, limit: int = 100, symbol: str | None = None) -> list[Order]:
        stmt = select(Order)
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

    def apply_broker_ack(
        self,
        order: Order,
        *,
        status: OrderStatus,
        broker_order_id: str | None,
        filled_lots: int,
        avg_fill_price: Decimal | None,
    ) -> None:
        order.status = status.value
        order.broker_order_id = broker_order_id
        order.filled_lots = max(0, order.filled_lots + int(filled_lots))
        if avg_fill_price is not None:
            order.avg_fill_price = avg_fill_price
        order.updated_at = datetime.now(UTC)
        self.session.add(order)
        self.session.flush()

    def set_realized_pnl(self, order: Order, realized_pnl: Decimal) -> None:
        order.realized_pnl = realized_pnl
        order.updated_at = datetime.now(UTC)
        self.session.add(order)
        self.session.flush()

    def count_orders_today(self) -> int:
        start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = select(func.count(Order.id)).where(Order.created_at >= start)
        return int(self.session.execute(stmt).scalar() or 0)

    def get_realized_pnl_today(self) -> Decimal:
        start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = select(func.coalesce(func.sum(Order.realized_pnl), 0)).where(
            Order.created_at >= start,
            Order.side == Side.SELL.value,
            Order.realized_pnl.is_not(None),
        )
        value = self.session.execute(stmt).scalar()
        return Decimal(str(value or 0))
