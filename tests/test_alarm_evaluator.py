"""Offline alarm-provider and closed-candle contracts; no account/network calls."""

import asyncio
import threading
from datetime import UTC, datetime
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from application.services import server_alarm_evaluator as alarms
from signals import calculate_combo_signal, calculate_hunter_signal

NOW = datetime(2026, 10, 2, 12, 30, tzinfo=UTC)


def candles(index: pd.DatetimeIndex, timeframe: str = "1h") -> pd.DataFrame:
    axis = np.arange(len(index))
    close = 100 + axis / 10 + np.sin(axis / 3) * 5
    frame = pd.DataFrame(
        {
            "Open": close + 0.2,
            "High": close + 2,
            "Low": close - 2,
            "Close": close,
            "Volume": 1000.0 + axis,
        },
        index=index,
    )
    frame.attrs["timeframe"] = timeframe
    return frame


def crypto_candles(timeframe: str = "1h", now: datetime = NOW) -> pd.DataFrame:
    step = {"1h": "1h", "4h": "4h", "1d": "1D"}[timeframe]
    return candles(
        pd.date_range(end=pd.Timestamp(now).floor(step), periods=161, freq=step), timeframe
    )


def bist_hours(now: str) -> pd.DataFrame:
    instant = pd.Timestamp(now, tz="Europe/Istanbul")
    days = pd.bdate_range(end=instant.normalize(), periods=30)
    index = pd.DatetimeIndex(
        [day + pd.Timedelta(hours=hour) for day in days for hour in range(10, 18)]
    )
    return candles(index[index <= instant][-161:])


def evaluate(frame: pd.DataFrame, **overrides) -> dict:
    arguments = {
        "market_type": "Kripto",
        "timeframe": "1h",
        "indicator": "rsi",
        "side": "dip",
        "threshold": 30,
        "now": NOW,
    }
    arguments.update(overrides)
    return alarms.evaluate_closed_alarm_bars(frame, **arguments)


class FakeProvider:
    def __init__(self, frame: pd.DataFrame | None) -> None:
        self.frame = frame
        self.calls = []

    def fetch_bars(self, **kwargs):
        self.calls.append(kwargs)
        return self.frame


@pytest.mark.parametrize("timeframe", ["1h", "4h", "1d"])
def test_only_closed_bar_used_at_exact_boundary(timeframe):
    frame = crypto_candles(timeframe)
    frame.iloc[-1] = np.inf  # Provider's forming candle is deliberately unusable.
    instant = frame.index[-1].to_pydatetime()
    result = evaluate(frame, timeframe=timeframe, now=instant)
    assert result["bar_time"] == frame.index[-2].isoformat().replace("+00:00", "Z")
    assert result["bar_closed_at"] == instant.isoformat().replace("+00:00", "Z")
    assert np.isfinite(result["value"])


def test_new_closed_bar_enters_condition_without_looking_ahead():
    frame = crypto_candles()
    closed = frame.iloc[:-1]
    previous = float(alarms.rsi(closed.Close.iloc[:-1], window=14).iloc[-1])
    current = float(alarms.rsi(closed.Close, window=14).iloc[-1])
    threshold = (previous + current) / 2
    side = "top" if current > previous else "dip"
    result = evaluate(frame, side=side, threshold=threshold)
    assert result["matched"] is True
    assert result["previous_matched"] is False


def test_zero_is_a_valid_williams_value():
    frame = crypto_candles()
    frame.loc[:, "Close"] = np.arange(len(frame)) + 100.0
    frame.loc[:, "Open"] = frame.Close
    frame.loc[:, "High"] = frame.Close
    frame.loc[:, "Low"] = frame.Close - 2
    result = evaluate(frame, indicator="wr", side="top", threshold=0)
    assert result["value"] == 0
    assert result["matched"] is True


