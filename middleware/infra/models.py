from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )


class SignalEvent(Base):
    __tablename__ = "mw_signal_events"
    __table_args__ = (
        UniqueConstraint("event_hash", name="uq_mw_signal_events_event_hash"),
        Index("ix_mw_signal_events_symbol", "symbol"),
        Index("ix_mw_signal_events_bar_time", "bar_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    symbol: Mapped[str] = mapped_column(String(24), nullable=False)
    ticker: Mapped[str] = mapped_column(String(24), nullable=False)
    signal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    signal_text: Mapped[str] = mapped_column(String(200), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(24), nullable=False)
    bar_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bar_index: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_realtime: Mapped[bool] = mapped_column(Boolean, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )

    order: Mapped[Order] = relationship(back_populates="signal_event", uselist=False)


class Order(Base, TimestampMixin):
    __tablename__ = "mw_orders"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_mw_orders_idempotency_key"),
        Index("ix_mw_orders_symbol", "symbol"),
        Index("ix_mw_orders_status", "status"),
        Index("ix_mw_orders_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    signal_event_id: Mapped[int] = mapped_column(
        ForeignKey("mw_signal_events.id", ondelete="CASCADE"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(96), nullable=False)
    symbol: Mapped[str] = mapped_column(String(24), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    signal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    requested_lots: Mapped[int] = mapped_column(Integer, nullable=False)
    filled_lots: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    limit_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    budget_tl: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(String(400), nullable=True)
    broker_name: Mapped[str] = mapped_column(String(40), nullable=False)
    broker_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_tranche_id: Mapped[int | None] = mapped_column(
        ForeignKey("mw_tranches.id", ondelete="SET NULL"), nullable=True
    )
    avg_fill_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    realized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    signal_event: Mapped[SignalEvent] = relationship(back_populates="order")
    target_tranche: Mapped[Tranche] = relationship(foreign_keys=[target_tranche_id])
    execution_reports: Mapped[list[ExecutionReport]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class Tranche(Base, TimestampMixin):
    __tablename__ = "mw_tranches"
    __table_args__ = (
        Index("ix_mw_tranches_symbol_status", "symbol", "status"),
        Index("ix_mw_tranches_entry_time", "entry_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(24), nullable=False)
    signal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requested_lots: Mapped[int] = mapped_column(Integer, nullable=False)
    filled_lots: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    remaining_lots: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    open_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("mw_orders.id", ondelete="SET NULL"), nullable=True
    )
    close_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("mw_orders.id", ondelete="SET NULL"), nullable=True
    )


class ExecutionReport(Base):
    __tablename__ = "mw_execution_reports"
    __table_args__ = (
        Index("ix_mw_execution_reports_order_id", "order_id"),
        Index("ix_mw_execution_reports_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("mw_orders.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )

    order: Mapped[Order] = relationship(back_populates="execution_reports")
