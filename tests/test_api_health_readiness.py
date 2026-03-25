import pytest
from fastapi import Response
from starlette.requests import Request

import api.main as api_main


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
    monkeypatch.setattr("db_session.get_table_stats", lambda: {"signals": 1})

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

    monkeypatch.setattr("db_session.get_table_stats", _raise_db_error)

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
    monkeypatch.setattr("db_session.get_table_stats", lambda: {"signals": 1})

    response = Response()
    result = await api_main.health_check(_request_stub(), response)

    assert response.status_code == 503
    assert result.status == "unhealthy"
    assert result.database == "connected"
    assert result.realtime == "error"
