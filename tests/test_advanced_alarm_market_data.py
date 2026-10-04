"""Offline provider, continuity, finality and bounded-lifecycle regressions."""

import asyncio
import threading
from datetime import UTC, datetime
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from application.services.advanced_alarm_data_cache import MarketCache
from application.services.advanced_alarm_market_data import AdvancedMarketData
from application.services.advanced_alarm_series import (
    SeriesError,
    bar_end,
    calculate_series,
    validate_frame,
)
from application.services.borsapy_gateway import BorsapyGatewayError

NOW = datetime(2026, 10, 5, 8, 0, tzinfo=UTC).timestamp()


def frame(timeframe="1m", count=60, last=None):
    interval = {"1m": "min", "5m": "5min", "1d": "D"}[timeframe]
    index = pd.date_range(
        end=pd.Timestamp(last or NOW, unit="s", tz="UTC"), periods=count, freq=interval
    )
    values = 100 + np.arange(count) / 10 + np.sin(np.arange(count))
    result = pd.DataFrame(
        {
            "Open": values,
            "High": values + 2,
            "Low": values - 2,
            "Close": values + 0.5,
            "Volume": np.arange(count, dtype=float),
        },
        index=index,
    )
    result.attrs["timeframe"] = timeframe
    return result


class MemoryCache:
    def __init__(self):
        self.data = {}
        self.universe = []
        self.closed = False

    def load_universe(self):
        return self.universe

    def save_universe(self, symbols):
        self.universe = symbols

    def save(self, key, candles, received):
        self.data[key] = (candles, received)

    def load(self, key):
        return self.data.get(key)

    def size(self):
        return 0

    def close(self):
        self.closed = True


class Connection:
    connected = True
    auth_failed = False

    def close(self):
        self.connected = False


class Provider:
    def __init__(self):
        self.generation = 1
        self.callback = None
        self.connections = []
        self.calls = []
        self.frames = {"1m": frame(), "5m": frame("5m"), "1d": frame("1d")}
        self.failure = None
        self.block = None
        self.entered = threading.Event()

    def epoch(self):
        return self.generation

    def universe(self):
        return ["THYAO", "GARAN"]

    def open_quotes(self, symbols, callback):
        self.calls.append(("quotes", tuple(symbols)))
        if self.failure:
            raise self.failure
        self.callback = callback
        connection = Connection()
        self.connections.append(connection)
        return connection

    def reset_auth(self, epoch):
        self.generation += 1

    def history(self, symbol, market, timeframe):
        self.calls.append(("history", symbol, market, timeframe))
        self.entered.set()
        if self.block:
            self.block.wait(5)
        if self.failure:
            raise self.failure
        return self.frames[timeframe].copy()

    def crypto_quotes(self, symbols):
        return {}


def rule(field="price", *, trigger="intrabar", timeframe="1m", op="gt", right=100):
    return {
        "id": 1,
        "revision": 1,
        "enabled": True,
        "scope": "symbols",
        "trigger": trigger,
        "timeframe": timeframe,
        "condition": {"op": op, "left": {"field": field}, "right": right},
        "symbols": [{"symbol": "THYAO", "market_type": "BIST"}],
    }


@pytest.fixture
def hub(tmp_path):
    settings = SimpleNamespace(
        database_path=str(tmp_path / "main.sqlite3"),
        advanced_alarm_cache_path=None,
        advanced_alarm_market_enabled=True,
        advanced_alarm_all_bist_enabled=False,
        advanced_alarm_max_symbols=2000,
        advanced_alarm_history_workers=1,
        advanced_alarm_quote_stale_seconds=120,
    )
    result = AdvancedMarketData(
        settings, provider=Provider(), cache=MemoryCache(), jitter=lambda: 0
    )
    result.time = [NOW]
    result._clock = lambda: result.time[0]
    result.configure([rule()])
    return result


