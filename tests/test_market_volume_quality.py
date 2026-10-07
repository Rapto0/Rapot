"""Missing/sentinel volume is not a zero-volume market observation."""

import numpy as np
import pandas as pd
import pytest

from application.services.borsapy_research import run_operation
from application.services.market_volume_quality import frame_volume_quality, native_volume


@pytest.mark.parametrize(
    "value", [None, True, -1, 1e100, 10**1000, float("nan"), float("inf"), "0"]
)
def test_non_native_or_invalid_volume_is_unknown(value):
    assert native_volume(value) is None


@pytest.fixture
def frame():
    close = np.linspace(100, 110, 80) + np.sin(np.arange(80))
    return pd.DataFrame(
        {"Open": close, "High": close + 1, "Low": close - 1, "Close": close, "Volume": 0},
        index=pd.date_range("2026-01-01", periods=80, tz="Europe/Istanbul"),
    )


def test_zero_requires_native_provenance_and_invalid_values_override_stale_metadata(frame):
    assert native_volume(0) == 0
    assert frame_volume_quality(frame)["state"] == "unverified"
    frame.attrs.update(volume_verified=False, volume_unavailable_rows=80)
    assert frame_volume_quality(frame)["state"] == "unavailable"
    frame.attrs.update(volume_verified=True, volume_unavailable_rows=0)
    assert frame_volume_quality(frame)["state"] == "verified"
    frame["Volume"] = 1e100
    assert frame_volume_quality(frame)["verified"] is False


@pytest.mark.parametrize("indicator", ["obv", "vwap"])
@pytest.mark.parametrize("provenance", ["missing", "unavailable"])
def test_volume_indicators_are_unknown_before_calculation(
    frame, monkeypatch, indicator, provenance
):
    import borsapy

    if provenance == "unavailable":
        frame.attrs.update(volume_verified=False, volume_unavailable_rows=80)
    monkeypatch.setattr(borsapy.Ticker, "history", lambda *args, **kwargs: frame)

    def forbidden(*args, **kwargs):
        pytest.fail("Unverified volume must not reach the indicator calculator")

    monkeypatch.setattr(borsapy, f"calculate_{indicator}", forbidden)
    result = run_operation(borsapy, "ta.indicators", {"indicator": indicator})
    assert result["summary"]["indicator"] is None
    assert result["volume_quality"]["state"] == (
        "unavailable" if provenance == "unavailable" else "unverified"
    )
    assert result["volume_quality"]["message"] in result["warnings"]
    assert len(result["candles"]) == len(frame)
    assert all(candle["volume"] is None for candle in result["candles"])
    assert all(row["Volume"] is None for row in result["tables"][0]["rows"])
    assert frame.Volume.eq(0).all()  # Provider cache/input was not mutated.


def test_verified_zero_volume_still_runs_real_obv(frame, monkeypatch):
    import borsapy

    frame.attrs.update(volume_verified=True, volume_unavailable_rows=0)
    monkeypatch.setattr(borsapy.Ticker, "history", lambda *args, **kwargs: frame)
    result = run_operation(borsapy, "ta.indicators", {"indicator": "obv"})
    assert result["volume_quality"]["verified"] is True
    assert all(candle["volume"] == 0 for candle in result["candles"])
    indicator = next(table for table in result["tables"] if table["name"] == "indicator")
    numeric = [
        value for row in indicator["rows"] for value in row.values() if type(value) in (int, float)
    ]
    assert numeric and all(value == 0 for value in numeric)


@pytest.mark.parametrize("operation", ["history", "replay", "heikin_ashi", "ta.indicators"])
def test_price_only_research_keeps_ohlc_and_labels_unknown_volume(frame, monkeypatch, operation):
    import borsapy

    monkeypatch.setattr(borsapy.Ticker, "history", lambda *args, **kwargs: frame)
    result = run_operation(
        borsapy, operation, {"indicator": "rsi"} if operation == "ta.indicators" else {}
    )
    assert len(result["candles"]) == len(frame)
    assert all(
        candle["close"] is not None and candle["volume"] is None for candle in result["candles"]
    )
    assert result["volume_quality"]["verified"] is False
    if operation == "ta.indicators":
        indicator = next(table for table in result["tables"] if table["name"] == "indicator")
        assert any(type(value) is float for row in indicator["rows"] for value in row.values())
