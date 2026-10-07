"""Synthetic shared market contract; no vendor credentials, network or real prices."""

from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import borsapy_market_routes as routes
from application.services.borsapy_gateway import BorsapyGatewayError
from application.services.borsapy_market_data import (
    BorsapyMarketData,
    instrument,
    performance_anchors,
    quote_performance,
)


def frame():
    return pd.DataFrame(
        {"Open": 10.0, "High": 12.0, "Low": 9.0, "Close": 11.0, "Volume": 3.0},
        index=pd.date_range("2026-01-01", periods=65, tz="Europe/Istanbul"),
    )


class Gateway:
    epoch = 1

    def data_epoch(self):
        return self.epoch

    def quote_snapshot(self, pairs):
        return {
            f"{exchange}:{symbol}": {
                "price": 12.0,
                "change": 1.0,
                "change_pct": 2.0,
                "state": "ok",
                "source": "borsapy_tradingview",
                "provider_time": "2026-01-08T12:00:00+03:00",
                "received_at": "2026-01-01T12:00:10Z",
                "realtime_verified": False,
            }
            for exchange, symbol in pairs
        }

    def history(self, *args, **kwargs):
        return frame()


def test_symbol_identity_never_substitutes_future_crypto_or_unknown_market():
    assert instrument("THYAO.IS")[:2] == ("BIST", "THYAO")
    assert instrument("XAUUSD=X")[:2] == ("OANDA", "XAUUSD")
    assert instrument("WTI")[:2] == ("TVC", "USOIL")
    for symbol in ["CL=F", "GC=F", "BTCUSDT", "UNKNOWN", "../secret.IS"]:
        assert instrument(symbol) is None


def test_quotes_keep_partial_states_and_never_fallback():
    service = BorsapyMarketData(Gateway())
    rows = service.quotes(["THYAO.IS", "UNKNOWN"])
    assert rows[0]["regularMarketPrice"] == 12
    assert rows[1]["state"] == "unsupported" and rows[1]["regularMarketPrice"] is None
    service.gateway.quote_snapshot = lambda _: (_ for _ in ()).throw(
        BorsapyGatewayError("Bağlantı gerekli", 409)
    )
    rows = service.quotes(["THYAO.IS", "UNKNOWN"])
    assert rows[0]["state"] == "auth_required" and rows[0]["regularMarketPrice"] is None
    assert rows[1]["state"] == "unsupported"


def test_history_returns_calendar_day_anchors_and_missing_is_not_zero():
    data = frame().iloc[:8]
    values = performance_anchors(data)
    assert values["anchor_7"] == 11
    assert values["anchor_30"] is None
    assert len(values["history"]) == 8
    assert values["history_time"].endswith("+03:00")


def test_metric_cache_scoped_to_connection_epoch_and_errors_are_not_signal_prices():
    gateway = Gateway()
    service = BorsapyMarketData(gateway)
    service._stop.set()  # deterministic preloaded history fixture, no worker
    service._history[(1, "THYAO", "BIST")] = (
        service._clock(),
        {
            "history_state": "ok",
            "anchor_7": 6,
            "closes": [("2026-01-01T00:00:00+03:00", 6.0)],
            "anchor_30": None,
            "history_time": "2026-01-01T00:00:00+03:00",
            "history_received_at": "2026-01-02T00:00:00Z",
        },
    )
    first = service.metrics(["BIST:THYAO"])["BIST:THYAO"]
    assert first["perf_7d"] == 100 and first["perf_30d"] is None
    gateway.epoch = 2
    changed = service.metrics(["BIST:THYAO"])["BIST:THYAO"]
    assert changed["history_state"] == "waiting" and changed["perf_7d"] is None
    with pytest.raises(BorsapyGatewayError):
        service.metrics(["Kripto:BTCUSDT"])


def test_grouped_bist_candles_preserve_prices_timezone_and_provenance():
    service = BorsapyMarketData(Gateway())
    result = service.candles("THYAO", "2wk", 4)
    assert result["count"] == 4 and result["timeframe"] == "2wk"
    assert result["source"] == "borsapy_tradingview" and result["adjustment"] == "splits"
    assert result["candles"][-1]["time"].endswith("+03:00")
    assert result["candles"][-1]["close"] == 11
    with pytest.raises(BorsapyGatewayError):
        service.candles("THYAO", "unknown")


