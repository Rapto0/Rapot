"""Offline parity checks with real signal/tag/AI rows in isolated SQLite."""

import asyncio
import json
import time
from typing import Any

import numpy as np
import pandas as pd
import pytest

import ai_analyst
import async_scanner
import market_scanner
from application.scanner.scan_history import track_scan
from db_session import get_session
from infrastructure.repositories.system_repository import list_scan_history
from models import AIAnalysis, Signal


def price_frame(*, rising: bool = False) -> pd.DataFrame:
    close = np.linspace(1000, 10, 1000)
    if rising:
        close = close[::-1]
    frame = pd.DataFrame(
        {
            "Open": close + 0.05,
            "High": close + 0.1,
            "Low": close - 0.1,
            "Close": close,
            "Volume": np.full(len(close), 10000),
        },
        index=pd.bdate_range(end="2026-01-30", periods=len(close)),
    )
    frame.attrs["fetched_at_ts"] = time.time()
    return frame


@pytest.fixture
def effects(monkeypatch: pytest.MonkeyPatch) -> dict[str, list]:
    calls: dict[str, list] = {"telegram": [], "ai": [], "news": [], "secondary": []}
    for module in (market_scanner, async_scanner):
        monkeypatch.setattr(
            module, "send_message", lambda message: calls["telegram"].append(message) or True
        )
        monkeypatch.setattr(module, "_publish_realtime_signal", lambda *_: True)
    monkeypatch.setattr(market_scanner, "_scanner_state", market_scanner.ScannerState())
    monkeypatch.setattr(async_scanner, "_async_state", async_scanner.AsyncScannerState())
    monkeypatch.setattr(
        market_scanner, "format_ai_message_for_telegram", lambda *_a, **_k: "offline AI"
    )
    monkeypatch.setattr(market_scanner, "_derive_technical_levels", lambda *_: {})

    def secondary(symbol: str, **_kwargs) -> pd.DataFrame:
        calls["secondary"].append(symbol)
        return price_frame()

    def news(symbol: str, market_type: str) -> list:
        calls["news"].append((symbol, market_type))
        return []

    def analyze(**kwargs: Any) -> str:
        calls["ai"].append(kwargs)
        response = '{"summary":["offline analysis"]}'
        saved = ai_analyst.save_analysis_to_db(
            symbol=kwargs["symbol"],
            market_type=kwargs["market_type"],
            scenario_name=kwargs["scenario_name"],
            signal_type=kwargs["signal_type"],
            signal_id=kwargs["signal_id"],
            analysis_text=response,
            technical_data=kwargs["technical_data"],
        )
        assert saved is not None
        return response

    monkeypatch.setattr(market_scanner, "get_bist_data_secondary", secondary)
    monkeypatch.setattr(market_scanner, "fetch_market_news", news)
    monkeypatch.setattr(market_scanner, "analyze_with_gemini", analyze)
    return calls


def snapshot(after_id: int = 0) -> tuple[list[tuple], list[tuple], int]:
    with get_session() as session:
        rows = session.query(Signal).filter(Signal.id > after_id).order_by(Signal.id).all()
        signals = [
            (
                row.strategy,
                row.signal_type,
                row.timeframe,
                row.score,
                row.price,
                row.details,
                row.special_tag,
            )
            for row in rows
        ]
        analyses = (
            session.query(AIAnalysis)
            .filter(AIAnalysis.signal_id > after_id)
            .order_by(AIAnalysis.id)
            .all()
        )
        ai = []
        for analysis in analyses:
            signal = analysis.signal
            assert signal is not None
            assert analysis.market_type == signal.market_type
            assert analysis.symbol == signal.symbol
            assert analysis.signal_type == signal.signal_type
            payload = json.loads(analysis.technical_data)
            assert payload["special_tag"] == signal.special_tag
            # Separate invocations have different wall-clock report creation times.
            assert payload.pop("generated_at")
            ai.append(
                (signal.strategy, signal.signal_type, signal.timeframe, signal.special_tag, payload)
            )
        return signals, ai, max((row.id for row in rows), default=after_id)


