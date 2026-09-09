"""ATR warmup must remain unavailable without interrupting HUNTER reports."""

import numpy as np
import pandas as pd
import pytest

from signals import calculate_hunter_signal
from strategy_inspector import inspect_strategy_dataframe


def build_ohlcv(periods: int) -> pd.DataFrame:
    close = 100 + np.arange(periods, dtype=float) * 0.25
    return pd.DataFrame(
        {
            "Open": close - 0.1,
            "High": close + 1,
            "Low": close - 1,
            "Close": close,
            "Volume": np.full(periods, 1000),
        },
        index=pd.date_range("2024-01-15", periods=periods, freq="D"),
    )


@pytest.mark.parametrize("periods", [0, 19, 20, 80])
def test_atr_only_becomes_available_after_twenty_bars(periods: int) -> None:
    frame = build_ohlcv(periods)

    atr = frame.ta.atr(length=20)

    pd.testing.assert_index_equal(atr.index, frame.index)
    assert atr.iloc[:19].isna().all()
    if periods >= 20:
        # High-low and every true range are exactly 2, including the ATR seed.
        assert atr.iloc[19:].tolist() == [2.0] * (periods - 19)
    else:
        assert atr.isna().all()


def test_atr_preserves_measured_zero_after_warmup() -> None:
    frame = build_ohlcv(20)
    frame[["Open", "High", "Low", "Close"]] = 100.0

    atr = frame.ta.atr(length=20)

    assert atr.iloc[:19].isna().all()
    assert atr.iloc[19] == 0.0


@pytest.mark.parametrize("periods, active_count", [(0, 0), (19, 9), (20, 13), (80, 15)])
def test_hunter_excludes_unavailable_indicators_from_scores(
    periods: int, active_count: int
) -> None:
    result = calculate_hunter_signal(build_ohlcv(periods), "ME")

    if periods == 0:
        assert result is None
        return

    assert result is not None
    details = result["details"]
    assert details["ActiveIndicators"] == f"{active_count}/15"
    dip_score, dip_limit = map(int, details["DipScore"].split("/"))
    top_score, top_limit = map(int, details["TopScore"].split("/"))
    assert (dip_limit, top_limit) == (5, 10)
    assert result["buy"] == (dip_score >= dip_limit)
    assert result["sell"] == (top_score >= top_limit)
    assert dip_score <= active_count
    assert top_score <= active_count
    if periods < 20:
        assert details["KeltPB"] == "N/A"
        assert details["CCI"] == "N/A"
        assert details["BBP"] == "N/A"
        assert details["ZScore"] == "N/A"
        assert result["sell"] is False
    else:
        assert np.isfinite(details["KeltPB"])


def test_monthly_short_history_keeps_hunter_report_contract() -> None:
    frame = build_ohlcv(480)
    assert len(frame.resample("ME").last()) == 17

    report = inspect_strategy_dataframe(frame, "BTCUSDT", "Kripto", "HUNTER")

    monthly = next(item for item in report["timeframes"] if item["code"] == "ME")
    assert monthly["available"] is True
    assert monthly["indicators"]["KeltPB"] == "N/A"
    assert monthly["active_indicators"] == "9/15"
    assert monthly["primary_score_label"] == "Dip Skoru"
    assert monthly["secondary_score_label"] == "Tepe Skoru"
    assert len(monthly["indicators"]) == 15
    assert len(report["timeframes"]) == 5
