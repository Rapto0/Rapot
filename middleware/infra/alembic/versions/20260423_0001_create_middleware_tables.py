"""create middleware trading tables

Revision ID: 20260423_0001
Revises: None
Create Date: 2026-04-23 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260423_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mw_signal_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_hash", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("symbol", sa.String(length=24), nullable=False),
        sa.Column("ticker", sa.String(length=24), nullable=False),
        sa.Column("signal_code", sa.String(length=20), nullable=False),
        sa.Column("signal_text", sa.String(length=200), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("price", sa.Numeric(18, 6), nullable=False),
        sa.Column("timeframe", sa.String(length=24), nullable=False),
        sa.Column("bar_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bar_index", sa.BigInteger(), nullable=False),
        sa.Column("is_realtime", sa.Boolean(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column(
            "received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("event_hash", name="uq_mw_signal_events_event_hash"),
    )
    op.create_index("ix_mw_signal_events_symbol", "mw_signal_events", ["symbol"])
    op.create_index("ix_mw_signal_events_bar_time", "mw_signal_events", ["bar_time"])

    op.create_table(
        "mw_tranches",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=24), nullable=False),
        sa.Column("signal_code", sa.String(length=20), nullable=False),
        sa.Column("entry_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("entry_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_lots", sa.Integer(), nullable=False),
        sa.Column("filled_lots", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("remaining_lots", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("open_order_id", sa.Integer(), nullable=True),
        sa.Column("close_order_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_mw_tranches_symbol_status", "mw_tranches", ["symbol", "status"])
    op.create_index("ix_mw_tranches_entry_time", "mw_tranches", ["entry_time"])

    op.create_table(
        "mw_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "signal_event_id",
            sa.Integer(),
            sa.ForeignKey("mw_signal_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=96), nullable=False),
        sa.Column("symbol", sa.String(length=24), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("signal_code", sa.String(length=20), nullable=False),
        sa.Column("requested_lots", sa.Integer(), nullable=False),
        sa.Column("filled_lots", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("limit_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("budget_tl", sa.Numeric(18, 6), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("rejection_reason", sa.String(length=400), nullable=True),
        sa.Column("broker_name", sa.String(length=40), nullable=False),
        sa.Column("broker_order_id", sa.String(length=100), nullable=True),
        sa.Column(
            "target_tranche_id",
            sa.Integer(),
            sa.ForeignKey("mw_tranches.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("avg_fill_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(18, 6), nullable=True),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_mw_orders_idempotency_key"),
    )
    op.create_index("ix_mw_orders_symbol", "mw_orders", ["symbol"])
    op.create_index("ix_mw_orders_status", "mw_orders", ["status"])
    op.create_index("ix_mw_orders_created_at", "mw_orders", ["created_at"])

    op.create_foreign_key(
        "fk_mw_tranches_open_order",
        "mw_tranches",
        "mw_orders",
        ["open_order_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_mw_tranches_close_order",
        "mw_tranches",
        "mw_orders",
        ["close_order_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "mw_execution_reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "order_id",
            sa.Integer(),
            sa.ForeignKey("mw_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_mw_execution_reports_order_id", "mw_execution_reports", ["order_id"])
    op.create_index("ix_mw_execution_reports_created_at", "mw_execution_reports", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_mw_execution_reports_created_at", table_name="mw_execution_reports")
    op.drop_index("ix_mw_execution_reports_order_id", table_name="mw_execution_reports")
    op.drop_table("mw_execution_reports")

    op.drop_constraint("fk_mw_tranches_close_order", "mw_tranches", type_="foreignkey")
    op.drop_constraint("fk_mw_tranches_open_order", "mw_tranches", type_="foreignkey")

    op.drop_index("ix_mw_orders_created_at", table_name="mw_orders")
    op.drop_index("ix_mw_orders_status", table_name="mw_orders")
    op.drop_index("ix_mw_orders_symbol", table_name="mw_orders")
    op.drop_table("mw_orders")

    op.drop_index("ix_mw_tranches_entry_time", table_name="mw_tranches")
    op.drop_index("ix_mw_tranches_symbol_status", table_name="mw_tranches")
    op.drop_table("mw_tranches")

    op.drop_index("ix_mw_signal_events_bar_time", table_name="mw_signal_events")
    op.drop_index("ix_mw_signal_events_symbol", table_name="mw_signal_events")
    op.drop_table("mw_signal_events")