def observe(hub, price, *, advance=1):
    hub.time[0] += advance
    hub.enqueue_quote("THYAO", {"price": price, "source_timestamp": hub.time[0]})
    hub.poll()


def snapshot(hub, selected=None):
    selected = selected or rule()
    return hub.snapshot(selected, {"symbol": "THYAO", "market_type": "BIST"})


def load(hub, selected):
    hub.configure([selected])
    key = ("BIST", "THYAO", selected["timeframe"])
    hub.fetch_history(key, hub._refs(key), hub._reset_count)


def test_price_crossing_actual_ticks_no_provider_io_in_snapshot(hub):
    selected = rule(op="crossed_above")
    observe(hub, 99)
    assert not snapshot(hub, selected)["ready"]
    observe(hub, 101)
    before = list(hub._provider.calls)
    result = snapshot(hub, selected)
    assert result["ready"] and result["matched"] is True
    assert result["value"] == 101 and result["previous_matched"] is False
    assert hub._provider.calls == before
    assert snapshot(hub, selected)["observation_id"] == result["observation_id"]


def test_repeated_packet_never_refreshes_old_quote(hub):
    observe(hub, 101)
    hub.time[0] += 121
    hub.enqueue_quote("THYAO", {"price": 101, "source_timestamp": NOW + 1})
    hub.poll()
    assert snapshot(hub)["continuity_reason"] == "stale"


def test_gap_and_regression_reset_crossing_continuity(hub):
    selected = rule(op="crossed_above")
    observe(hub, 99)
    before = snapshot(hub)["continuity_id"]
    observe(hub, 101, advance=121)
    assert snapshot(hub)["continuity_id"] != before
    assert not snapshot(hub, selected)["ready"]
    hub.enqueue_quote("THYAO", {"price": 100, "source_timestamp": NOW})
    hub.poll()
    assert not snapshot(hub)["ready"]


def test_quote_does_not_fabricate_a_candle_or_indicator(hub):
    observe(hub, 101)
    assert snapshot(hub)["ready"]
    assert not snapshot(hub, rule("rsi"))["ready"]
    assert hub.history("THYAO")["candles"] == []


def test_closed_bar_uses_next_real_provider_bar_not_forming_tail(hub):
    selected = rule("close", trigger="bar_close")
    load(hub, selected)
    result = snapshot(hub, selected)
    assert result["ready"]
    assert result["value"] == pytest.approx(hub._provider.frames["1m"].Close.iloc[-2])
    assert result["bar_time"] == "2026-10-05T07:59:00Z"
    # Wall-clock passage without a new provider bar cannot close a BIST tail.
    hub.time[0] += 70
    assert snapshot(hub, selected)["observation_id"] == result["observation_id"]


def test_same_history_receipt_is_not_a_new_intrabar_observation(hub):
    selected = rule("rsi")
    load(hub, selected)
    first = snapshot(hub, selected)
    hub.time[0] += 10
    load(hub, selected)
    assert snapshot(hub, selected)["observation_id"] == first["observation_id"]


def test_old_provider_timestamp_rejected_despite_recent_fetch(hub):
    hub._provider.frames["1m"] = frame(last=NOW - 600)
    selected = rule("close")
    load(hub, selected)
    assert snapshot(hub, selected)["continuity_reason"] == "stale"


def test_missing_data_in_or_group_stays_unknown(hub):
    selected = rule()
    selected["condition"] = {
        "op": "or",
        "children": [
            selected["condition"],
            {"op": "gt", "left": {"field": "rsi"}, "right": 50},
        ],
    }
    observe(hub, 110)
    assert not snapshot(hub, selected)["ready"]


def test_provider_revision_resets_prices_and_other_timeframes(hub):
    selected = rule("close")
    load(hub, selected)
    observe(hub, 120)
    before = snapshot(hub, selected)["continuity_id"]
    revised = hub._provider.frames["1m"].copy()
    revised.loc[:, ["Open", "High", "Low", "Close"]] /= 2
    hub._provider.frames["1m"] = revised
    load(hub, selected)
    assert snapshot(hub, selected)["continuity_id"] != before
    assert not snapshot(hub)["ready"]


