"""Offline scanner lifecycle regressions with real temporary signal/history tables."""

import asyncio

import pytest

import async_scanner
import market_scanner
from application.scanner import scan_history
from db_session import get_session
from infrastructure.repositories.system_repository import list_scan_history
from models import Signal


def saved_signal(symbol: str, market: str) -> int:
    return market_scanner._save_signal_and_publish(
        symbol=symbol,
        market_type=market,
        strategy="COMBO",
        signal_type="AL",
        timeframe="1D",
        score="+4/-0",
        price=100,
        details={"test": "scan history"},
    )


@pytest.fixture
def scanners(monkeypatch, sample_ohlcv_data):
    monkeypatch.setattr(market_scanner, "_scanner_state", market_scanner.ScannerState())
    monkeypatch.setattr(async_scanner, "_async_state", async_scanner.AsyncScannerState())
    for module in (market_scanner, async_scanner):
        monkeypatch.setattr(module, "get_all_bist_symbols", lambda: ["THYAO"])
        monkeypatch.setattr(module, "_publish_realtime_signal", lambda *_: False)
        monkeypatch.setattr(module, "send_message", lambda *_: None)
    monkeypatch.setattr(market_scanner, "get_all_binance_symbols", lambda: ["BTCUSDT"])
    monkeypatch.setattr(async_scanner, "get_all_binance_symbols_async", lambda: ["BTCUSDT"])
    monkeypatch.setattr(market_scanner, "get_bist_data", lambda *_a, **_k: sample_ohlcv_data)
    monkeypatch.setattr(market_scanner, "cached_get_crypto_data", lambda *_: sample_ohlcv_data)
    monkeypatch.setattr(market_scanner, "is_dataframe_fresh", lambda *_: True)
    monkeypatch.setattr(async_scanner, "is_dataframe_fresh", lambda *_: True)
    monkeypatch.setattr(market_scanner.time, "sleep", lambda *_: None)
    monkeypatch.setattr(market_scanner.price_cache, "clear_expired", lambda: None)
    monkeypatch.setattr(
        market_scanner.price_cache, "get_stats", lambda: {"session_hits": 0, "session_misses": 0}
    )
    monkeypatch.setattr(
        market_scanner,
        "process_symbol",
        lambda _df, sym, market, **_kwargs: saved_signal(sym, market),
    )

    async def fetch(symbols, **_kwargs):
        return dict.fromkeys(symbols, sample_ohlcv_data)

    async def process(symbol, _df, market):
        return {
            "symbol": symbol,
            "market_type": market,
            "signals": [
                {
                    "strategy": "COMBO",
                    "type": "AL",
                    "timeframe": "1D",
                    "score": "+4/-0",
                    "price": 100,
                }
            ],
        }

    monkeypatch.setattr(async_scanner, "fetch_multiple_bist_async", fetch)
    monkeypatch.setattr(async_scanner, "fetch_multiple_crypto_async", fetch)
    monkeypatch.setattr(async_scanner, "process_symbol_async", process)


def one_history(status: str, *, symbols: int, signals: int, errors: int):
    rows = list_scan_history(10)
    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == status
    assert row["symbols_scanned"] == symbols
    assert row["signals_found"] == signals
    assert row["errors_count"] == errors
    assert row["duration_seconds"] >= 0
    return row


def test_sync_success_records_one_terminal_row_and_saved_signal(scanners):
    market_scanner.scan_market(markets="BIST")
    row = one_history("success", symbols=1, signals=1, errors=0)
    assert row["scan_type"] == "BIST" and row["mode"] == "sync"
    assert market_scanner.get_scan_count() == market_scanner.get_signal_count() == 1


def test_sync_ignored_insert_does_not_increment_saved_signal_totals(scanners, monkeypatch):
    market_scanner.scan_market(markets="BIST")
    monkeypatch.setattr(market_scanner, "db_save_signal", lambda **_kwargs: 0)
    market_scanner.scan_market(markets="BIST")
    rows = list_scan_history(10)
    assert sorted(row["signals_found"] for row in rows) == [0, 1]
    assert market_scanner.get_signal_count() == 1