async def run_symbol(mode: str, frame: pd.DataFrame, market: str, *, notify: bool = False) -> None:
    symbol = "THYAO" if market == "BIST" else "BTCUSDT"
    with track_scan(markets={market}, mode=mode) as progress:
        progress.symbols_scanned = 1
        if mode == "sync":
            market_scanner.process_symbol(frame, symbol, market, notify=notify)
        else:
            result = await async_scanner.process_symbol_async(symbol, frame, market)
            await async_scanner.process_signals_batch([result], notify=notify)


@pytest.mark.asyncio
@pytest.mark.parametrize("market", ["BIST", "Kripto"])
@pytest.mark.parametrize("rising", [False, True], ids=["buy", "sell"])
async def test_same_ohlcv_yields_same_saved_signals_tags_and_ai_ids(
    effects, monkeypatch, market, rising
):
    frame = price_frame(rising=rising)
    monkeypatch.setattr(market_scanner, "get_bist_data_secondary", lambda *_a, **_k: frame.copy())

    def unexpected_format(*_args, **_kwargs):
        pytest.fail("notify=False must not invoke Telegram formatting")

    monkeypatch.setattr(market_scanner, "format_ai_message_for_telegram", unexpected_format)
    await run_symbol("sync", frame.copy(), market)
    expected_signals, expected_ai, boundary = snapshot()
    assert expected_signals and expected_ai
    expected_tags = {"PAHALI", "FAHIS_FIYAT"} if rising else {"COK_UCUZ", "BELES"}
    assert expected_tags <= {row[-1] for row in expected_signals}
    await run_symbol("async", frame.copy(), market)
    actual_signals, actual_ai, _ = snapshot(boundary)
    assert actual_signals == expected_signals
    assert actual_ai == expected_ai
    assert effects["telegram"] == []
    assert len(effects["ai"]) == len(expected_ai) * 2
    assert len(effects["news"]) == len(effects["ai"])
    history = list_scan_history(10)
    assert len(history) == 2
    assert all(row["signals_found"] == len(expected_signals) for row in history)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["sync", "async"])
@pytest.mark.parametrize("failure", ["missing", "stale", "mismatch"])
async def test_bist_second_source_gate_matches_reference_and_keeps_exact_tags(
    effects, monkeypatch, mode, failure
):
    secondary = None if failure == "missing" else price_frame(rising=failure == "mismatch")
    if failure == "stale":
        secondary.attrs["fetched_at_ts"] = time.time() - 91
    monkeypatch.setattr(market_scanner, "get_bist_data_secondary", lambda *_a, **_k: secondary)
    await run_symbol(mode, price_frame(), "BIST", notify=True)
    signals, analyses, _ = snapshot()
    assert signals and any(row[-1] for row in signals)
    assert analyses == [] and effects["ai"] == [] and effects["telegram"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["sync", "async"])
@pytest.mark.parametrize("failure", ["disabled", "exception"])
async def test_ai_off_or_failure_preserves_tags_and_notify_false_suppresses_every_message(
    effects, monkeypatch, mode, failure
):
    def analyze(**_kwargs):
        if failure == "exception":
            raise RuntimeError("offline AI failure")
        return ai_analyst.analyze_with_gemini(**_kwargs)

    # The offline bootstrap sets AI_ENABLED=0: the real disabled branch does no network I/O.
    monkeypatch.setattr(market_scanner, "analyze_with_gemini", analyze)
    await run_symbol(mode, price_frame(), "Kripto", notify=False)
    signals, analyses, _ = snapshot()
    assert signals and any(row[-1] for row in signals)
    assert analyses == [] and effects["telegram"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["sync", "async"])