def test_reconnect_backoff_credential_epoch_and_late_callbacks(hub):
    hub.connection_step()
    old = hub._provider.callback
    old("THYAO", {"price": 101, "source_timestamp": NOW})
    hub.poll()
    assert snapshot(hub)["ready"]
    old_continuity = snapshot(hub)["continuity_id"]
    hub._provider.connections[-1].connected = False
    hub.connection_step()
    assert not snapshot(hub)["ready"]
    assert snapshot(hub)["continuity_id"] != old_continuity
    old("THYAO", {"price": 999, "source_timestamp": NOW})
    hub.poll()
    assert not snapshot(hub)["ready"]
    calls = len(hub._provider.calls)
    hub.connection_step()
    assert len(hub._provider.calls) == calls
    hub.time[0] += 2
    hub.connection_step()
    assert len(hub._provider.calls) == calls + 1
    hub._provider.generation += 1
    hub.connection_step()
    assert hub._provider.connections[-2].connected is False


def test_auth_failure_visible_sanitized_and_retry_bounded(hub):
    hub._provider.failure = BorsapyGatewayError("secret upstream text", 409)
    hub.connection_step()
    assert hub.status()["state"] == "auth_required"
    assert "secret" not in str(hub.status())
    assert snapshot(hub)["continuity_reason"] == "auth"
    count = len(hub._provider.calls)
    hub.connection_step()
    assert len(hub._provider.calls) == count


def test_all_bist_continuous_without_rules_and_shared_rule_membership(hub):
    hub.settings.advanced_alarm_all_bist_enabled = True
    hub.configure([])
    hub.connection_step()
    assert hub.status()["subscribed_symbols"] == 2
    assert set(hub._requests) == {("BIST", "GARAN", "1m"), ("BIST", "THYAO", "1m")}
    many = [{**rule("rsi"), "id": i, "scope": "all_bist"} for i in range(3000)]
    hub.configure(many)
    assert hub.symbols(1) is hub.symbols(2999)
    assert len(hub._requests) == 2
    assert len(hub._global_refs["1m"]) == 1


def test_active_and_background_history_have_fair_turns(hub):
    hub.settings.advanced_alarm_all_bist_enabled = True
    hub._set_universe([f"S{i}" for i in range(12)])
    hub.configure(
        [{**rule("rsi"), "symbols": [{"market_type": "BIST", "symbol": f"S{i}"} for i in range(6)]}]
    )
    jobs = [hub._take_work()[0] for _ in range(8)]
    assert all(key in hub._active for key in jobs[:3])
    assert jobs[3] not in hub._active and jobs[7] not in hub._active


def test_history_failure_drops_old_calculation_and_increments_continuity(hub):
    selected = rule("close")
    load(hub, selected)
    before = snapshot(hub, selected)["continuity_id"]
    hub._provider.failure = RuntimeError("private response")
    load(hub, selected)
    result = snapshot(hub, selected)
    assert not result["ready"] and result["continuity_id"] != before
    assert "private" not in str(result)


def test_late_history_result_after_epoch_change_cannot_become_ready(hub):
    selected = rule("close")
    hub.configure([selected])
    hub._provider.block = threading.Event()
    key = ("BIST", "THYAO", "1m")
    task = threading.Thread(target=hub.fetch_history, args=(key, hub._refs(key), hub._reset_count))
    task.start()
    assert hub._provider.entered.wait(1)
    hub._invalidate("warming", "reset")
    hub._provider.block.set()
    task.join(2)
    assert not snapshot(hub, selected)["ready"]
    assert not hub._cache.data