@pytest.mark.parametrize("failure", ["missing", "stale", "exception"])
def test_sync_symbol_failure_is_partial_and_keeps_other_insert(scanners, monkeypatch, failure):
    monkeypatch.setattr(market_scanner, "get_all_bist_symbols", lambda: ["THYAO", "ASELS"])
    original = market_scanner.get_bist_data

    def data(symbol, **kwargs):
        if symbol == "ASELS":
            if failure == "exception":
                raise ValueError("provider failed")
            if failure == "missing":
                return None
            frame = original(symbol, **kwargs).copy()
            frame.attrs["stale_test"] = True
            return frame
        return original(symbol, **kwargs)

    monkeypatch.setattr(market_scanner, "get_bist_data", data)
    monkeypatch.setattr(
        market_scanner, "is_dataframe_fresh", lambda df, _: not df.attrs.get("stale_test")
    )
    market_scanner.scan_market(markets="BIST")
    one_history("partial", symbols=2, signals=1, errors=1)


def test_sync_fatal_error_preserves_previous_market_insert(scanners, monkeypatch):
    def fail():
        raise RuntimeError("symbol enumeration failed")

    monkeypatch.setattr(market_scanner, "get_all_binance_symbols", fail)
    with pytest.raises(RuntimeError, match="symbol enumeration failed"):
        market_scanner.scan_market()
    one_history("failed", symbols=1, signals=1, errors=1)


def test_sync_interruption_records_cancelled_and_propagates(scanners):
    def cancel():
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        market_scanner.scan_market(check_commands_callback=cancel, markets="BIST")
    one_history("cancelled", symbols=1, signals=1, errors=0)


def test_manual_analysis_callback_is_not_counted_as_scheduled_signal(scanners):
    market_scanner.scan_market(
        check_commands_callback=lambda: saved_signal("MANUAL", "BIST"), markets="BIST"
    )
    one_history("success", symbols=1, signals=1, errors=0)
    with get_session() as session:
        assert session.query(Signal).count() == 2


@pytest.mark.asyncio
async def test_async_success_records_real_persistence_and_terminal_summary(scanners):
    result = await async_scanner.scan_market_async(notify=False, markets="Kripto")
    row = one_history("success", symbols=1, signals=1, errors=0)
    assert row["mode"] == "async" and row["scan_type"] == "Kripto"
    assert result["history_id"] == row["id"]
    assert result["total_signals"] == 1 and result["status"] == "success"
    assert not async_scanner._async_state.is_scanning


@pytest.mark.asyncio
async def test_async_ignored_insert_counts_only_new_insert(scanners, monkeypatch):
    first = await async_scanner.scan_market_async(notify=False, markets="Kripto")
    monkeypatch.setattr(async_scanner, "db_save_signal", lambda **_kwargs: 0)
    second = await async_scanner.scan_market_async(notify=False, markets="Kripto")
    assert [first["total_signals"], second["total_signals"]] == [1, 0]
    assert async_scanner._async_state.get_stats()["signal_count"] == 1
    assert len(list_scan_history(10)) == 2


@pytest.mark.asyncio
async def test_async_fatal_error_keeps_prior_insert_and_clears_running_state(scanners, monkeypatch):
    def fail():
        raise ValueError("symbol enumeration failed")

    monkeypatch.setattr(async_scanner, "get_all_binance_symbols_async", fail)
    result = await async_scanner.scan_market_async(notify=False)
    one_history("failed", symbols=1, signals=1, errors=1)
    assert result["status"] == "failed" and result["total_signals"] == 1
    assert not async_scanner._async_state.is_scanning


@pytest.mark.asyncio
async def test_async_cancel_during_next_market_keeps_insert_and_propagates(scanners, monkeypatch):
    async def cancelled(*_args, **_kwargs):
        raise asyncio.CancelledError

    monkeypatch.setattr(async_scanner, "fetch_multiple_crypto_async", cancelled)
    with pytest.raises(asyncio.CancelledError):
        await async_scanner.scan_market_async(notify=False)
    one_history("cancelled", symbols=2, signals=1, errors=0)
    assert not async_scanner._async_state.is_scanning