@pytest.mark.parametrize(
    "indicator,side,key",
    [
        ("combo", "dip", "BuyScore"),
        ("combo", "top", "SellScore"),
        ("hunter", "dip", "DipScore"),
        ("hunter", "top", "TopScore"),
    ],
)
def test_backend_scores_used_directly_for_custom_threshold(indicator, side, key):
    frame = crypto_candles()
    calculator = calculate_combo_signal if indicator == "combo" else calculate_hunter_signal
    native = calculator(frame.iloc[:-1], "1h")
    expected = float(native["details"][key].split("/")[0])
    result = evaluate(frame, indicator=indicator, side=side, threshold=2)
    assert result["value"] == expected
    assert result["matched"] is (expected >= 2)
    assert "Python backend" in result["detail"]


@pytest.mark.parametrize(
    "mutation,match",
    [
        ("duplicate", "tekrarlı"),
        ("order", "sırasız"),
        ("gap", "eksik periyot"),
        ("naive", "saat dilimi"),
        ("wrong_interval", "periyodu"),
        ("nan", "sonlu olmayan"),
        ("infinity", "sonlu olmayan"),
        ("ohlc", "tutarsız"),
        ("negative", "aralığı"),
        ("old", "eski"),
        ("future", "geleceğe"),
        ("short", "120"),
    ],
)
def test_invalid_or_stale_data_never_evaluates(mutation, match):
    frame = crypto_candles()
    if mutation == "duplicate":
        frame.index = pd.DatetimeIndex([frame.index[0], *frame.index[:-1]])
    elif mutation == "order":
        frame = frame.iloc[::-1]
    elif mutation == "gap":
        frame = frame.drop(frame.index[-4])
    elif mutation == "naive":
        frame.index = frame.index.tz_localize(None)
    elif mutation == "wrong_interval":
        frame.attrs["timeframe"] = "1d"
    elif mutation in {"nan", "infinity"}:
        frame.loc[frame.index[-2], "Close"] = np.nan if mutation == "nan" else np.inf
    elif mutation == "ohlc":
        frame.loc[frame.index[-2], "High"] = 1
    elif mutation == "negative":
        frame.loc[frame.index[-2], "Volume"] = -1
    elif mutation == "old":
        frame = frame.iloc[:-2]
    elif mutation == "future":
        frame.index += pd.Timedelta(hours=1)
    elif mutation == "short":
        frame = frame.iloc[-120:]
    with pytest.raises(alarms.AlarmEvaluationError, match=match):
        evaluate(frame)


@pytest.mark.parametrize("corruption", ["partial", "infinite"])
def test_partial_or_infinite_backend_components_are_rejected(monkeypatch, corruption):
    native = calculate_combo_signal(crypto_candles().iloc[:-1], "1h")
    if corruption == "partial":
        native["details"]["ActiveIndicators"] = "3/4"
    else:
        native["details"]["RSI"] = float("inf")
    monkeypatch.setattr(alarms, "calculate_combo_signal", lambda *_: native)
    with pytest.raises(alarms.AlarmEvaluationError, match="bileşenleri"):
        evaluate(crypto_candles(), indicator="combo", threshold=2)


def test_flat_williams_data_is_unknown_not_zero():
    frame = crypto_candles()
    frame.loc[:, ["Open", "High", "Low", "Close"]] = 100
    with pytest.raises(alarms.AlarmEvaluationError, match="hesaplanamadı"):
        evaluate(frame, indicator="wr", threshold=-80)


@pytest.mark.parametrize(
    "instant,expected",
    [
        ("2026-10-02 12:30", "2026-10-02T08:00:00Z"),
        ("2026-10-03 14:00", "2026-10-02T14:00:00Z"),
        ("2026-10-05 10:30", "2026-10-02T14:00:00Z"),
    ],
)
def test_bist_timezone_and_weekend_keep_latest_closed_session(instant, expected):
    frame = bist_hours(instant)
    result = evaluate(
        frame, market_type="BIST", now=pd.Timestamp(instant, tz="Europe/Istanbul").to_pydatetime()
    )
    assert result["bar_time"] == expected