def test_shutdown_joins_provider_worker_and_rejects_late_data(hub):
    async def exercise():
        hub.configure([rule("close")])
        hub._provider.block = threading.Event()
        await hub.start()
        assert await asyncio.to_thread(hub._provider.entered.wait, 2)
        stopping = asyncio.create_task(hub.stop())
        await asyncio.sleep(0.02)
        assert not stopping.done()
        hub._provider.block.set()
        await asyncio.wait_for(stopping, 3)
        assert not hub._threads and hub._cache.closed
        assert not snapshot(hub)["ready"]

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "mutation", ["gap", "duplicate", "reverse", "nan", "infinity", "bad_ohlc", "naive", "wrong_tf"]
)
def test_bad_candles_never_enter_indicator_pipeline(mutation):
    value = frame()
    if mutation == "gap":
        value = value.drop(value.index[-2])
    elif mutation == "duplicate":
        value.index = [*value.index[:-1], value.index[-2]]
    elif mutation == "reverse":
        value = value.iloc[::-1]
    elif mutation in {"nan", "infinity"}:
        value.iloc[-1, 3] = np.nan if mutation == "nan" else np.inf
    elif mutation == "bad_ohlc":
        value.iloc[-1, 1] = 1
    elif mutation == "naive":
        value.index = value.index.tz_localize(None)
    else:
        value.attrs["timeframe"] = "1d"
    with pytest.raises(SeriesError):
        validate_frame(value, "1m", "Kripto" if mutation == "gap" else "BIST", NOW)


@pytest.mark.parametrize("timeframe,seconds", [("1m", 90), ("5m", 420)])
def test_bist_sparse_bars_still_reject_non_integral_interval(timeframe, seconds):
    raw = frame(timeframe, count=3, last=NOW - 600)
    raw.index = raw.index[:-1].append(
        pd.DatetimeIndex([raw.index[-2] + pd.Timedelta(seconds=seconds)])
    )
    with pytest.raises(SeriesError) as raised:
        validate_frame(raw, timeframe, "BIST", NOW)
    assert raised.value.reason == "gap"


def test_native_sparse_bist_sessions_are_cached_without_fabricated_bars(hub, tmp_path):
    # Native provider shape: continuous session, no-trade/auction interval,
    # then a new session. The retained 500 bars still span both auction gaps.
    index = pd.date_range("2026-10-01 17:30", periods=30, freq="min", tz="Europe/Istanbul")
    index = index.append(
        pd.DatetimeIndex(["2026-10-01 18:08", "2026-10-01 18:09"], tz="Europe/Istanbul")
    )
    index = index.append(
        pd.date_range("2026-10-02 10:00", periods=480, freq="min", tz="Europe/Istanbul")
    )
    index = index.append(
        pd.DatetimeIndex(["2026-10-02 18:08", "2026-10-02 18:09"], tz="Europe/Istanbul")
    )
    raw = frame(count=len(index))
    raw.index = index
    hub._provider.frames["1m"] = raw
    hub.time[0] = pd.Timestamp("2026-10-04T12:00:00Z").timestamp()
    valid = validate_frame(raw, "1m", "BIST", hub.time[0])
    assert len(valid) == 500
    assert valid.index.equals(raw.tail(500).index.tz_convert("UTC"))
    np.testing.assert_array_equal(valid.to_numpy(), raw.tail(500).to_numpy())
    assert len(valid.attrs["native_gap_starts"]) == 2
    calculated = calculate_series(valid, "1m", "BIST", [{"field": "close"}], hub.time[0])
    assert calculated.points[-2].confirmed and not calculated.points[-1].confirmed
    assert len(calculated.gaps) == 1  # Compact long-lived series retain only the latest gap.
    cache = MarketCache(tmp_path / "native-sparse.sqlite3", reserve=0)
    hub._cache = cache
    try:
        selected = rule("close", trigger="bar_close")
        load(hub, selected)
        rows, _ = cache.load("BIST:THYAO:1m")
        assert [row["time"] for row in rows] == [int(stamp.timestamp()) for stamp in valid.index]
        assert [row["close"] for row in rows] == valid.Close.tolist()
        status = hub.status()
        assert status["history_cached"] == 1 and status["history_ready"] == 0
        assert status["cache_bytes"] > 0
        assert status["history_failures_by_reason"] == {"provider": 0, "gap": 0, "invalid_data": 0}
        assert snapshot(hub, selected)["continuity_reason"] == "stale"
    finally:
        cache.close()


