from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest
from starlette.requests import Request

import api.main as api_main


def _request_stub(path: str) -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
        "app": api_main.app,
    }
    return Request(scope)


class DummyQuery:
    def __init__(self, rows: list[Any]):
        self._rows = list(rows)

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def limit(self, count: int):
        self._rows = self._rows[:count]
        return self

    def all(self):
        return list(self._rows)


class DummySession:
    def __init__(self, mapping: dict[Any, list[Any]]):
        self._mapping = mapping

    def query(self, model: Any):
        return DummyQuery(self._mapping.get(model, []))


def _build_session_factory(mapping: dict[Any, list[Any]]):
    @contextmanager
    def _session_cm():
        yield DummySession(mapping)

    return _session_cm


@pytest.mark.asyncio
async def test_signals_endpoint_contract_smoke(monkeypatch):
    from models import Signal

    signal_row = SimpleNamespace(
        id=101,
        symbol="THYAO",
        market_type="BIST",
        strategy="HUNTER",
        signal_type="AL",
        timeframe="1D",
        score="8/10",
        price=302.15,
        created_at=datetime(2026, 3, 29, 10, 0, 0),
        special_tag="COK_UCUZ",
        details={"TopScore": "8/10"},
    )

    monkeypatch.setattr("db_session.get_session", _build_session_factory({Signal: [signal_row]}))

    response = await api_main.get_signals(
        _request_stub("/signals"),
        symbol=None,
        strategy=None,
        signal_type=None,
        market_type=None,
        special_tag=None,
        limit=10,
    )

    assert len(response) == 1
    assert response[0].id == 101
    assert response[0].symbol == "THYAO"
    assert response[0].market_type == "BIST"
    assert response[0].special_tag == "COK_UCUZ"


@pytest.mark.asyncio
async def test_trades_endpoint_contract_smoke(monkeypatch):
    from models import Trade

    trade_row = SimpleNamespace(
        id=11,
        symbol="BTCUSDT",
        market_type="Kripto",
        direction="BUY",
        price=62000.0,
        quantity=0.01,
        pnl=12.5,
        status="OPEN",
        created_at=datetime(2026, 3, 29, 11, 0, 0),
    )

    monkeypatch.setattr("db_session.get_session", _build_session_factory({Trade: [trade_row]}))

    response = await api_main.get_trades(
        _request_stub("/trades"),
        symbol=None,
        status=None,
        limit=10,
    )

    assert len(response) == 1
    assert response[0].id == 11
    assert response[0].symbol == "BTCUSDT"
    assert response[0].status == "OPEN"


def _sample_history_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "Close": [101.0, 103.0],
        },
        index=pd.to_datetime(["2026-03-28 10:00:00", "2026-03-29 10:00:00"]),
    )


@pytest.mark.asyncio
async def test_market_overview_contract_smoke(monkeypatch):
    api_main._market_overview_cache = None
    monkeypatch.setattr(
        api_main, "_fetch_history_with_fallback", lambda *args, **kwargs: _sample_history_frame()
    )

    response = await api_main.get_market_overview(_request_stub("/market/overview"))

    assert set(response.keys()) == {"bist", "crypto"}
    assert all(
        "currentValue" in item and "change" in item and "history" in item
        for item in response.values()
    )


@pytest.mark.asyncio
async def test_market_ticker_contract_smoke(monkeypatch):
    api_main._market_ticker_cache = None
    monkeypatch.setattr(
        api_main, "_fetch_history_with_fallback", lambda *args, **kwargs: _sample_history_frame()
    )

    response = await api_main.get_market_ticker(_request_stub("/market/ticker"))

    assert len(response) > 0
    first = response[0]
    assert {"symbol", "name", "price", "change", "changePercent"} <= set(first.keys())


@pytest.mark.asyncio
async def test_candles_contract_smoke_for_crypto_intraday(monkeypatch):
    fake_klines = [
        [1711700000000, "100", "105", "98", "102", "1000", 1711700059999, "0", "0", "0", "0", "0"],
        [1711703600000, "102", "106", "101", "104", "1200", 1711703659999, "0", "0", "0", "0", "0"],
        [1711707200000, "104", "108", "103", "107", "900", 1711707259999, "0", "0", "0", "0", "0"],
    ]
    monkeypatch.setattr(api_main, "_fetch_binance_klines", lambda *_args, **_kwargs: fake_klines)

    response = await api_main.get_candles(
        _request_stub("/candles/BTCUSDT"),
        symbol="BTCUSDT",
        market_type="Kripto",
        timeframe="1h",
        limit=3,
    )

    assert response["symbol"] == "BTCUSDT"
    assert response["market_type"] == "Kripto"
    assert response["timeframe"] == "1h"
    assert response["source"] == "binance"
    assert response["count"] == 3
    assert {"time", "open", "high", "low", "close", "volume"} <= set(response["candles"][0].keys())