@pytest.mark.parametrize("failure", ["ignored_insert", "save_error", "tag_error"])
async def test_failed_current_target_never_tags_or_attaches_ai_to_previous_row(
    effects, monkeypatch, mode, failure
):
    original_save = market_scanner.db_save_signal
    old_id = original_save(
        symbol="BTCUSDT",
        market_type="Kripto",
        strategy="COMBO",
        signal_type="AL",
        timeframe="3W-FRI",
        price=9,
        score="+4/-0",
        special_tag="LEGACY",
    )
    original_tag = market_scanner.db_set_signal_special_tag
    tagged_ids = []

    def save(**kwargs):
        if kwargs["timeframe"] == "3W-FRI" and failure != "tag_error":
            if failure == "save_error":
                raise OSError("offline target insert failure")
            return 0
        return original_save(**kwargs)

    def tag(**kwargs):
        tagged_ids.append(kwargs["signal_id"])
        if (
            failure == "tag_error"
            and kwargs["strategy"] == "COMBO"
            and kwargs["timeframe"] == "3W-FRI"
        ):
            raise OSError("offline target tag failure")
        return original_tag(**kwargs)

    for module in (market_scanner, async_scanner):
        monkeypatch.setattr(module, "db_save_signal", save)
    monkeypatch.setattr(market_scanner, "db_set_signal_special_tag", tag)
    await run_symbol(mode, price_frame(), "Kripto")
    with get_session() as session:
        assert session.get(Signal, old_id).special_tag == "LEGACY"
        assert session.query(AIAnalysis).filter(AIAnalysis.signal_id == old_id).count() == 0
        committed = session.query(Signal).filter(Signal.id > old_id).all()
        new_ids = {signal.id for signal in committed}
        assert new_ids
        assert set(tagged_ids) <= new_ids
        assert {call["signal_id"] for call in effects["ai"]} <= new_ids
        if failure != "tag_error":
            assert not any(signal.timeframe == "3W-FRI" for signal in committed)
    row = list_scan_history(1)[0]
    assert row["signals_found"] == len(new_ids)
    assert row["status"] == ("partial" if failure == "save_error" else "success")
    assert effects["telegram"] == []


@pytest.mark.asyncio
async def test_notify_true_uses_the_same_special_telegram_path(effects):
    await run_symbol("sync", price_frame(), "Kripto", notify=True)
    expected = list(effects["telegram"])
    assert expected
    effects["telegram"].clear()
    await run_symbol("async", price_frame(), "Kripto", notify=True)
    assert effects["telegram"] == expected


@pytest.mark.asyncio
async def test_async_missing_and_stale_bist_data_are_partial_without_writes(effects, monkeypatch):
    stale = price_frame()
    stale.attrs["fetched_at_ts"] = time.time() - 91
    monkeypatch.setattr(
        async_scanner, "get_all_bist_symbols", lambda: ["MISSING", "STALE", "EMPTY"]
    )

    async def fetch(*_args, **_kwargs):
        return {"STALE": stale, "EMPTY": pd.DataFrame()}

    monkeypatch.setattr(async_scanner, "fetch_multiple_bist_async", fetch)
    result = await async_scanner.scan_market_async(notify=False, markets="BIST")
    assert result["status"] == "partial" and result["errors_count"] == 3
    assert snapshot()[0] == [] and effects["ai"] == [] and effects["telegram"] == []


