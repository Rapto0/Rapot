"""harden fifo constraints and signal schema version

Revision ID: 20260423_0002
Revises: 20260423_0001
Create Date: 2026-04-23 12:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260423_0002"
down_revision = "20260423_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mw_signal_events",
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_check_constraint(
        "ck_mw_orders_requested_lots_non_negative",
        "mw_orders",
        "requested_lots >= 0",
    )
    op.create_check_constraint(
        "ck_mw_orders_filled_lots_non_negative",
        "mw_orders",
        "filled_lots >= 0",
    )
    op.create_check_constraint(
        "ck_mw_orders_filled_lots_lte_requested",
        "mw_orders",
        "filled_lots <= requested_lots",
    )

    op.create_unique_constraint(
        "uq_mw_tranches_open_order_id",
        "mw_tranches",
        ["open_order_id"],
    )
    op.create_check_constraint(
        "ck_mw_tranches_requested_lots_non_negative",
        "mw_tranches",
        "requested_lots >= 0",
    )
    op.create_check_constraint(
        "ck_mw_tranches_filled_lots_non_negative",
        "mw_tranches",
        "filled_lots >= 0",
    )
    op.create_check_constraint(
        "ck_mw_tranches_remaining_lots_non_negative",
        "mw_tranches",
        "remaining_lots >= 0",
    )
    op.create_check_constraint(
        "ck_mw_tranches_filled_lots_lte_requested",
        "mw_tranches",
        "filled_lots <= requested_lots",
    )
    op.create_check_constraint(
        "ck_mw_tranches_remaining_lots_lte_filled",
        "mw_tranches",
        "remaining_lots <= filled_lots",
    )
    op.create_index(
        "ix_mw_tranches_fifo_lookup",
        "mw_tranches",
        ["symbol", "status", "entry_time", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_mw_tranches_fifo_lookup", table_name="mw_tranches")
    op.drop_constraint("ck_mw_tranches_remaining_lots_lte_filled", "mw_tranches", type_="check")
    op.drop_constraint("ck_mw_tranches_filled_lots_lte_requested", "mw_tranches", type_="check")
    op.drop_constraint("ck_mw_tranches_remaining_lots_non_negative", "mw_tranches", type_="check")
    op.drop_constraint("ck_mw_tranches_filled_lots_non_negative", "mw_tranches", type_="check")
    op.drop_constraint("ck_mw_tranches_requested_lots_non_negative", "mw_tranches", type_="check")
    op.drop_constraint("uq_mw_tranches_open_order_id", "mw_tranches", type_="unique")

    op.drop_constraint("ck_mw_orders_filled_lots_lte_requested", "mw_orders", type_="check")
    op.drop_constraint("ck_mw_orders_filled_lots_non_negative", "mw_orders", type_="check")
    op.drop_constraint("ck_mw_orders_requested_lots_non_negative", "mw_orders", type_="check")

    op.drop_column("mw_signal_events", "schema_version")
