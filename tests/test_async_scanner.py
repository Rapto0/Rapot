import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import async_scanner
from async_scanner import process_signals_batch


@pytest.mark.asyncio
async def test_process_signals_batch_does_not_send_regular_telegram(monkeypatch):
    sent_messages = []
    saved_signals = []

    monkeypatch.setattr("async_scanner.send_message", sent_messages.append)
    monkeypatch.setattr(
        "async_scanner.db_save_signal", lambda **kwargs: saved_signals.append(kwargs)
    )
    monkeypatch.setattr("async_scanner._async_state.increment_signal", lambda: 1)

    results = [
        {
            "symbol": "THYAO",
            "market_type": "BIST",
            "signals": [
                {
                    "strategy": "COMBO",
                    "type": "AL",
                    "timeframe": "1D",
                    "tf_label": "GÜNLÜK",
                    "score": "+4/-0",
                    "price": 307.5,
                },
                {
                    "strategy": "HUNTER",
                    "type": "AL",
                    "timeframe": "W-FRI",
                    "tf_label": "1 HAFTALIK",
                    "score": "7/7",
                    "price": 307.5,
                },
            ],
        }
    ]

    total = await process_signals_batch(results, notify=True)

    assert total == 2
    assert len(saved_signals) == 2
    assert sent_messages == []


@pytest.mark.asyncio
async def test_scan_market_async_returns_failed_status_on_fatal_error(monkeypatch):
    sent_messages: list[str] = []

    monkeypatch.setattr("async_scanner.send_message", sent_messages.append)
    monkeypatch.setattr(
        "async_scanner.get_all_bist_symbols", lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    monkeypatch.setattr("async_scanner.fetch_multiple_bist_async", lambda *args, **kwargs: {})
    monkeypatch.setattr("async_scanner.fetch_multiple_crypto_async", lambda *args, **kwargs: {})
    monkeypatch.setattr("async_scanner.get_all_binance_symbols_async", lambda: [])

    async_scanner._async_state._is_scanning = False
    result = await async_scanner.scan_market_async(notify=False, markets=["BIST"])

    assert result["status"] == "failed"
    assert "boom" in result["error"]
    assert async_scanner._async_state.is_scanning is False
    assert any("basarisiz" in msg.lower() for msg in sent_messages)