@pytest.mark.asyncio
async def test_async_reentry_does_not_create_a_scan(scanners):
    async_scanner._async_state._is_scanning = True
    result = await async_scanner.scan_market_async(notify=False)
    assert result.get("error")
    assert list_scan_history(10) == []
    assert async_scanner._async_state.get_stats()["scan_count"] == 0


@pytest.mark.asyncio
async def test_async_missing_symbol_is_visible_as_partial(scanners, monkeypatch):
    monkeypatch.setattr(
        async_scanner, "get_all_binance_symbols_async", lambda: ["BTCUSDT", "ETHUSDT"]
    )
    original = async_scanner.fetch_multiple_crypto_async

    async def missing(symbols, **kwargs):
        return await original(symbols[:1], **kwargs)

    monkeypatch.setattr(async_scanner, "fetch_multiple_crypto_async", missing)
    result = await async_scanner.scan_market_async(notify=False, markets="Kripto")
    one_history("partial", symbols=2, signals=1, errors=1)
    assert result["status"] == "partial"


@pytest.mark.asyncio
async def test_async_child_exception_is_partial_and_other_child_is_saved(scanners, monkeypatch):
    monkeypatch.setattr(
        async_scanner, "get_all_binance_symbols_async", lambda: ["BTCUSDT", "ETHUSDT"]
    )
    original = async_scanner.process_symbol_async

    async def one_failed(symbol, *args):
        if symbol == "ETHUSDT":
            raise ValueError("indicator failed")
        return await original(symbol, *args)

    monkeypatch.setattr(async_scanner, "process_symbol_async", one_failed)
    await async_scanner.scan_market_async(notify=False, markets="Kripto")
    one_history("partial", symbols=2, signals=1, errors=1)


def test_monotonic_duration_and_nested_invocation_counts_are_independent(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(scan_history.time, "monotonic", lambda: now[0])
    with scan_history.track_scan(markets={"BIST"}, mode="sync") as outer:
        scan_history.record_signal_saved()
        with scan_history.track_scan(markets={"Kripto"}, mode="async") as inner:
            scan_history.record_signal_saved()
            scan_history.record_signal_saved()
            now[0] = 102.0
        now[0] = 105.0
    assert (inner.duration_seconds, outer.duration_seconds) == (2.0, 5.0)
    assert (inner.signals_found, outer.signals_found) == (2, 1)
    scan_history.record_signal_saved()
    assert outer.signals_found == 1


def test_history_write_failure_does_not_mask_original_exception(monkeypatch):
    def failed_write(**_kwargs):
        raise OSError("history storage unavailable")

    monkeypatch.setattr(scan_history, "save_scan_history", failed_write)
    with (
        pytest.raises(ValueError, match="original failure"),
        scan_history.track_scan(markets={"BIST"}, mode="sync") as progress,
    ):
        raise ValueError("original failure")
    assert progress.status == "failed" and progress.history_id is None


def test_notification_failure_does_not_change_committed_scan(scanners, monkeypatch):
    def notify_failed(*_args):
        raise OSError("notification unavailable")

    monkeypatch.setattr(market_scanner, "send_message", notify_failed)
    market_scanner.scan_market(markets="BIST")
    one_history("success", symbols=1, signals=1, errors=0)


def test_sync_cancel_after_insert_before_publish_preserves_committed_count(scanners, monkeypatch):
    def cancelled(*_args):
        raise KeyboardInterrupt

    monkeypatch.setattr(market_scanner, "_publish_realtime_signal", cancelled)
    with pytest.raises(KeyboardInterrupt):
        market_scanner.scan_market(markets="BIST")
    one_history("cancelled", symbols=1, signals=1, errors=0)
    with get_session() as session:
        assert session.query(Signal).count() == 1


@pytest.mark.asyncio
async def test_async_cancel_after_insert_before_publish_preserves_committed_count(
    scanners, monkeypatch
):
    def cancelled(*_args):
        raise asyncio.CancelledError

    monkeypatch.setattr(async_scanner, "_publish_realtime_signal", cancelled)
    with pytest.raises(asyncio.CancelledError):
        await async_scanner.scan_market_async(notify=False, markets="Kripto")
    one_history("cancelled", symbols=1, signals=1, errors=0)
    assert not async_scanner._async_state.is_scanning