@pytest.mark.asyncio
async def test_async_validates_and_processes_each_bist_batch_before_fetching_next(
    effects, monkeypatch
):
    clock = [1000.0]
    fetches = []
    fresh_checks = []
    monkeypatch.setattr(async_scanner, "get_all_bist_symbols", lambda: [f"S{i}" for i in range(31)])
    monkeypatch.setattr(market_scanner, "finalize_symbol_signals", lambda **_kwargs: None)

    async def fetch(symbols, **_kwargs):
        fetches.append(list(symbols))
        if len(fetches) == 2:
            assert len(fresh_checks) == 60  # receipt and per-symbol write boundary
            with get_session() as session:
                assert session.query(Signal).count() == 30
            clock[0] += 91
        frame = pd.DataFrame({"Close": [10.0] * 30})
        frame.attrs["fetched_at_ts"] = clock[0]
        return dict.fromkeys(symbols, frame)

    def fresh(frame, max_age):
        fresh_checks.append(clock[0] - frame.attrs["fetched_at_ts"])
        return fresh_checks[-1] <= max_age

    async def process(symbol, frame, market):
        return {
            "symbol": symbol,
            "market_type": market,
            "df_daily": frame,
            "signals": [
                {
                    "strategy": "COMBO",
                    "type": "AL",
                    "timeframe": "1D",
                    "score": "+4/-0",
                    "price": 10,
                }
            ],
        }

    monkeypatch.setattr(async_scanner, "fetch_multiple_bist_async", fetch)
    monkeypatch.setattr(async_scanner, "is_dataframe_fresh", fresh)
    monkeypatch.setattr(async_scanner, "process_symbol_async", process)
    result = await async_scanner.scan_market_async(notify=False, markets="BIST")
    assert [len(batch) for batch in fetches] == [30, 1]
    assert result["status"] == "success" and result["total_signals"] == 31
    assert fresh_checks == [0.0] * 62


@pytest.mark.asyncio
async def test_async_rechecks_bist_after_prior_ai_and_processes_the_next_fresh_batch(
    effects, monkeypatch
):
    clock = [1000.0]
    monkeypatch.setattr(async_scanner, "get_all_bist_symbols", lambda: [f"S{i}" for i in range(31)])

    async def fetch(symbols, **_kwargs):
        frame = pd.DataFrame({"Close": [10.0] * 30})
        frame.attrs["fetched_at_ts"] = clock[0]
        return dict.fromkeys(symbols, frame)

    def finalize(**kwargs):
        if kwargs["symbol"] == "S0":
            # Simulate the first symbol's news/AI phase taking longer than freshness.
            clock[0] += 91

    async def process(symbol, frame, market):
        return {
            "symbol": symbol,
            "market_type": market,
            "df_daily": frame,
            "signals": [
                {
                    "strategy": "COMBO",
                    "type": "AL",
                    "timeframe": "1D",
                    "score": "+4/-0",
                    "price": 10,
                }
            ],
        }

    monkeypatch.setattr(async_scanner, "fetch_multiple_bist_async", fetch)
    monkeypatch.setattr(
        async_scanner,
        "is_dataframe_fresh",
        lambda df, age: clock[0] - df.attrs["fetched_at_ts"] <= age,
    )
    monkeypatch.setattr(async_scanner, "process_symbol_async", process)
    monkeypatch.setattr(market_scanner, "finalize_symbol_signals", finalize)
    result = await async_scanner.scan_market_async(notify=False, markets="BIST")
    assert result["status"] == "partial" and result["errors_count"] == 29
    assert result["total_signals"] == 2
    with get_session() as session:
        assert [row.symbol for row in session.query(Signal).order_by(Signal.id)] == ["S0", "S30"]


@pytest.mark.asyncio
async def test_async_cancel_after_commit_prevents_later_ai_or_signal_writes(effects, monkeypatch):
    frame = price_frame()
    monkeypatch.setattr(
        async_scanner, "get_all_binance_symbols_async", lambda: ["BTCUSDT", "ETHUSDT"]
    )

    async def fetch(symbols, **_kwargs):
        return dict.fromkeys(symbols, frame)

    def publish(_payload):
        asyncio.current_task().cancel()
        return True

    monkeypatch.setattr(async_scanner, "fetch_multiple_crypto_async", fetch)
    monkeypatch.setattr(async_scanner, "_publish_realtime_signal", publish)
    with pytest.raises(asyncio.CancelledError):
        await async_scanner.scan_market_async(notify=False, markets="Kripto")
    await asyncio.sleep(0)
    signals, analyses, _ = snapshot()
    assert len(signals) == 1 and analyses == [] and effects["ai"] == []
    history = list_scan_history(1)[0]
    assert history["status"] == "cancelled" and history["signals_found"] == 1
    assert not async_scanner._async_state.is_scanning