@pytest.mark.parametrize("missing_hour", [10, 13, 17])
def test_bist_missing_session_candle_rejected(missing_hour):
    frame = bist_hours("2026-10-03 14:00")
    frame = frame.drop(pd.Timestamp(f"2026-10-01 {missing_hour}:00", tz="Europe/Istanbul"))
    with pytest.raises(alarms.AlarmEvaluationError, match="eksik"):
        evaluate(frame, market_type="BIST", now=datetime(2026, 10, 3, 11, tzinfo=UTC))


def test_bist_missing_latest_weekday_has_explicit_calendar_uncertainty():
    frame = bist_hours("2026-10-02 17:30")
    with pytest.raises(alarms.AlarmEvaluationError, match="Tatil/yarım gün"):
        evaluate(frame, market_type="BIST", now=datetime(2026, 10, 5, 9, tzinfo=UTC))


def test_bist_daily_waits_for_local_midnight():
    index = pd.bdate_range(end="2026-10-02", periods=161, tz="Europe/Istanbul")
    frame = candles(index, "1d")
    evening = evaluate(
        frame, market_type="BIST", timeframe="1d", now=datetime(2026, 10, 2, 18, tzinfo=UTC)
    )
    midnight = evaluate(
        frame, market_type="BIST", timeframe="1d", now=datetime(2026, 10, 2, 21, tzinfo=UTC)
    )
    assert evening["bar_time"] == "2026-09-30T21:00:00Z"
    assert midnight["bar_time"] == "2026-10-01T21:00:00Z"
    assert midnight["bar_closed_at"] == "2026-10-02T21:00:00Z"


@pytest.mark.asyncio
async def test_provider_cache_reused_but_closed_bar_freshness_rechecked():
    provider = FakeProvider(crypto_candles())
    evaluator = alarms.ServerAlarmEvaluator(provider)
    arguments = {
        "symbol": "BTCUSDT",
        "market_type": "Kripto",
        "timeframe": "1h",
        "indicator": "rsi",
        "side": "dip",
        "threshold": 30,
        "now": NOW,
    }
    try:
        await evaluator.evaluate(**arguments)
        await evaluator.evaluate(**arguments)
        with pytest.raises(alarms.AlarmEvaluationError, match="eski"):
            await evaluator.evaluate(**{**arguments, "now": datetime(2026, 10, 2, 14, tzinfo=UTC)})
        assert len(provider.calls) == 1
    finally:
        evaluator.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "override",
    [
        {"timeframe": "1wk"},
        {"market_type": "BIST", "symbol": "THYAO", "timeframe": "1h"},
        {"market_type": "BIST", "symbol": "THYAO", "timeframe": "4h"},
        {"symbol": "../BTC"},
        {"threshold": float("nan")},
        {"indicator": "pine"},
        {"indicator": "hunter", "threshold": 4.5},
        {"now": datetime(2026, 10, 2)},
    ],
)
async def test_invalid_request_never_calls_provider(override):
    provider = FakeProvider(crypto_candles())
    evaluator = alarms.ServerAlarmEvaluator(provider)
    arguments = {
        "symbol": "BTCUSDT",
        "market_type": "Kripto",
        "timeframe": "1h",
        "indicator": "rsi",
        "side": "dip",
        "threshold": 30,
        "now": NOW,
    }
    try:
        with pytest.raises(alarms.AlarmEvaluationError):
            await evaluator.evaluate(**{**arguments, **override})
        assert not provider.calls
    finally:
        evaluator.close()


