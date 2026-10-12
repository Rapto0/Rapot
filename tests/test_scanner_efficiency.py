"""Offline lifetime and candle parity checks; no provider or notification work."""

import asyncio
import gc
import time
import weakref

import numpy as np
import pandas as pd
import pytest

import async_scanner
import data_loader


def _frame(rows: int = 2100) -> pd.DataFrame:
    close = 100 + np.arange(rows, dtype=float) / 10
    frame = pd.DataFrame(
        {
            "Open": close - 0.2,
            "High": close + 1,
            "Low": close - 1,
            "Close": close,
            "Volume": np.arange(rows, dtype=float) * 11,
        },
        index=pd.date_range("2020-01-01", periods=rows, tz="UTC"),
    )
    frame.attrs["fetched_at_ts"] = time.time()
    return frame


def _legacy_aggregate(frame: pd.DataFrame, keys: pd.Series) -> pd.DataFrame | None:
    """Previous scalar reductions, used only as an offline comparison oracle."""
    work = frame.copy()
    work["_group_key"] = keys.to_numpy()
    rows = []
    for _, block in work.groupby("_group_key", sort=True):
        block = block.drop(columns="_group_key")
        row = {}
        for column in ("Open", "High", "Low", "Close", "Volume"):
            if column not in block:
                continue
            series = block[column]
            value = (
                series.iloc[0]
                if column == "Open"
                else series.iloc[-1]
                if column == "Close"
                else series.max()
                if column == "High"
                else series.min()
                if column == "Low"
                else series.sum()
            )
            row[column] = float(value)
        rows.append((block.index[0], row))
    if not rows:
        return None
    return pd.DataFrame(
        [row for _, row in rows], index=pd.DatetimeIndex([stamp for stamp, _ in rows])
    ).sort_index()


@pytest.mark.parametrize("market", ["BIST", "Kripto"])
@pytest.mark.parametrize("timeframe", ["1D", "W-FRI", "2W-FRI", "3W-FRI", "ME", "2M", "3M"])
def test_batched_resampling_matches_previous_reductions(monkeypatch, market, timeframe):
    frame = _frame()
    # Missing volume, actual zero, signed cancellation and large/small values
    # exercise the existing Series.sum precision and missing-value behavior.
    frame.loc[frame.index[30:60], "Volume"] = np.nan
    frame.loc[frame.index[100:104], "Volume"] = [1e16, 1.0, -1e16, 3.0]
    frame.loc[frame.index[4], "Close"] = np.nan
    frame = pd.concat([frame.iloc[:10], frame.iloc[[9]], frame.iloc[10:]]).iloc[::-1]
    original = frame.copy(deep=True)
    actual = data_loader.resample_market_data(frame, timeframe, market)
    with monkeypatch.context() as patch:
        patch.setattr(data_loader, "_aggregate_grouped_ohlcv", _legacy_aggregate)
        expected = data_loader.resample_market_data(frame, timeframe, market)
    pd.testing.assert_frame_equal(actual, expected, check_exact=True)
    pd.testing.assert_frame_equal(frame, original, check_exact=True)
    assert frame.attrs == original.attrs
    actual.iloc[-1, 0] = -123
    pd.testing.assert_frame_equal(frame, original, check_exact=True)


def test_real_trading_day_labels_and_utc_crypto_boundaries():
    # Both UTC instants fall on February 2 in Istanbul, including the first
    # real trading day after the previous Friday. Inputs must stay untouched.
    frame = pd.DataFrame(
        {
            "Open": [10, 20, 30],
            "High": [14, 24, 35],
            "Low": [9, 18, 28],
            "Close": [12, 22, 33],
            "Volume": [0, 5, 7],
        },
        index=pd.to_datetime(["2026-01-30T21:30Z", "2026-02-01T21:30Z", "2026-02-02T21:30Z"]),
    )
    bist = data_loader.resample_market_data(frame, "W-FRI", "BIST")
    crypto = data_loader.resample_market_data(frame, "W-FRI", "Kripto")
    assert bist.index.tolist() == [
        pd.Timestamp("2026-01-31 00:30"),
        pd.Timestamp("2026-02-02 00:30"),
    ]
    assert crypto.index.tolist() == [
        pd.Timestamp("2026-01-30 21:30"),
        pd.Timestamp("2026-02-02 21:30"),
    ]
    assert bist.to_numpy().tolist() == [[10, 14, 9, 12, 0], [20, 35, 18, 33, 12]]
    assert crypto.to_numpy().tolist() == [[10, 24, 9, 22, 5], [30, 35, 28, 33, 7]]


@pytest.mark.parametrize("market", ["BIST", "Kripto"])
def test_resampling_preserves_absent_volume_and_real_zero(market):
    frame = _frame(30)
    missing = data_loader.resample_market_data(frame.drop(columns="Volume"), "ME", market)
    assert "Volume" not in missing
    frame["Volume"] = 0.0
    known_zero = data_loader.resample_market_data(frame, "ME", market)
    assert known_zero["Volume"].tolist() == [0.0]


@pytest.mark.asyncio
async def test_async_scan_releases_finished_frames_before_next_market_batch(monkeypatch):
    living: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
    batches = []
    all_bytes = 0
    peak_bytes = 0
    observed = []
    monkeypatch.setattr(async_scanner, "_async_state", async_scanner.AsyncScannerState())
    monkeypatch.setattr(async_scanner, "get_all_bist_symbols", lambda: [f"S{i}" for i in range(61)])
    monkeypatch.setattr(
        async_scanner, "get_all_binance_symbols_async", lambda: [f"C{i}USDT" for i in range(101)]
    )
    monkeypatch.setattr(async_scanner, "send_message", lambda *_: pytest.fail("No Telegram"))

    async def fetch(symbols, **_kwargs):
        nonlocal all_bytes, peak_bytes
        await asyncio.sleep(0)
        gc.collect()
        assert not living, "Completed batches must not remain alive during the next fetch"
        data = {}
        for symbol in symbols:
            frame = _frame()
            data[symbol] = frame
            living[symbol] = frame
            all_bytes += int(frame.memory_usage(deep=True).sum())
        peak_bytes = max(
            peak_bytes, sum(int(f.memory_usage(deep=True).sum()) for f in data.values())
        )
        batches.append(len(symbols))
        return data

    async def analyze(symbol, frame, market):
        return {"symbol": symbol, "market_type": market, "df_daily": frame, "signals": []}

    async def persist(results, notify):
        assert notify is False
        observed.extend((result["market_type"], result["symbol"]) for result in results)
        assert all(result["df_daily"] is living[result["symbol"]] for result in results)

    monkeypatch.setattr(async_scanner, "fetch_multiple_bist_async", fetch)
    monkeypatch.setattr(async_scanner, "fetch_multiple_crypto_async", fetch)
    monkeypatch.setattr(async_scanner, "process_symbol_async", analyze)
    monkeypatch.setattr(async_scanner, "process_signals_batch", persist)
    result = await async_scanner.scan_market_async(notify=False)
    await asyncio.sleep(0)
    gc.collect()
    assert not living
    assert batches == [30, 30, 1, 50, 50, 1]
    assert result["bist_count"] == 61 and result["crypto_count"] == 101
    assert result["status"] == "success" and len(set(observed)) == 162
    assert peak_bytes == 50 * 2100 * 6 * 8
    assert all_bytes == 162 * 2100 * 6 * 8
