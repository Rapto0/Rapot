import pytest
import sqlalchemy as sa
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

from middleware.infra.schema import migrate_schema, migration_config, require_current_schema


def test_production_gate_rejects_missing_or_old_revision_and_accepts_head(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'schema.sqlite3'}")
    scripts = ScriptDirectory.from_config(migration_config())
    try:
        with pytest.raises(RuntimeError, match="not at Alembic head"):
            require_current_schema(engine)
        with engine.begin() as connection:
            MigrationContext.configure(connection).stamp(scripts, "20260907_0005")
        with pytest.raises(RuntimeError, match="not at Alembic head"):
            require_current_schema(engine)
        with engine.begin() as connection:
            MigrationContext.configure(connection).stamp(scripts, "head")
        require_current_schema(engine)
    finally:
        engine.dispose()


def test_existing_unversioned_tables_are_never_automatically_stamped(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'legacy.sqlite3'}")
    try:
        with engine.begin() as connection:
            connection.execute(sa.text("CREATE TABLE mw_orders (id INTEGER PRIMARY KEY)"))
            connection.execute(sa.text("INSERT INTO mw_orders (id) VALUES (7)"))
        with pytest.raises(RuntimeError, match="Automatic stamping is disabled"):
            migrate_schema(engine)
        with engine.connect() as connection:
            assert connection.scalar(sa.text("SELECT id FROM mw_orders")) == 7
            assert "alembic_version" not in sa.inspect(connection).get_table_names()
    finally:
        engine.dispose()
