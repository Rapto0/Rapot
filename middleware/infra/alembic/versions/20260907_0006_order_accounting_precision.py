"""add commission accounting and twelve-decimal prices

Revision ID: 20260907_0006
Revises: 20260907_0005
Create Date: 2026-09-07 20:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260907_0006"
down_revision = "20260907_0005"
branch_labels = None
depends_on = None

OLD_PRICE = sa.Numeric(18, 6)
NEW_PRICE = sa.Numeric(28, 12)


def _alter_prices(new_type: sa.Numeric, old_type: sa.Numeric) -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("mw_signal_events") as batch_op:
            batch_op.alter_column("price", existing_type=old_type, type_=new_type)
        with op.batch_alter_table("mw_orders") as batch_op:
            for column in ("limit_price", "budget_tl", "avg_fill_price", "realized_pnl"):
                batch_op.alter_column(column, existing_type=old_type, type_=new_type)
        with op.batch_alter_table("mw_tranches") as batch_op:
            batch_op.alter_column("entry_price", existing_type=old_type, type_=new_type)
        return

    op.alter_column("mw_signal_events", "price", existing_type=old_type, type_=new_type)
    for column in ("limit_price", "budget_tl", "avg_fill_price", "realized_pnl"):
        op.alter_column("mw_orders", column, existing_type=old_type, type_=new_type)
    op.alter_column("mw_tranches", "entry_price", existing_type=old_type, type_=new_type)


def upgrade() -> None:
    _alter_prices(NEW_PRICE, OLD_PRICE)
    op.add_column(
        "mw_orders",
        sa.Column("commission_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "mw_orders",
        sa.Column("commission_complete", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("mw_orders", "commission_complete")
    op.drop_column("mw_orders", "commission_json")
    _alter_prices(OLD_PRICE, NEW_PRICE)
