"""Deployment-time Alembic checks; never infer revisions for existing unversioned data."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, inspect


def migration_config() -> Config:
    root = Path(__file__).resolve().parents[2]
    cfg = Config(str(root / "middleware/infra/alembic.ini"))
    cfg.set_main_option("script_location", str(root / "middleware/infra/alembic"))
    return cfg


def require_current_schema(engine: Engine) -> None:
    expected = set(ScriptDirectory.from_config(migration_config()).get_heads())
    with engine.connect() as connection:
        current = set(MigrationContext.configure(connection).get_current_heads())
    if current != expected:
        raise RuntimeError("Middleware schema is not at Alembic head; run the migration service")


def migrate_schema(engine: Engine) -> None:
    with engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())
        revisions = MigrationContext.configure(connection).get_current_heads()
    if any(name.startswith("mw_") for name in tables) and not revisions:
        raise RuntimeError(
            "Unversioned middleware tables found; back up and verify their schema before "
            "an explicit migration baseline. Automatic stamping is disabled."
        )
    command.upgrade(migration_config(), "head")
    require_current_schema(engine)
