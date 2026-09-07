"""add deterministic client order id for recovery

Revision ID: 20260907_0005
Revises: 20260907_0004
Create Date: 2026-09-07 19:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260907_0005"
down_revision = "20260907_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mw_orders", sa.Column("client_order_id", sa.String(length=36), nullable=True))
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("mw_orders") as batch_op:
            batch_op.create_unique_constraint(
                "uq_mw_orders_scope_client_order_id",
                ["inventory_scope", "client_order_id"],
            )
        return
    op.create_unique_constraint(
        "uq_mw_orders_scope_client_order_id",
        "mw_orders",
        ["inventory_scope", "client_order_id"],
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("mw_orders") as batch_op:
            batch_op.drop_constraint("uq_mw_orders_scope_client_order_id", type_="unique")
            batch_op.drop_column("client_order_id")
        return
    op.drop_constraint("uq_mw_orders_scope_client_order_id", "mw_orders", type_="unique")
    op.drop_column("mw_orders", "client_order_id")