def test_new_native_gap_resets_once_and_never_crosses_unobserved_interval(hub):
    selected = rule("close", trigger="bar_close")
    crossed = rule("close", trigger="bar_close", op="crossed_above")
    raw = frame(last=NOW - 60)
    raw.loc[:, ["Open", "High", "Low", "Close"]] = [99, 102, 98, 99]
    hub._provider.frames["1m"] = raw
    load(hub, selected)
    baseline = snapshot(hub, selected)
    assert baseline["ready"] and baseline["matched"] is False
    # 08:00 is absent in native history. Seeing 08:01 does not bridge that gap.
    for offset in (60, 120, 180):
        stamp = pd.Timestamp(NOW + offset, unit="s", tz="UTC")
        raw.loc[stamp] = [101, 102, 98, 101, 1]
        hub.time[0] = NOW + offset + 1
        hub._provider.frames["1m"] = raw.copy()
        load(hub, selected)
        current = snapshot(hub, selected)
        if offset == 60:
            assert current["continuity_reason"] == "gap"
            after_gap = current["continuity_id"]
            assert after_gap != baseline["continuity_id"]
        else:
            assert current["continuity_id"] == after_gap
            assert current["ready"] and current["matched"] is True
            crossing = snapshot(hub, crossed)
            if offset == 120:
                assert not crossing["ready"]  # Previous closed bar belongs to the old segment.
            else:
                assert crossing["ready"] and crossing["matched"] is False
    load(hub, selected)
    assert snapshot(hub, selected)["continuity_id"] == after_gap


@pytest.mark.parametrize("reason", ["provider", "gap", "invalid_data"])
def test_history_failure_status_is_bounded_and_distinguishes_invalid_data(hub, reason):
    if reason == "provider":
        hub._provider.failure = RuntimeError("private provider error")
    elif reason == "gap":
        raw = frame()
        raw.index = raw.index[:-1].append(
            pd.DatetimeIndex([raw.index[-1] - pd.Timedelta(seconds=30)])
        )
        hub._provider.frames["1m"] = raw
    else:
        hub._provider.frames["1m"].iloc[-1, 3] = np.nan
    load(hub, rule("close"))
    status = hub.status()
    assert status["history_cached"] == 0
    assert status["history_failures_by_reason"][reason] == 1
    assert sum(status["history_failures_by_reason"].values()) == 1
    assert "private provider error" not in str(status)


def test_timezone_equivalence_crypto_finality_and_calendar_month():
    raw = frame()
    raw.index = raw.index.tz_convert("Europe/Istanbul")
    normalized = validate_frame(raw, "1m", "BIST", NOW)
    assert normalized.index[-1].timestamp() == NOW
    refs = [{"field": "close", "timeframe": "1m"}]
    bist = calculate_series(normalized, "1m", "BIST", refs, NOW + 61)
    crypto = calculate_series(normalized, "1m", "Kripto", refs, NOW + 61)
    assert not bist.points[-1].confirmed and crypto.points[-1].confirmed
    assert (
        bar_end(pd.Timestamp("2026-02-01", tz="UTC"), "1mo", "Kripto")
        == pd.Timestamp("2026-03-01", tz="UTC").timestamp()
    )