@pytest.mark.parametrize("interval", ["1d", "2wk"])
@pytest.mark.parametrize("verified", [True, False, None])
def test_chart_volume_requires_provenance_and_keeps_real_zero(interval, verified):
    data = frame()
    data["Volume"] = 0.0
    if verified is not None:
        data.attrs["volume_verified"] = verified
        data.attrs["volume_unavailable_rows"] = 0 if verified else len(data)
    gateway = Gateway()
    gateway.history = lambda *args, **kwargs: data.copy()
    result = BorsapyMarketData(gateway).candles("THYAO", interval, 4)
    assert result["count"] == 4
    assert all(bar["close"] == 11 for bar in result["candles"])
    assert result["volume_quality"]["verified"] is (verified is True)
    assert [bar["volume"] for bar in result["candles"]] == [0.0 if verified else None] * 4
    assert result["volume_quality"]["state"] == (
        "verified" if verified else "unavailable" if verified is False else "unverified"
    )


@pytest.mark.parametrize(
    "path",
    [
        "indices?symbol=THYAO.IS",
        "metrics?key=BIST:THYAO",
        "ticker",
        "overview",
        "status",
        "crypto-metrics?key=Kripto:BTCUSDT",
    ],
)
def test_all_new_routes_admin_only_and_uncacheable(api_auth_users, path, monkeypatch):
    app = FastAPI()
    app.include_router(routes.router)
    monkeypatch.setattr(
        routes, "get_borsapy_market_data", lambda: pytest.fail("No provider on denied request")
    )
    with TestClient(app) as client:
        response = client.get("/borsapy/market/" + path)
        assert (
            response.status_code == 401 and response.headers["cache-control"] == "private, no-store"
        )
        token = api_auth_users.create_access_token({"sub": "user"})
        response = client.get(
            "/borsapy/market/" + path, headers={"Authorization": "Bearer " + token}
        )
        assert response.status_code == 403


def test_request_bounds_fail_before_market_access(api_auth_users, monkeypatch):
    app = FastAPI()
    app.include_router(routes.router)
    monkeypatch.setattr(
        routes, "get_borsapy_market_data", lambda: pytest.fail("Must validate first")
    )
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer " + api_auth_users.create_access_token(
            {"sub": "admin"}
        )
        for query in [[], [("symbol", "THYAO.IS")] * 51]:
            result = client.get("/borsapy/market/indices", params=query)
            assert result.status_code == 422
            assert result.headers["cache-control"] == "private, no-store"


def test_binance_missing_quote_not_replaced_with_bist_or_zero(monkeypatch):
    import websocket_manager

    monkeypatch.setattr(websocket_manager, "ws_manager", SimpleNamespace(get_ticker=lambda _: None))
    service = BorsapyMarketData(Gateway())
    result = service.crypto_metrics(["Kripto:BTCUSDT"])["Kripto:BTCUSDT"]
    assert result["source"] == "binance" and result["state"] == "waiting"
    assert result["latest_price"] is None and result["perf_7d"] is None


def test_performance_uses_quote_calendar_date_in_history_timezone():
    history = {"closes": [("2026-01-01T00:00:00+03:00", 5), ("2026-01-02T00:00:00+03:00", 10)]}
    # Jan 9 in Istanbul, despite UTC still being Jan 8. Baseline is Jan 2.
    result = quote_performance(15, "2026-01-08T23:00:00Z", history)
    assert result["perf_7d"] == 50
    assert result["perf_30d"] is None
    # A very old cached end cannot masquerade as a current 7-day return.
    assert quote_performance(15, "2026-02-09T12:00:00Z", history)["perf_7d"] is None


@pytest.mark.parametrize("bad", [float("inf"), float("nan"), -1, 0])
def test_invalid_history_never_reaches_metric_output(bad):
    data = frame()
    data.loc[data.index[0], "Close"] = bad
    with pytest.raises(ValueError):
        performance_anchors(data)


def test_service_recreated_after_application_lifecycle_close(monkeypatch):
    from application.services import borsapy_market_data as module

    previous = BorsapyMarketData(Gateway())
    monkeypatch.setattr(module, "_market", previous)
    assert module.get_borsapy_market_data() is previous
    previous.close()
    restarted = module.get_borsapy_market_data()
    assert restarted is not previous and not restarted._stop.is_set()
    restarted.close()