@pytest.mark.asyncio
async def test_provider_failure_is_sanitized_and_no_fallback():
    provider = FakeProvider(None)
    evaluator = alarms.ServerAlarmEvaluator(provider)
    arguments = {
        "symbol": "BTCUSDT",
        "market_type": "Kripto",
        "timeframe": "1h",
        "indicator": "rsi",
        "side": "dip",
        "threshold": 30,
        "now": NOW,
    }
    try:
        with pytest.raises(alarms.AlarmEvaluationError, match="döndürmedi"):
            await evaluator.evaluate(**arguments)
        provider.fetch_bars = MagicMock(side_effect=RuntimeError("private-key in provider error"))
        with pytest.raises(alarms.AlarmEvaluationError) as caught:
            await evaluator.evaluate(**arguments)
        assert "private-key" not in str(caught.value)
        assert provider.fetch_bars.call_count == 1
    finally:
        evaluator.close()


@pytest.mark.asyncio
async def test_timed_out_calls_cannot_accumulate_unbounded_threads():
    release = threading.Event()
    calls = []

    class SlowProvider:
        def fetch_bars(self, **kwargs):
            calls.append(kwargs)
            release.wait(timeout=2)
            return crypto_candles()

    evaluator = alarms.ServerAlarmEvaluator(SlowProvider(), timeout_seconds=0.02)
    arguments = {
        "market_type": "Kripto",
        "timeframe": "1h",
        "indicator": "rsi",
        "side": "dip",
        "threshold": 30,
        "now": NOW,
    }
    try:
        for symbol in ["BTCUSDT", "ETHUSDT", "BTCUSDT"]:
            with pytest.raises(alarms.AlarmEvaluationError, match="zaman aşımına"):
                await evaluator.evaluate(symbol=symbol, **arguments)
        with pytest.raises(alarms.AlarmEvaluationError, match="meşgul"):
            await evaluator.evaluate(symbol="SOLUSDT", **arguments)
        assert len(calls) == 2
    finally:
        release.set()
        await asyncio.sleep(0.03)
        evaluator.close()


def test_native_binance_provider_requests_exact_interval_and_timeout(monkeypatch):
    import binance.client

    frame = crypto_candles("4h")
    rows = [
        [
            int(ts.timestamp() * 1000),
            *row,
            int((ts + pd.Timedelta(hours=4)).timestamp() * 1000) - 1,
            0,
            0,
            0,
            0,
            0,
        ]
        for ts, row in frame.iterrows()
    ]
    client = MagicMock()
    client.get_klines.return_value = rows
    constructor = MagicMock(return_value=client)
    monkeypatch.setattr(binance.client, "Client", constructor)
    result = alarms.PublicAlarmDataProvider().fetch_bars(
        symbol="BTCUSDT", market_type="Kripto", timeframe="4h"
    )
    constructor.assert_called_once_with(ping=False, requests_params={"timeout": (3.05, 10)})
    client.get_klines.assert_called_once_with(symbol="BTCUSDT", interval="4h", limit=301)
    client.close_connection.assert_called_once()
    assert result.attrs["timeframe"] == "4h"
    assert str(result.index.tz) == "UTC"
    client.get_klines.return_value[0][6] -= 1
    with pytest.raises(alarms.AlarmEvaluationError, match="periyodu"):
        alarms.PublicAlarmDataProvider().fetch_bars(
            symbol="BTCUSDT", market_type="Kripto", timeframe="4h"
        )


def test_native_bist_provider_has_no_daily_fallback(monkeypatch):
    import yfinance

    ticker = MagicMock()
    ticker.history.return_value = pd.DataFrame()
    factory = MagicMock(return_value=ticker)
    monkeypatch.setattr(yfinance, "Ticker", factory)
    with pytest.raises(alarms.AlarmEvaluationError, match="döndürmedi"):
        alarms.PublicAlarmDataProvider().fetch_bars(
            symbol="THYAO", market_type="BIST", timeframe="1h"
        )
    factory.assert_called_once_with("THYAO.IS")
    ticker.history.assert_called_once_with(
        period="60d", interval="1h", auto_adjust=False, actions=False, timeout=10, raise_errors=True
    )
