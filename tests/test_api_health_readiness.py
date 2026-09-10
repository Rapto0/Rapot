import asyncio
import threading
from contextlib import contextmanager

import pytest
from fastapi import Response
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
from starlette.requests import Request

import api.main as api_main
import db_session


def _request_stub() -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": "/health",
        "raw_path": b"/health",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
        "app": api_main.app,
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_health_returns_healthy_when_db_and_realtime_are_ready(monkeypatch):
    api_main._RUNTIME_STATE["db_ready"] = True
    api_main._RUNTIME_STATE["realtime_ready"] = True
    monkeypatch.setattr(db_session, "probe_database_readiness", lambda: None)

    response = Response()
    result = await api_main.health_check(_request_stub(), response)

    assert response.status_code == 200
    assert result.status == "healthy"
    assert result.database == "connected"
    assert result.realtime == "running"


@pytest.mark.asyncio
async def test_health_returns_503_when_db_probe_fails(monkeypatch):
    api_main._RUNTIME_STATE["db_ready"] = True
    api_main._RUNTIME_STATE["realtime_ready"] = True

    def _raise_db_error():
        raise RuntimeError("db-down")

    monkeypatch.setattr(db_session, "probe_database_readiness", _raise_db_error)

    response = Response()
    result = await api_main.health_check(_request_stub(), response)

    assert response.status_code == 503
    assert result.status == "unhealthy"
    assert result.database == "error"
    assert result.realtime == "running"


@pytest.mark.asyncio
async def test_health_returns_503_when_realtime_not_ready(monkeypatch):
    api_main._RUNTIME_STATE["db_ready"] = True
    api_main._RUNTIME_STATE["realtime_ready"] = False
    monkeypatch.setattr(db_session, "probe_database_readiness", lambda: None)

    response = Response()
    result = await api_main.health_check(_request_stub(), response)

    assert response.status_code == 503
    assert result.status == "unhealthy"
    assert result.database == "connected"
    assert result.realtime == "error"


@pytest.mark.asyncio
async def test_health_does_not_probe_before_startup_marks_database_ready(monkeypatch):
    api_main._RUNTIME_STATE.update(db_ready=False, realtime_ready=True)

    def unexpected_probe():
        pytest.fail("A readiness probe must not bypass the startup database gate")

    monkeypatch.setattr(db_session, "probe_database_readiness", unexpected_probe)
    response = Response()
    result = await api_main.health_check(_request_stub(), response)

    assert response.status_code == 503
    assert result.status == "unhealthy"
    assert result.database == "error"
    assert result.realtime == "running"


@pytest.mark.asyncio
async def test_health_checks_required_schema_in_one_session_without_counting_rows(monkeypatch):
    api_main._RUNTIME_STATE.update(db_ready=True, realtime_ready=True)
    engine = db_session.get_engine()
    statements = []
    session_threads = []
    original_session = db_session.get_session

    @contextmanager
    def observe_session():
        session_threads.append(threading.get_ident())
        with original_session() as session:
            yield session

    def observe_sql(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement.strip())

    def unexpected_counts():
        pytest.fail("Health must not query table row counts")

    monkeypatch.setattr(db_session, "get_session", observe_session)
    monkeypatch.setattr(db_session, "get_table_stats", unexpected_counts)
    event.listen(engine, "before_cursor_execute", observe_sql)
    try:
        response = Response()
        result = await api_main.health_check(_request_stub(), response)
    finally:
        event.remove(engine, "before_cursor_execute", observe_sql)

    assert response.status_code == 200
    assert result.status == "healthy"
    assert result.database == "connected"
    assert statements == [
        f"SELECT 1 FROM {table} LIMIT 0"
        for table in ("signals", "trades", "orders", "scan_history", "bot_stats", "ai_analyses")
    ]
    assert len(session_threads) == 1
    assert session_threads[0] != threading.get_ident()
    assert engine.pool.checkedout() == 0


@pytest.mark.parametrize(
    "missing_table", ["signals", "trades", "orders", "scan_history", "bot_stats", "ai_analyses"]
)
@pytest.mark.asyncio
async def test_health_returns_503_when_a_required_table_is_missing(missing_table):
    api_main._RUNTIME_STATE.update(db_ready=True, realtime_ready=True)
    engine = db_session.get_engine()
    with engine.begin() as connection:
        connection.exec_driver_sql(f"DROP TABLE {missing_table}")

    response = Response()
    result = await api_main.health_check(_request_stub(), response)

    assert response.status_code == 503
    assert result.status == "unhealthy"
    assert result.database == "error"
    assert result.realtime == "running"
    assert engine.pool.checkedout() == 0


@pytest.mark.asyncio
async def test_health_propagates_schema_query_failure_as_503_and_releases_connection():
    api_main._RUNTIME_STATE.update(db_ready=True, realtime_ready=True)
    engine = db_session.get_engine()

    def fail_query(_connection, _cursor, statement, _parameters, _context, _many):
        if statement == "SELECT 1 FROM orders LIMIT 0":
            raise OperationalError(statement, {}, RuntimeError("probe-query-failed"))

    event.listen(engine, "before_cursor_execute", fail_query)
    try:
        response = Response()
        result = await api_main.health_check(_request_stub(), response)
    finally:
        event.remove(engine, "before_cursor_execute", fail_query)

    assert response.status_code == 503
    assert result.status == "unhealthy"
    assert result.database == "error"
    assert result.realtime == "running"
    assert engine.pool.checkedout() == 0


@pytest.mark.asyncio
async def test_slow_readiness_probe_does_not_block_the_event_loop(monkeypatch):
    api_main._RUNTIME_STATE.update(db_ready=True, realtime_ready=True)
    entered = threading.Event()
    release = threading.Event()

    def slow_probe():
        entered.set()
        if not release.wait(timeout=2):
            raise RuntimeError("Event loop did not release the probe")

    async def independent_task() -> bool:
        while not entered.is_set():
            await asyncio.sleep(0.001)
        still_pending = not health_task.done()
        release.set()
        return still_pending

    monkeypatch.setattr(db_session, "probe_database_readiness", slow_probe)
    response = Response()
    health_task = asyncio.create_task(api_main.health_check(_request_stub(), response))
    try:
        assert await asyncio.wait_for(independent_task(), timeout=1)
    finally:
        release.set()
        result = await health_task

    assert response.status_code == 200
    assert result.status == "healthy"
