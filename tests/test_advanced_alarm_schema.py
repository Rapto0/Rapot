"""Additive schema acceptance against the accepted 876f3f37 source, entirely offline.

Frozen AST hashes allow the CI shallow checkout to check the actual old model
definitions without fetching Git history or trusting a second mutable fixture.
The eleventh production table (lost_and_found) is not an ORM model: its fixture
below is deliberately synthetic, not a copy or claim about production DDL/data.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import Boolean, DateTime, Float, Integer, create_engine, event, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateIndex, CreateTable

import db_session
from models import Base

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "876f3f37b9d56624d17c46ab924684de559c5530"
OLD_MODELS_BLOB_SHA256 = "4f18c6650ad5e0d6c7d45eab3bd4d5e4adc844975f69e80168278287651742c4"
OLD_MODELS_AST_SHA256 = "3bc237018083636f7482f9b77d8700f385aac4be40165d414c37275ffdb84f32"
OLD_INIT_AST_SHA256 = "a3bef026cde064b0a250c3523df5a39961b207ea7fff0447ec163ab14556eb9a"
ADDED_CLASSES = {
    "AdvancedAlarmWatchlist",
    "AdvancedAlarmRule",
    "AdvancedAlarmState",
    "AdvancedAlarmEvent",
}
ADDED_TABLES = {
    "advanced_alarm_watchlists",
    "advanced_alarm_rules",
    "advanced_alarm_states",
    "advanced_alarm_events",
}
OLD_TABLES = {
    "ai_analyses",
    "bot_stats",
    "orders",
    "research_workspaces",
    "scan_history",
    "server_alarm_events",
    "server_alarm_rules",
    "server_alarm_symbol_states",
    "signals",
    "trades",
}


def digest(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def baseline_metadata():
    tree = ast.parse((ROOT / "models.py").read_text(encoding="utf-8"))
    names = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
    assert names >= ADDED_CLASSES
    tree.body = [
        node
        for node in tree.body
        if not (isinstance(node, ast.ClassDef) and node.name in ADDED_CLASSES)
    ]
    # This checks every old model column, constraint, Python/server default,
    # relationship and declaration against the independently read accepted source.
    assert (
        hashlib.sha256(ast.dump(tree, include_attributes=False).encode()).hexdigest()
        == OLD_MODELS_AST_SHA256
    )
    namespace = {"__name__": "synthetic_876f3f37_models"}
    exec(compile(tree, "<verified-old-model-definitions>", "exec"), namespace)
    metadata = namespace["Base"].metadata
    assert set(metadata.tables) == OLD_TABLES
    init_tree = ast.parse((ROOT / "db_session.py").read_text(encoding="utf-8"))
    init_tree.body = [
        node
        for node in init_tree.body
        if isinstance(node, ast.FunctionDef) and node.name in {"init_db", "ensure_sqlite_columns"}
    ]
    assert (
        hashlib.sha256(ast.dump(init_tree, include_attributes=False).encode()).hexdigest()
        == OLD_INIT_AST_SHA256
    )
    return namespace["Base"]


def metadata_ddl(metadata, dialect, names) -> dict:
    return {
        name: {
            "table": str(CreateTable(metadata.tables[name]).compile(dialect=dialect)),
            "indexes": sorted(
                str(CreateIndex(index).compile(dialect=dialect))
                for index in metadata.tables[name].indexes
            ),
        }
        for name in sorted(names)
    }


def schema(connection, names: set[str] | None = None) -> dict:
    objects = [
        list(row)
        for row in connection.exec_driver_sql(
            "SELECT type,name,tbl_name,sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
        )
        if names is None or row[2] in names
    ]
    tables = sorted(row[1] for row in objects if row[0] == "table")
    details = {}
    for name in tables:
        # Every identifier originates in sqlite_master, never in request input.
        quoted = '"' + name.replace('"', '""') + '"'
        indexes = [list(row) for row in connection.exec_driver_sql(f"PRAGMA index_list({quoted})")]
        details[name] = {
            "columns": [
                list(row) for row in connection.exec_driver_sql(f"PRAGMA table_info({quoted})")
            ],
            "foreign_keys": [
                list(row)
                for row in connection.exec_driver_sql(f"PRAGMA foreign_key_list({quoted})")
            ],
            "indexes": indexes,
            "index_columns": {
                index[1]: [
                    list(row)
                    for row in connection.exec_driver_sql(
                        'PRAGMA index_xinfo("' + index[1].replace('"', '""') + '")'
                    )
                ]
                for index in indexes
            },
        }
    return {"objects": objects, "table_details": details}


def rows(connection, names) -> dict:
    result = {}
    for name in sorted(names):
        quoted = '"' + name.replace('"', '""') + '"'
        data = [
            [item.hex() if isinstance(item, bytes) else item for item in row]
            for row in connection.exec_driver_sql(f"SELECT * FROM {quoted}")
        ]
        result[name] = {"count": len(data), "rows_sha256": digest(sorted(data, key=digest))}
    return result


def fixture_row(table, index: int) -> dict:
    result = {}
    for column in table.columns:
        if column.foreign_keys:
            foreign = next(iter(column.foreign_keys)).column
            result[column.name] = fixture_row(foreign.table, index)[foreign.name]
        elif isinstance(column.type, Boolean):
            result[column.name] = index == 1
        elif isinstance(column.type, DateTime):
            result[column.name] = datetime(2026, 1, index, 10, 20, 30, 123456)
        elif isinstance(column.type, Integer):
            result[column.name] = index
        elif isinstance(column.type, Float):
            result[column.name] = 101.125 * index
        else:
            text = f"synthetic-{index}"
            limit = getattr(column.type, "length", None)
            result[column.name] = text[-limit:] if limit else text
    return result


def test_old_schema_rows_and_extra_table_survive_additive_init_twice(tmp_path, monkeypatch):
    baseline = baseline_metadata()
    engine = create_engine(f"sqlite:///{tmp_path / 'synthetic-additive.sqlite3'}")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    try:
        assert metadata_ddl(baseline.metadata, engine.dialect, OLD_TABLES) == metadata_ddl(
            Base.metadata, engine.dialect, OLD_TABLES
        )
        assert set(Base.metadata.tables) - OLD_TABLES == ADDED_TABLES
        monkeypatch.setattr(db_session, "get_engine", lambda: engine)
        with monkeypatch.context() as old:
            old.setattr(db_session, "Base", baseline)
            db_session.init_db()
        all_old = OLD_TABLES | {"lost_and_found"}
        with engine.begin() as connection:
            for table in baseline.metadata.sorted_tables:
                connection.execute(table.insert(), [fixture_row(table, 1), fixture_row(table, 2)])
            # An intentionally non-ORM legacy object tests that arbitrary pre-existing
            # recovery data, including BLOB values, indexes and triggers, is preserved.
            connection.exec_driver_sql(
                "CREATE TABLE lost_and_found (id INTEGER PRIMARY KEY, label TEXT NOT NULL, "
                "payload BLOB NOT NULL, recovered INTEGER NOT NULL CHECK(recovered IN (0,1)))"
            )
            connection.exec_driver_sql(
                "CREATE UNIQUE INDEX idx_synthetic_recovery_label ON lost_and_found(label)"
            )
            connection.exec_driver_sql(
                "CREATE TRIGGER synthetic_recovery_guard BEFORE DELETE ON lost_and_found "
                "BEGIN SELECT RAISE(ABORT, 'synthetic row must survive'); END"
            )
            connection.exec_driver_sql(
                "INSERT INTO lost_and_found VALUES(?,?,?,?)",
                (1, "synthetic-only", b"\x00\xffsynthetic", 1),
            )
            before_schema, before_rows = schema(connection), rows(connection, all_old)
            assert len(before_schema["table_details"]) == 11

        statements = []

        def record(_conn, _cursor, statement, _parameters, _context, _many):
            statements.append(statement.strip().split()[0].upper())

        event.listen(engine, "before_cursor_execute", record)
        db_session.init_db()
        with engine.connect() as connection:
            after_schema = schema(connection)
            after_existing = schema(connection, all_old)
            added_schema = schema(connection, ADDED_TABLES)
            after_rows = rows(connection, all_old)
            assert before_schema == after_existing
            assert before_rows == after_rows
            assert set(after_schema["table_details"]) - all_old == ADDED_TABLES
            assert all(item["count"] == 0 for item in rows(connection, ADDED_TABLES).values())
            assert connection.exec_driver_sql("PRAGMA integrity_check").scalar_one() == "ok"
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
        db_session.init_db()
        with engine.connect() as connection:
            assert schema(connection) == after_schema
            assert rows(connection, all_old) == before_rows
        event.remove(engine, "before_cursor_execute", record)
        assert not set(statements) & {"INSERT", "UPDATE", "DELETE", "REPLACE", "ALTER", "DROP"}

        constraints = assert_new_constraints(engine)
        with engine.connect() as connection:
            assert rows(connection, all_old) == before_rows
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
            assert connection.exec_driver_sql("PRAGMA integrity_check").scalar_one() == "ok"
        report = {
            "schema": "rapot-advanced-alarms-additive-schema-v1",
            "status": "verified_additive_create_all",
            "source_sha": "PENDING",
            "base_sha": BASE_SHA,
            "base_models_blob_sha256": OLD_MODELS_BLOB_SHA256,
            "base_models_ast_sha256": OLD_MODELS_AST_SHA256,
            "base_init_ast_sha256": OLD_INIT_AST_SHA256,
            "old_tables": sorted(all_old),
            "old_orm_tables": sorted(OLD_TABLES),
            "added_tables": sorted(ADDED_TABLES),
            "removed_tables": [],
            "synthetic_extra_table": "lost_and_found",
            "production_schema_equivalence_claimed": False,
            "existing_metadata_unchanged": True,
            "existing_schema_unchanged": True,
            "existing_rows_unchanged": True,
            "repeat_init_idempotent": True,
            "new_tables_initially_empty": True,
            "init_dml_or_alter_or_drop": False,
            "foreign_keys_valid": True,
            "integrity_check": "ok",
            "provider_calls": False,
            "production_database_used": False,
            "schema_fingerprint_format": "sorted-sqlite-master-and-pragmas-json-sha256-v1",
            "before_schema_sha256": digest(before_schema),
            "after_existing_schema_sha256": digest(after_existing),
            "after_schema_sha256": digest(after_schema),
            "added_schema_sha256": digest(added_schema),
            "added_schema": added_schema,
            "before_rows_sha256": digest(before_rows),
            "after_existing_rows_sha256": digest(after_rows),
            "fixture_rows": sum(item["count"] for item in before_rows.values()),
            "fixture_tables": before_rows,
            "new_constraints": constraints,
            "source_blob_sha256": {
                name: hashlib.sha256((ROOT / name).read_text(encoding="utf-8").encode()).hexdigest()
                for name in (
                    "models.py",
                    "db_session.py",
                    "database.py",
                    "scripts/runtime.py",
                    "api/main.py",
                    "tests/test_advanced_alarm_schema.py",
                )
            },
        }
        output = os.environ.get("RAPOT_SCHEMA_SCOPE_REPORT")
        if output:
            path = Path(output)
            assert path.is_absolute() and path.suffix == ".json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
    finally:
        engine.dispose()


def assert_new_constraints(engine) -> dict:
    inspector = inspect(engine)
    primary = {
        name: inspector.get_pk_constraint(name)["constrained_columns"]
        for name in sorted(ADDED_TABLES)
    }
    assert primary["advanced_alarm_states"] == ["rule_id", "revision", "symbol", "market_type"]
    assert all(primary[name] == ["id"] for name in ADDED_TABLES - {"advanced_alarm_states"})
    unique = inspector.get_unique_constraints("advanced_alarm_events")
    assert unique == [
        {
            "name": "uq_advanced_alarm_observation",
            "column_names": ["rule_id", "revision", "symbol", "market_type", "observation_id"],
        }
    ]
    indexes = inspector.get_indexes("advanced_alarm_events")
    assert any(
        index["name"] == "idx_advanced_alarm_delivery"
        and index["column_names"] == ["delivery_status", "next_attempt_at"]
        for index in indexes
    )
    with engine.begin() as connection:
        for name in sorted(ADDED_TABLES):
            table = Base.metadata.tables[name]
            row = fixture_row(table, 1)
            connection.execute(table.insert(), row)
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(table.insert(), row)
            required = next(
                column.name
                for column in table.columns
                if not column.nullable and not column.primary_key
            )
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(table.insert(), {**fixture_row(table, 3), required: None})
        events = Base.metadata.tables["advanced_alarm_events"]
        first = fixture_row(events, 1)
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(events.insert(), {**first, "id": 2})
        connection.execute(events.insert(), {**first, "id": 2, "revision": 2})
        states = Base.metadata.tables["advanced_alarm_states"]
        connection.execute(states.insert(), {**fixture_row(states, 1), "revision": 2})
    return {
        "primary_keys": primary,
        "event_observation_unique": unique[0]["column_names"],
        "delivery_index_verified": True,
        "duplicate_keys_rejected": True,
        "required_null_rejected": True,
        "distinct_revision_allowed": True,
        "declared_foreign_keys": {
            name: inspector.get_foreign_keys(name) for name in sorted(ADDED_TABLES)
        },
    }
