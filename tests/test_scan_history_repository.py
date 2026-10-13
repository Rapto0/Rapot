from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, create_engine

import db_session
from infrastructure.persistence.ops_repository import save_scan_history
from infrastructure.repositories.system_repository import list_scan_history


@pytest.fixture(params=[False, True], ids=["legacy-sqlite", "previous-orm"])
def historical_engine(
    request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[Engine, bool]]:
    previous_orm = request.param
    engine = create_engine(f"sqlite:///{tmp_path / 'historical.sqlite3'}")
    extra_columns = ", mode VARCHAR(10), errors_count INTEGER" if previous_orm else ""
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE scan_history ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, scan_type TEXT NOT NULL, "
            "symbols_scanned INTEGER, signals_found INTEGER, duration_seconds REAL, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP" + extra_columns + ")"
        )
        connection.exec_driver_sql(
            "INSERT INTO scan_history "
            "(id, scan_type, symbols_scanned, signals_found, duration_seconds, created_at) "
            "VALUES (7, 'BIST', 123, 4, 5.25, '2026-01-01 12:00:00')"
        )
        if previous_orm:
            connection.exec_driver_sql(
                "INSERT INTO scan_history "
                "(id, scan_type, mode, symbols_scanned, signals_found, errors_count, "
                "duration_seconds, created_at) "
                "VALUES (8, 'Kripto', 'async', 80, 2, 3, 6.5, '2026-01-02 12:00:00')"
            )
    monkeypatch.setattr(db_session, "_engine", engine)
    monkeypatch.setattr(db_session, "_SessionFactory", None)
    monkeypatch.setattr(db_session, "_ScopedSession", None)
    try:
        yield engine, previous_orm
    finally:
        if db_session._ScopedSession is not None:
            db_session._ScopedSession.remove()
        engine.dispose()


def test_historical_schema_upgrade_is_repeatable_and_preserves_unknown_evidence(
    historical_engine: tuple[Engine, bool],
) -> None:
    engine, previous_orm = historical_engine
    with engine.connect() as connection:
        before = connection.exec_driver_sql(
            "SELECT id, scan_type, symbols_scanned, signals_found, duration_seconds, created_at "
            "FROM scan_history ORDER BY id"
        ).fetchall()

    db_session.init_db()
    db_session.init_db()

    with engine.connect() as connection:
        after = connection.exec_driver_sql(
            "SELECT id, scan_type, symbols_scanned, signals_found, duration_seconds, created_at "
            "FROM scan_history ORDER BY id"
        ).fetchall()
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(scan_history)")}
    assert after == before
    assert {"mode", "errors_count", "status"} <= columns
    scans = {row["id"]: row for row in list_scan_history(10)}
    assert scans[7]["mode"] == "unknown"
    assert scans[7]["errors_count"] is None
    assert scans[7]["status"] == "unknown"
    if previous_orm:
        assert scans[8]["mode"] == "async"
        assert scans[8]["errors_count"] == 3
        assert scans[8]["status"] == "unknown"
    new_id = save_scan_history(
        scan_type="Full",
        mode="sync",
        symbols_scanned=1,
        signals_found=0,
        errors_count=1,
        duration_seconds=0.25,
        status="partial",
    )
    assert new_id > max(row[0] for row in before)
    assert list_scan_history(1)[0]["status"] == "partial"
    assert len(list_scan_history(10)) == len(before) + 1


@pytest.mark.parametrize("status", ["success", "partial", "failed", "cancelled"])
@pytest.mark.parametrize("mode", ["sync", "async"])
def test_terminal_writer_commits_id_and_preserves_status_in_history(status: str, mode: str) -> None:
    scan_id = save_scan_history(
        scan_type="BIST",
        mode=mode,
        symbols_scanned=0,
        signals_found=0,
        errors_count=0,
        duration_seconds=0.0,
        status=status,
    )
    # Read using a separate raw connection to prove the writer committed before returning.
    with db_session.get_engine().connect() as connection:
        assert connection.exec_driver_sql(
            "SELECT id, status, errors_count FROM scan_history"
        ).fetchall() == [(scan_id, status, 0)]
    scan = list_scan_history(1)[0]
    assert scan["id"] == scan_id
    assert scan["status"] == status
    assert scan["mode"] == mode
    assert scan["errors_count"] == 0


def test_legacy_raw_insert_keeps_unknown_status_and_error_count() -> None:
    with db_session.get_engine().begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO scan_history "
            "(scan_type, symbols_scanned, signals_found, duration_seconds, created_at) "
            "VALUES ('BIST', 5, 0, 1.0, '2026-01-01 12:00:00')"
        )
    row = list_scan_history(1)[0]
    assert row["status"] == "unknown"
    assert row["mode"] == "unknown"
    assert row["errors_count"] is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "unknown"),
        ("status", "running"),
        ("mode", "unknown"),
        ("mode", "sync:success"),
        ("symbols_scanned", -1),
        ("signals_found", -1),
        ("errors_count", -1),
        ("errors_count", None),
        ("symbols_scanned", 1.5),
        ("signals_found", True),
        ("duration_seconds", -0.1),
        ("duration_seconds", float("nan")),
        ("duration_seconds", float("inf")),
        ("duration_seconds", True),
    ],
)
def test_terminal_writer_rejects_invalid_values_without_writing(field: str, value: Any) -> None:
    values = {
        "scan_type": "BIST",
        "mode": "sync",
        "symbols_scanned": 1,
        "signals_found": 0,
        "errors_count": 0,
        "duration_seconds": 1.0,
        "status": "success",
    }
    values[field] = value
    with pytest.raises(ValueError):
        save_scan_history(**values)
    assert list_scan_history(10) == []
