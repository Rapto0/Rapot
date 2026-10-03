"""Private research boundaries and durable inputs with no external account calls."""

from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import borsapy_routes as routes
from infrastructure.repositories import research_workspace_repository as saved


@pytest.fixture
def client(api_auth_users):
    app = FastAPI()
    app.include_router(routes.router)
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer " + api_auth_users.create_access_token(
            {"sub": "admin"}
        )
        yield client


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("get", "/borsapy/catalog", None),
        ("post", "/borsapy/query", {"operation": "search", "params": {}}),
        ("get", "/borsapy/candles/THYAO", None),
        ("get", "/borsapy/saved", None),
        ("post", "/borsapy/saved", {"name": "Örnek", "operation": "search", "params": {}}),
        ("delete", "/borsapy/saved/missing", None),
    ],
)
def test_every_research_route_requires_admin(client, api_auth_users, method, path, body):
    client.headers.pop("Authorization")
    kwargs = {"json": body} if body else {}
    assert getattr(client, method)(path, **kwargs).status_code == 401
    client.headers["Authorization"] = "Bearer " + api_auth_users.create_access_token(
        {"sub": "user"}
    )
    assert getattr(client, method)(path, **kwargs).status_code == 403


def test_invalid_operation_and_secret_field_never_reach_provider(client, monkeypatch):
    from application.services import borsapy_gateway

    def forbidden():
        pytest.fail("Provider must not be initialized for invalid input")

    monkeypatch.setattr(borsapy_gateway, "get_borsapy_gateway", forbidden)
    response = client.post("/borsapy/query", json={"operation": "unknown", "params": {}})
    assert response.status_code == 422
    response = client.post(
        "/borsapy/query", json={"operation": "search", "params": {"session": "secret"}}
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "operation,params,uses_tv,auth",
    [
        ("fund.history", {}, False, False),
        ("history", {}, True, True),
        ("fx.history", {"interval": "1d"}, False, False),
        ("fx.history", {"interval": "1m", "period": "1d"}, True, True),
    ],
)
def test_research_auth_depends_on_actual_data_source(
    client, monkeypatch, operation, params, uses_tv, auth
):
    from application.services import borsapy_gateway

    calls = []

    def run(callback, **kwargs):
        calls.append(kwargs)
        return {"operation": operation}

    monkeypatch.setattr(borsapy_gateway, "get_borsapy_gateway", lambda: SimpleNamespace(run=run))
    response = client.post("/borsapy/query", json={"operation": operation, "params": params})
    assert response.status_code == 200
    assert calls == [{"tradingview": uses_tv, "require_auth": auth}]


def test_saved_research_is_durable_and_owner_scoped():
    payload = {"name": "Portföyüm", "operation": "portfolio", "params": {"positions": []}}
    created = saved.save_workspace("alice", payload)
    assert saved.list_workspaces("alice")[0] == created
    assert saved.list_workspaces("bob") == []
    with pytest.raises(LookupError):
        saved.save_workspace("bob", payload, created["id"])
    with pytest.raises(LookupError):
        saved.delete_workspace("bob", created["id"])
    updated = saved.save_workspace("alice", {**payload, "name": "Yeni ad"}, created["id"])
    assert updated["name"] == "Yeni ad"
    saved.delete_workspace("alice", created["id"])
    assert saved.list_workspaces("alice") == []


