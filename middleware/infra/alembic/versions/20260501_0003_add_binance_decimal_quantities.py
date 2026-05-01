"""add binance decimal quantity columns

Revision ID: 20260501_0003
Revises: 20260423_0002
Create Date: 2026-05-01 13:30:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260501_0003"
down_revision = "20260423_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mw_orders",
        sa.Column(
            "requested_quantity",
            sa.Numeric(28, 12),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "mw_orders",
        sa.Column("filled_quantity", sa.Numeric(28, 12), nullable=False, server_default="0"),
    )
    op.add_column("mw_orders", sa.Column("quote_budget", sa.Numeric(28, 12), nullable=True))
    op.add_column("mw_orders", sa.Column("base_asset", sa.String(length=20), nullable=True))
    op.add_column("mw_orders", sa.Column("quote_asset", sa.String(length=20), nullable=True))

    op.add_column(
        "mw_tranches",
        sa.Column(
            "requested_quantity",
            sa.Numeric(28, 12),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "mw_tranches",
        sa.Column("filled_quantity", sa.Numeric(28, 12), nullable=False, server_default="0"),
    )
    op.add_column(
        "mw_tranches",
        sa.Column("remaining_quantity", sa.Numeric(28, 12), nullable=False, server_default="0"),
    )

    op.execute(
        "UPDATE mw_orders SET requested_quantity = requested_lots, "
        "filled_quantity = filled_lots WHERE requested_quantity = 0"
    )
    op.execute(
        "UPDATE mw_tranches SET requested_quantity = requested_lots, "
        "filled_quantity = filled_lots, remaining_quantity = remaining_lots "
        "WHERE requested_quantity = 0"
    )


def downgrade() -> None:
    op.drop_column("mw_tranches", "remaining_quantity")
    op.drop_column("mw_tranches", "filled_quantity")
    op.drop_column("mw_tranches", "requested_quantity")

    op.drop_column("mw_orders", "quote_asset")
    op.drop_column("mw_orders", "base_asset")
    op.drop_column("mw_orders", "quote_budget")
    op.drop_column("mw_orders", "filled_quantity")
    op.drop_column("mw_orders", "requested_quantity")
