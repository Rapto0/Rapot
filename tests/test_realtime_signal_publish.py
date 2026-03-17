import os

os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

import pandas as pd
import pytest

from async_scanner import process_signals_batch
from market_scanner import process_symbol


def test_sync_process_symbol_publishes_realtime_signal(monkeypatch):
    df = pd.DataFrame({"Close": [1.0] * 30})
    published_payloads = []

    monkeypatch.setattr("market_scanner.TIMEFRAMES", [("1D", "GUNLUK")])
    monkeypatch.setattr(
        "market_scanner.resample_market_data",
        lambda current_df, tf, market_type: current_df,
    )
    monkeypatch.setattr(
        "market_scanner.calculate_combo_signal",
        lambda current_df, tf: {
            "buy": True,
            "sell": False,
            "details": {"Score": "+4/-0", "PRICE": 125.5, "DATE": "2026-03-17"},
        },
    )
    monkeypatch.setattr("market_scanner.calculate_hunter_signal", lambda current_df, tf: None)
    monkeypatch.setattr("market_scanner.db_save_signal", lambda **kwargs: 101)
    monkeypatch.setattr("market_scanner.increment_signal_count", lambda: None)
    monkeypatch.setattr(
        "market_scanner._publish_realtime_signal",
        lambda payload: published_payloads.append(payload) or True,
    )

    process_symbol(df, "THYAO", "BIST")

    assert len(published_payloads) == 1
    signal = published_payloads[0]
    assert signal["id"] == 101
    assert signal["symbol"] == "THYAO"
    assert signal["strategy"] == "COMBO"
    assert signal["signalType"] == "AL"
    assert signal["timeframe"] == "1D"
    assert signal["score"] == "+4/-0"


@pytest.mark.asyncio
async def test_async_process_signals_batch_publishes_realtime_signal(monkeypatch):
    published_payloads = []

    monkeypatch.setattr("async_scanner.db_save_signal", lambda **kwargs: 77)
    monkeypatch.setattr("async_scanner._async_state.increment_signal", lambda: 1)
    monkeypatch.setattr(
        "async_scanner._publish_realtime_signal",
        lambda payload: published_payloads.append(payload) or True,
    )

    results = [
        {
            "symbol": "BTCUSDT",
            "market_type": "Kripto",
            "signals": [
                {
                    "strategy": "HUNTER",
                    "type": "SAT",
                    "timeframe": "1D",
                    "score": "8/10",
                    "price": 60000.0,
                    "details": {"TopScore": "8/10"},
                }
            ],
        }
    ]

    total = await process_signals_batch(results, notify=False)

    assert total == 1
    assert len(published_payloads) == 1
    signal = published_payloads[0]
    assert signal["id"] == 77
    assert signal["symbol"] == "BTCUSDT"
    assert signal["strategy"] == "HUNTER"
    assert signal["signalType"] == "SAT"