@pytest.mark.parametrize("market", ["BIST", "Kripto"])
def test_near_future_next_bar_cannot_confirm_previous_before_actual_end(market):
    now = pd.Timestamp("2026-10-05T10:00:56Z").timestamp()
    raw = frame(count=3, last=pd.Timestamp("2026-10-05T10:01:00Z").timestamp())
    valid = validate_frame(raw, "1m", market, now)
    refs = [{"field": "close", "timeframe": "1m"}]
    before = calculate_series(valid, "1m", market, refs, now)
    assert before.points[-2].time == pd.Timestamp("2026-10-05T10:00:00Z").timestamp()
    assert not before.points[-2].confirmed
    assert not before.points[-1].confirmed
    at_boundary = calculate_series(valid, "1m", market, refs, now + 4)
    assert at_boundary.points[-2].confirmed
    assert not at_boundary.points[-1].confirmed


def test_zero_volume_preserved_and_short_atr_unknown():
    value = frame(count=5)
    value.Volume = 0.0
    valid = validate_frame(value, "1m", "BIST", NOW)
    refs = [
        {"field": "volume", "timeframe": "1m"},
        {"field": "atr", "period": 14, "timeframe": "1m"},
    ]
    result = calculate_series(valid, "1m", "BIST", refs, NOW)
    assert result.points[-1].values["volume:1m::"] == 0
    assert result.points[-1].values["atr:1m:14:"] is None


def test_sqlite_cache_survives_restart_retention_and_disk_reserve(tmp_path, monkeypatch):
    path = tmp_path / "market.sqlite3"
    cache = MarketCache(path, reserve=0)
    rows = [{"time": i, "close": 1} for i in range(700)]
    cache.save("BIST:THYAO:1m", rows, NOW)
    cache.save_universe(["THYAO"])
    cache.close()
    reopened = MarketCache(path, reserve=0)
    assert len(reopened.load("BIST:THYAO:1m")[0]) == 500
    assert reopened.load_universe() == ["THYAO"]
    assert reopened._open().execute("PRAGMA max_page_count").fetchone()[0] <= 32768
    monkeypatch.setattr("shutil.disk_usage", lambda _: SimpleNamespace(free=0))
    reopened.reserve = 1
    with pytest.raises(OSError, match="rezerv"):
        reopened.save("BIST:THYAO:1m", rows, NOW)
    reopened.close()


def test_unchanged_config_and_history_http_poll_preserve_retry_backoff(hub):
    selected = rule("close")
    hub.configure([selected])
    key = ("BIST", "THYAO", "1m")
    hub._provider.failure = RuntimeError("unavailable")
    hub.fetch_history(key, hub._refs(key), hub._reset_count)
    due = hub._requests[key].due
    hub.time[0] += 5
    hub.configure([dict(selected)])
    hub.history("THYAO")
    assert hub._requests[key].due == due > hub.time[0]
    changed = {**selected, "revision": 2, "condition": rule("rsi")["condition"]}
    hub.configure([changed])
    assert hub._requests[key].due <= hub.time[0]


def test_history_observation_gap_resets_even_when_evaluator_missed_stale_period(hub):
    selected = rule("close", op="crossed_above", right=110)
    load(hub, selected)
    before = snapshot(hub, selected)["continuity_id"]
    hub.time[0] += 240
    hub._provider.frames["1m"] = frame(last=hub.time[0])
    load(hub, selected)
    result = snapshot(hub, selected)
    assert result["continuity_id"] != before
    assert not result["ready"]  # No crossing from the pre-gap observation.


def test_native_monthly_identity_for_quote_once_per_bar(hub):
    selected = {**rule(timeframe="1mo"), "mode": "once_per_bar"}
    hub.configure([selected])
    observe(hub, 101)
    assert not snapshot(hub, selected)["ready"]
    raw = frame("1d", count=4)
    raw.index = pd.date_range("2026-07-01", periods=4, freq="MS", tz="Europe/Istanbul")
    raw.attrs["timeframe"] = "1mo"
    hub._provider.frames["1mo"] = raw
    load(hub, selected)
    first = snapshot(hub, selected)
    assert first["ready"] and first["bar_time"] == "2026-09-30T21:00:00Z"
    assert snapshot(hub)["bar_time"] is None  # Quote-only on-enter does not invent a candle.


