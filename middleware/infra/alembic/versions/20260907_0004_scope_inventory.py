"""scope middleware inventory by mode, venue, and account

Revision ID: 20260907_0004
Revises: 20260501_0003
Create Date: 2026-09-07 18:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260907_0004"
down_revision = "20260501_0003"
branch_labels = None
depends_on = None

LEGACY_SCOPE = "LEGACY_UNCLASSIFIED"


def _set_not_null(table_name: str, column_name: str, column_type: sa.TypeEngine) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column(
                column_name,
                existing_type=column_type,
                nullable=False,
            )
        return
    op.alter_column(
        table_name,
        column_name,
        existing_type=column_type,
        nullable=False,
    )


def upgrade() -> None:
    op.add_column("mw_orders", sa.Column("inventory_scope", sa.String(length=220)))
    op.add_column("mw_tranches", sa.Column("mode", sa.String(length=16)))
    op.add_column("mw_tranches", sa.Column("inventory_scope", sa.String(length=220)))

    # Historical account/venue identity cannot be proven from the stored rows. Keep it
    # quarantined until an operator deliberately classifies it outside this migration.
    op.execute(
        sa.text("UPDATE mw_orders SET inventory_scope = :scope").bindparams(scope=LEGACY_SCOPE)
    )
    op.execute(
        sa.text(
            "UPDATE mw_tranches SET "
            "mode = COALESCE((SELECT mode FROM mw_orders "
            "WHERE mw_orders.id = mw_tranches.open_order_id), 'LEGACY'), "
            "inventory_scope = :scope"
        ).bindparams(scope=LEGACY_SCOPE)
    )

    _set_not_null("mw_orders", "inventory_scope", sa.String(length=220))
    _set_not_null("mw_tranches", "mode", sa.String(length=16))
    _set_not_null("mw_tranches", "inventory_scope", sa.String(length=220))

    op.create_index(
        "ix_mw_orders_inventory_scope_created_at",
        "mw_orders",
        ["inventory_scope", "created_at"],
    )
    op.drop_index("ix_mw_tranches_symbol_status", table_name="mw_tranches")
    op.drop_index("ix_mw_tranches_fifo_lookup", table_name="mw_tranches")
    op.create_index(
        "ix_mw_tranches_symbol_status",
        "mw_tranches",
        ["inventory_scope", "symbol", "status"],
    )
    op.create_index(
        "ix_mw_tranches_fifo_lookup",
        "mw_tranches",
        ["inventory_scope", "symbol", "status", "entry_time", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_mw_tranches_fifo_lookup", table_name="mw_tranches")
    op.drop_index("ix_mw_tranches_symbol_status", table_name="mw_tranches")
    op.create_index(
        "ix_mw_tranches_symbol_status",
        "mw_tranches",
        ["symbol", "status"],
    )
    op.create_index(
        "ix_mw_tranches_fifo_lookup",
        "mw_tranches",
        ["symbol", "status", "entry_time", "id"],
    )
    op.drop_index("ix_mw_orders_inventory_scope_created_at", table_name="mw_orders")

    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("mw_tranches") as batch_op:
            batch_op.drop_column("inventory_scope")
            batch_op.drop_column("mode")
        with op.batch_alter_table("mw_orders") as batch_op:
            batch_op.drop_column("inventory_scope")
        return
    op.drop_column("mw_tranches", "inventory_scope")
    op.drop_column("mw_tranches", "mode")
    op.drop_column("mw_orders", "inventory_scope")
