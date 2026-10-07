"""Missing provider volume must not become a genuine zero-volume observation."""

import pandas as pd
import pytest

from application.services.advanced_alarm_series import calculate_series, validate_frame


def history(quality=None):
    index = pd.date_range("2026-10-07 14:00", periods=25, freq="min", tz="UTC")
    frame = pd.DataFrame(
        {"Open": 100.0, "High": 102.0, "Low": 99.0, "Close": 101.0, "Volume": 0.0},
        index=index,
    )
    frame.attrs["timeframe"] = "1m"
    if quality is not None:
        frame.attrs["volume_verified"] = quality
    return frame


@pytest.mark.parametrize("quality", [None, False, "true", 1])
def test_bist_unknown_volume_keeps_price_indicators_usable(quality):
    frame = history(quality)
    now = frame.index[-1].timestamp() + 30
    valid = validate_frame(frame, "1m", "BIST", now)
    result = calculate_series(
        valid,
        "1m",
        "BIST",
        [{"field": "volume"}, {"field": "close"}, {"field": "rsi", "period": 14}],
        now,
    )
    values = result.points[-1].values
    assert values["volume:1m::"] is None
    assert values["close:1m::"] == 101.0
    assert values["rsi:1m:14:"] is not None


@pytest.mark.parametrize("market,quality", [("BIST", True), ("Kripto", None)])
def test_verified_or_binance_zero_volume_remains_zero(market, quality):
    frame = history(quality)
    now = frame.index[-1].timestamp() + 30
    result = calculate_series(
        validate_frame(frame, "1m", market, now), "1m", market, [{"field": "volume"}], now
    )
    assert result.points[-1].values["volume:1m::"] == 0.0


def test_volume_provenance_change_changes_observation_version():
    frame = history(False)
    now = frame.index[-1].timestamp() + 30
    before = calculate_series(frame, "1m", "BIST", [{"field": "volume"}], now)
    frame.attrs["volume_verified"] = True
    after = calculate_series(frame, "1m", "BIST", [{"field": "volume"}], now)
    assert before.version != after.version