def test_research_schema_addition_is_idempotent_and_preserves_existing_rows():
    from sqlalchemy import inspect

    from db_session import get_engine, init_db
    from models import ResearchWorkspace

    engine = get_engine()
    ResearchWorkspace.__table__.drop(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE legacy_probe (id INTEGER PRIMARY KEY, value TEXT)")
        connection.exec_driver_sql("INSERT INTO legacy_probe VALUES (1, 'preserve-me')")
    before = set(inspect(engine).get_table_names())
    init_db()
    init_db()
    assert set(inspect(engine).get_table_names()) == before | {"research_workspaces"}
    with engine.connect() as connection:
        assert (
            connection.exec_driver_sql("SELECT value FROM legacy_probe").scalar() == "preserve-me"
        )
    payload = {"name": "Kalıcı", "operation": "search", "params": {"query": "THY"}}
    created = saved.save_workspace("schema-owner", payload)
    init_db()
    assert saved.list_workspaces("schema-owner") == [created]


def test_private_chart_uses_authenticated_gateway_and_sanitizes_failures(client, monkeypatch):
    from application.services import borsapy_gateway

    frame = pd.DataFrame(
        {"Open": [10.0], "High": [12.0], "Low": [9.0], "Close": [11.0], "Volume": [100]},
        index=pd.date_range("2026-10-02", periods=1, tz="Europe/Istanbul"),
    )
    calls = []

    def history(symbol, **kwargs):
        calls.append((symbol, kwargs))
        return frame

    monkeypatch.setattr(
        borsapy_gateway, "get_borsapy_gateway", lambda: SimpleNamespace(history=history)
    )
    response = client.get("/borsapy/candles/THYAO?interval=1m&limit=20")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json()["candles"][0]["close"] == 11
    assert calls[0][1] == {"interval": "1m", "period": "5d"}
    assert client.get("/borsapy/candles/THYAO?interval=3m").status_code == 422
    assert len(calls) == 1

    def failing(*args, **kwargs):
        raise RuntimeError("cookie=session-secret&token=private")

    monkeypatch.setattr(
        borsapy_gateway, "get_borsapy_gateway", lambda: SimpleNamespace(history=failing)
    )
    response = client.get("/borsapy/candles/THYAO")
    assert response.status_code == 502
    assert "session-secret" not in response.text


def test_selected_borsapy_alarm_data_never_falls_back(monkeypatch):
    from application.services import borsapy_gateway
    from application.services.server_alarm_evaluator import (
        AlarmEvaluationError,
        PublicAlarmDataProvider,
    )
    from settings import settings

    monkeypatch.setattr(settings, "borsapy_use_for_bist", True)

    def failing(*args, **kwargs):
        raise RuntimeError("private-token")

    monkeypatch.setattr(
        borsapy_gateway, "get_borsapy_gateway", lambda: SimpleNamespace(history=failing)
    )
    with pytest.raises(AlarmEvaluationError, match="başka kaynağa geçilmedi"):
        PublicAlarmDataProvider().fetch_bars(symbol="THYAO", market_type="BIST", timeframe="1d")


def test_selected_scanner_data_keeps_provider_and_fetch_freshness(monkeypatch):
    import data_loader
    from application.services import borsapy_gateway
    from settings import settings

    monkeypatch.setattr(settings, "borsapy_use_for_bist", True)
    frame = pd.DataFrame(
        {"Open": [10.0], "High": [12.0], "Low": [9.0], "Close": [11.0], "Volume": [100]},
        index=pd.date_range("2026-10-02 10:00", periods=1, tz="Europe/Istanbul"),
    )
    monkeypatch.setattr(
        borsapy_gateway,
        "get_borsapy_gateway",
        lambda: SimpleNamespace(history=lambda *args, **kwargs: frame),
    )
    result = data_loader.get_bist_data("THYAO")
    assert result.attrs["source_hint"] == "borsapy_tradingview"
    assert result.attrs["open_quality"] == "provider"
    assert data_loader.is_dataframe_fresh(result, max_age_seconds=60)
    assert result.index[0] == pd.Timestamp("2026-10-02")
    assert frame.index[0].hour == 10


def test_authenticated_bist_data_bypasses_the_public_price_cache(monkeypatch):
    import data_loader
    import price_cache
    from settings import settings

    monkeypatch.setattr(settings, "borsapy_use_for_bist", True)
    private_frame = pd.DataFrame({"Close": [999]})
    monkeypatch.setattr(data_loader, "get_bist_data", lambda *a, **k: private_frame)

    def forbidden(*args, **kwargs):
        pytest.fail("Private TradingView data cannot use the public price cache")

    monkeypatch.setattr(price_cache.price_cache, "get", forbidden)
    monkeypatch.setattr(price_cache.price_cache, "set", forbidden)
    assert price_cache.cached_get_bist_data("THYAO") is private_frame


@pytest.mark.asyncio
async def test_public_candles_explicitly_use_legacy_source_when_private_jobs_enabled(monkeypatch):
    import logging

    import data_loader
    from application.services.market_data_service import build_candles_payload
    from settings import settings

    monkeypatch.setattr(settings, "borsapy_use_for_bist", True)
    calls = []

    def public_history(symbol, start_date, *, use_borsapy):
        calls.append(use_borsapy)
        assert use_borsapy is False
        frame = pd.DataFrame(
            {"Open": [10.0], "High": [12.0], "Low": [9.0], "Close": [11.0], "Volume": [100]},
            index=pd.date_range("2026-10-02", periods=1),
        )
        frame.attrs["source_hint"] = "isyatirim"
        return frame

    monkeypatch.setattr(data_loader, "get_bist_data", public_history)
    result = await build_candles_payload(
        symbol="THYAO",
        market_type="BIST",
        timeframe="1d",
        limit=100,
        provider=SimpleNamespace(),
        logger=logging.getLogger(__name__),
    )
    assert calls == [False]
    assert result["source"] == "isyatirim"
    assert result["candles"][0]["close"] == 11


def test_borsapy_daily_data_normalizes_session_date_for_existing_alarm_contract(monkeypatch):
    from application.services import borsapy_gateway
    from application.services.server_alarm_evaluator import PublicAlarmDataProvider
    from settings import settings

    monkeypatch.setattr(settings, "borsapy_use_for_bist", True)
    index = pd.date_range("2026-10-02 10:00", periods=1, tz="Europe/Istanbul")
    frame = pd.DataFrame(
        {
            key: [value]
            for key, value in {"Open": 10, "High": 12, "Low": 9, "Close": 11, "Volume": 100}.items()
        },
        index=index,
    )
    monkeypatch.setattr(
        borsapy_gateway,
        "get_borsapy_gateway",
        lambda: SimpleNamespace(history=lambda *args, **kwargs: frame),
    )
    result = PublicAlarmDataProvider().fetch_bars(
        symbol="THYAO", market_type="BIST", timeframe="1d"
    )
    assert result.index[0].hour == 0
    assert frame.index[0].hour == 10
    assert result.attrs == {"source": "borsapy_tradingview", "timeframe": "1d"}