def test_multi_timeframe_closed_values_do_not_use_forming_higher_bar(hub):
    selected = rule("close", trigger="bar_close")
    selected["condition"]["right"] = {"field": "close", "timeframe": "5m"}
    hub.configure([selected])
    for tf in ("1m", "5m"):
        key = ("BIST", "THYAO", tf)
        hub.fetch_history(key, hub._refs(key), hub._reset_count)
    result = snapshot(hub, selected)
    assert result["ready"]
    assert result["values"]["close:1m::"] == hub._provider.frames["1m"].Close.iloc[-2]
    assert result["values"]["close:5m::"] == hub._provider.frames["5m"].Close.iloc[-2]


def test_local_account_epoch_blocks_cached_values_without_provider_io(hub):
    hub.connection_step()
    hub._provider.memory_epoch = lambda: hub._provider.generation
    observe(hub, 101)
    assert snapshot(hub)["ready"]
    calls = len(hub._provider.calls)
    hub._provider.generation += 1
    assert snapshot(hub)["continuity_reason"] == "auth"
    assert len(hub._provider.calls) == calls


def test_crypto_batch_cursor_eventually_visits_more_than_first_100(hub):
    selected = {
        **rule(),
        "symbols": [{"market_type": "Kripto", "symbol": f"COIN{i}USDT"} for i in range(150)],
    }
    hub.configure([selected])
    batches = []
    hub._provider.crypto_quotes = lambda batch: batches.append(batch) or {}
    hub.connection_step()
    hub.time[0] += 5
    hub.connection_step()
    assert len(batches) == 2 and all(len(batch) == 100 for batch in batches)
    assert len(set(batches[0] + batches[1])) == 150


@pytest.mark.parametrize(
    "field", ["rsi", "ema", "sma", "macd", "macd_signal", "atr", "wr", "combo", "hunter"]
)
def test_all_native_indicators_have_finite_values_on_sufficient_data(field):
    raw = frame(count=400)
    ref = {"field": field, "timeframe": "1m"}
    if field in {"rsi", "ema", "sma", "atr", "wr"}:
        ref["period"] = 14
    if field in {"combo", "hunter"}:
        ref["side"] = "buy"
    result = calculate_series(validate_frame(raw, "1m", "Kripto", NOW), "1m", "Kripto", [ref], NOW)
    assert np.isfinite(next(iter(result.points[-1].values.values())))


def test_cancelled_stop_still_waits_for_native_worker(hub):
    async def exercise():
        hub.configure([rule("close")])
        hub._provider.block = threading.Event()
        await hub.start()
        assert await asyncio.to_thread(hub._provider.entered.wait, 2)
        stopping = asyncio.create_task(hub.stop())
        await asyncio.sleep(0.01)
        stopping.cancel()
        await asyncio.sleep(0.01)
        assert not stopping.done()
        hub._provider.block.set()
        with pytest.raises(asyncio.CancelledError):
            await stopping
        assert not hub._threads and hub._cache.closed

    asyncio.run(exercise())


def test_indicator_cache_value_budget_evicts_old_series(hub, monkeypatch):
    monkeypatch.setattr("application.services.advanced_alarm_market_data.MAX_VALUE_CELLS", 5)
    selected = rule("close")
    load(hub, selected)
    other = ("BIST", "GARAN", "1m")
    hub.fetch_history(other, [{"field": "close", "timeframe": "1m"}], hub._reset_count)
    assert len(hub._series) == 1 and other in hub._series


