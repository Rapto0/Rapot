from __future__ import annotations

import importlib
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_inventory_migration_quarantines_legacy_rows_and_downgrades(test_sandbox, monkeypatch):
    engine = sa.create_engine(f"sqlite+pysqlite:///{(test_sandbox / 'legacy.sqlite3').as_posix()}")
    metadata = sa.MetaData()
    orders = sa.Table(
        "mw_orders",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    tranches = sa.Table(
        "mw_tranches",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("open_order_id", sa.Integer),
        sa.Column("symbol", sa.String(24), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("entry_time", sa.DateTime, nullable=False),
    )
    sa.Index("ix_mw_tranches_symbol_status", tranches.c.symbol, tranches.c.status)
    sa.Index(
        "ix_mw_tranches_fifo_lookup",
        tranches.c.symbol,
        tranches.c.status,
        tranches.c.entry_time,
        tranches.c.id,
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            orders.insert(),
            [
                {"id": 1, "mode": "DRY_RUN", "created_at": datetime(2026, 1, 1)},
                {"id": 2, "mode": "LIVE", "created_at": datetime(2026, 1, 2)},
            ],
        )
        connection.execute(
            tranches.insert(),
            [
                {
                    "id": 1,
                    "open_order_id": 1,
                    "symbol": "BTCUSDT",
                    "status": "open",
                    "entry_time": datetime(2026, 1, 1),
                },
                {
                    "id": 2,
                    "open_order_id": 2,
                    "symbol": "ETHUSDT",
                    "status": "open",
                    "entry_time": datetime(2026, 1, 2),
                },
                {
                    "id": 3,
                    "open_order_id": None,
                    "symbol": "XRPUSDT",
                    "status": "open",
                    "entry_time": datetime(2026, 1, 3),
                },
            ],
        )

        migration = importlib.import_module(
            "middleware.infra.alembic.versions.20260907_0004_scope_inventory"
        )
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
        migration.upgrade()

        migrated_orders = connection.execute(
            sa.text("SELECT mode, inventory_scope FROM mw_orders ORDER BY id")
        ).all()
        migrated_tranches = connection.execute(
            sa.text("SELECT mode, inventory_scope FROM mw_tranches ORDER BY id")
        ).all()
        assert migrated_orders == [
            ("DRY_RUN", "LEGACY_UNCLASSIFIED"),
            ("LIVE", "LEGACY_UNCLASSIFIED"),
        ]
        assert migrated_tranches == [
            ("DRY_RUN", "LEGACY_UNCLASSIFIED"),
            ("LIVE", "LEGACY_UNCLASSIFIED"),
            ("LEGACY", "LEGACY_UNCLASSIFIED"),
        ]
        columns = {item["name"]: item for item in sa.inspect(connection).get_columns("mw_tranches")}
        assert columns["mode"]["nullable"] is False
        assert columns["inventory_scope"]["nullable"] is False

        recovery_migration = importlib.import_module(
            "middleware.infra.alembic.versions.20260907_0005_add_order_recovery_id"
        )
        monkeypatch.setattr(
            recovery_migration,
            "op",
            Operations(MigrationContext.configure(connection)),
        )
        recovery_migration.upgrade()
        order_columns = {
            item["name"]: item for item in sa.inspect(connection).get_columns("mw_orders")
        }
        order_constraints = {
            item["name"] for item in sa.inspect(connection).get_unique_constraints("mw_orders")
        }
        assert order_columns["client_order_id"]["nullable"] is True
        assert "uq_mw_orders_scope_client_order_id" in order_constraints
        assert connection.scalar(sa.text("SELECT COUNT(*) FROM mw_orders")) == 2

        recovery_migration.downgrade()
        migration.downgrade()
        assert {item["name"] for item in sa.inspect(connection).get_columns("mw_orders")} == {
            "id",
            "mode",
            "created_at",
        }
        assert connection.scalar(sa.text("SELECT COUNT(*) FROM mw_tranches")) == 3


def test_accounting_precision_migration_preserves_rows_and_downgrades(test_sandbox, monkeypatch):
    engine = sa.create_engine(
        f"sqlite+pysqlite:///{(test_sandbox / 'accounting-legacy.sqlite3').as_posix()}"
    )
    metadata = sa.MetaData()
    signal_events = sa.Table(
        "mw_signal_events",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("price", sa.Numeric(18, 6), nullable=False),
    )
    orders = sa.Table(
        "mw_orders",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("limit_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("budget_tl", sa.Numeric(18, 6)),
        sa.Column("avg_fill_price", sa.Numeric(18, 6)),
        sa.Column("realized_pnl", sa.Numeric(18, 6)),
    )
    tranches = sa.Table(
        "mw_tranches",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("entry_price", sa.Numeric(18, 6), nullable=False),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(signal_events.insert(), {"id": 1, "price": Decimal("1.123456")})
        connection.execute(
            orders.insert(),
            {
                "id": 1,
                "limit_price": Decimal("1.123456"),
                "budget_tl": Decimal("10"),
                "avg_fill_price": Decimal("1.123456"),
                "realized_pnl": Decimal("0.5"),
            },
        )
        connection.execute(tranches.insert(), {"id": 1, "entry_price": Decimal("1.123456")})

        migration = importlib.import_module(
            "middleware.infra.alembic.versions.20260907_0006_order_accounting_precision"
        )
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
        migration.upgrade()

        inspector = sa.inspect(connection)
        order_columns = {item["name"]: item for item in inspector.get_columns("mw_orders")}
        assert order_columns["limit_price"]["type"].scale == 12
        assert order_columns["commission_json"]["nullable"] is False
        assert order_columns["commission_complete"]["nullable"] is False
        assert connection.scalar(sa.text("SELECT commission_json FROM mw_orders")) == "{}"
        assert connection.scalar(sa.text("SELECT COUNT(*) FROM mw_orders")) == 1

        migration.downgrade()
        downgraded = {
            item["name"]: item for item in sa.inspect(connection).get_columns("mw_orders")
        }
        assert downgraded["limit_price"]["type"].scale == 6
        assert "commission_json" not in downgraded
        assert connection.scalar(sa.text("SELECT COUNT(*) FROM mw_orders")) == 1
