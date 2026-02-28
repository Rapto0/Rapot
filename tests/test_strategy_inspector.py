from datetime import datetime

import numpy as np
import pandas as pd

from strategy_inspector import (
    build_strategy_inspector_chunks,
    inspect_strategy_dataframe,
    normalize_inspector_timeframe,
)


def build_long_ohlcv(periods: int = 480) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.date_range(end=datetime.now(), periods=periods, freq="D")
    drift = np.linspace(0, 0.35, periods)
    noise = rng.normal(0, 0.015, periods).cumsum()
    close = 100 * np.exp(noise) * (1 + drift)

    df = pd.DataFrame(
        {
            "Open": close * (1 + rng.normal(0, 0.003, periods)),
            "High": close * (1 + np.abs(rng.normal(0, 0.008, periods))),
            "Low": close * (1 - np.abs(rng.normal(0, 0.008, periods))),
            "Close": close,
            "Volume": rng.integers(100000, 1000000, periods),
        },
        index=dates,
    )
    return df


def test_inspect_strategy_dataframe_combo_structure():
    report = inspect_strategy_dataframe(
        df_daily=build_long_ohlcv(),
        symbol="THYAO",
        market_type="BIST",
        strategy="COMBO",
    )

    assert report["symbol"] == "THYAO"
    assert report["market_type"] == "BIST"
    assert report["strategy"] == "COMBO"
    assert report["indicator_order"] == ["MACD", "RSI", "WR", "CCI"]
    assert len(report["timeframes"]) == 5
    assert [timeframe["code"] for timeframe in report["timeframes"]] == [
        "1D",
        "W-FRI",
        "2W-FRI",
        "3W-FRI",
        "ME",
    ]

    for timeframe in report["timeframes"]:
        assert set(timeframe["indicators"].keys()) == {"MACD", "RSI", "WR", "CCI"}


def test_inspect_strategy_dataframe_hunter_structure():
    report = inspect_strategy_dataframe(
        df_daily=build_long_ohlcv(),
        symbol="BTCUSDT",
        market_type="Kripto",
        strategy="HUNTER",
    )

    assert report["symbol"] == "BTCUSDT"
    assert report["market_type"] == "Kripto"
    assert report["strategy"] == "HUNTER"
    assert len(report["indicator_order"]) == 15
    assert len(report["timeframes"]) == 5

    for timeframe in report["timeframes"]:
        assert len(timeframe["indicators"]) == 15
        assert timeframe["primary_score_label"] == "Dip Skoru"
        assert timeframe["secondary_score_label"] == "Tepe Skoru"


def test_build_strategy_inspector_chunks_contains_symbol_and_strategy():
    report = inspect_strategy_dataframe(
        df_daily=build_long_ohlcv(),
        symbol="THYAO",
        market_type="BIST",
        strategy="HUNTER",
    )

    chunks = build_strategy_inspector_chunks(report)

    assert chunks
    assert "THYAO" in chunks[0]
    assert "HUNTER" in chunks[0]
    assert "<pre>" not in chunks[0]
    assert "Mod: OZET" in chunks[0]
    assert "Momentum" not in chunks[0]
    assert "RSI14" not in chunks[0]
    assert "Fiyat" in chunks[0]


def test_build_strategy_inspector_chunks_detail_single_timeframe():
    report = inspect_strategy_dataframe(
        df_daily=build_long_ohlcv(),
        symbol="THYAO",
        market_type="BIST",
        strategy="HUNTER",
    )

    chunks = build_strategy_inspector_chunks(report, detail=True, timeframe_code="1D")

    assert len(chunks) == 1
    assert "Mod: DETAY" in chunks[0]
    assert "Momentum" in chunks[0]
    assert "Trend" in chunks[0]
    assert "1 HAFTALIK" not in chunks[0]
    assert "RSIF" in chunks[0]


def test_normalize_inspector_timeframe_aliases():
    assert normalize_inspector_timeframe("1D") == "1D"
    assert normalize_inspector_timeframe("1w") == "W-FRI"
    assert normalize_inspector_timeframe("2hf") == "2W-FRI"
    assert normalize_inspector_timeframe("1ay") == "ME"