def test_real_hub_engine_repository_transition_restart_and_reconnect_dedup(hub):
    from application.services.advanced_alarm_service import AdvancedAlarmEngine
    from infrastructure.repositories import advanced_alarm_repository as repository

    selected = {
        **rule(),
        "name": "Offline integration",
        "category": "price",
        "watchlist_id": None,
        "mode": "on_enter",
        "cooldown_seconds": 60,
        "notify_telegram": False,
    }
    repository.save_rule("admin", selected)
    engine = AdvancedAlarmEngine(
        hub, clock=lambda: hub.time[0], wall_clock=lambda: datetime.fromtimestamp(hub.time[0], UTC)
    )
    engine.tick()
    hub.connection_step()

    def callback_tick(price):
        hub.time[0] += 1
        hub._provider.callback("THYAO", {"price": price, "source_timestamp": hub.time[0]})
        hub.poll()
        engine.tick()

    callback_tick(99)
    assert repository.events("admin")["events"] == []
    callback_tick(101)
    assert len(repository.events("admin")["events"]) == 1
    engine.tick()
    restarted = AdvancedAlarmEngine(
        hub, clock=lambda: hub.time[0], wall_clock=lambda: datetime.fromtimestamp(hub.time[0], UTC)
    )
    restarted.tick()
    assert len(repository.events("admin")["events"]) == 1
    hub._provider.connections[-1].connected = False
    hub.connection_step()
    engine.tick()
    hub.time[0] += 3
    hub.connection_step()
    callback_tick(110)
    assert len(repository.events("admin")["events"]) == 1


def test_real_hub_3000_rule_memory_and_snapshot_measurement(hub):
    import time
    import tracemalloc

    rules = [{**rule(), "id": i, "scope": "all_bist", "symbols": []} for i in range(3000)]
    hub._set_universe([f"S{i}" for i in range(2000)])
    tracemalloc.start()
    try:
        hub.configure(rules)
        hub.enqueue_quote("S0", {"price": 101, "source_timestamp": NOW})
        hub.poll()
        begin = time.perf_counter()
        ready = sum(
            hub.snapshot(item, {"symbol": "S0", "market_type": "BIST"})["ready"] for item in rules
        )
        elapsed = time.perf_counter() - begin
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert ready == 3000 and hub.symbols(0) is hub.symbols(2999)
    assert peak < 80 * 1024**2
    print(
        f"Synthetic hub: 3000 price snapshots={elapsed:.3f}s; tracked allocation peak={peak}B; no provider calls"
    )


def test_status_counts_never_observed_and_blocks_dead_connection(hub):
    hub.settings.advanced_alarm_all_bist_enabled = True
    hub.connection_step()
    assert hub.status()["stale_symbols"] == 2
    observe(hub, 101)
    assert hub.status()["fresh_symbols"] == 1 and hub.status()["stale_symbols"] == 1
    hub._provider.connections[-1].connected = False
    assert hub.status()["fresh_symbols"] == 0 and hub.status()["history_ready"] == 0
    hub._storage_error = True
    assert hub.status()["state"] == "storage_error"
    assert "diske kaydedilemiyor" in hub.status()["message"]


@pytest.mark.parametrize("today_gap", [False, True])
def test_daily_primary_can_resolve_previous_session_minute_within_history_window(hub, today_gap):
    selected = rule("close", timeframe="1d", trigger="bar_close")
    selected["condition"]["right"] = {"field": "close", "timeframe": "1m"}
    hub.configure([selected])
    daily = frame("1d", count=4)
    daily.index = pd.date_range("2026-10-02", periods=4, tz="Europe/Istanbul")
    hub._provider.frames["1d"] = daily
    minute = frame(count=360)
    minute.index = pd.date_range(
        "2026-10-04 13:00", periods=300, freq="min", tz="Europe/Istanbul"
    ).append(pd.date_range("2026-10-05 10:01", periods=60, freq="min", tz="Europe/Istanbul"))
    if today_gap:
        minute = minute.drop(minute.index[-5])
    hub._provider.frames["1m"] = minute
    for tf in ("1d", "1m"):
        key = ("BIST", "THYAO", tf)
        hub.fetch_history(key, hub._refs(key), hub._reset_count)
    result = snapshot(hub, selected)
    assert result["ready"]
    assert result["values"]["close:1m::"] == minute.Close.iloc[299]
