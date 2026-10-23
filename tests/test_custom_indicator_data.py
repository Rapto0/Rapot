"""Native custom data scheduling and continuity; no provider/network/account IO."""

import json
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from application.services.advanced_alarm_conditions import condition_fields
from application.services.advanced_alarm_market_data import AdvancedMarketData
from application.services.borsapy_gateway import BorsapyGateway, BorsapyGatewayError
from application.services.custom_indicator_data import (
    CustomIndicatorData,
    HistorySummary,
    _bist_daily_end,
    native_bars,
    with_native_ends,
)
from infrastructure.providers.custom_indicator_history import (
    history_provider,
    validate_native_request,
)
from tests.test_advanced_alarm_gateway import Module, authenticate
from tests.test_advanced_alarm_market_data import MemoryCache
from tests.test_advanced_alarm_market_data import Provider as OrdinaryProvider

NOW = datetime(2026, 10, 13, 14, tzinfo=UTC).timestamp()
SESSION = {"timezone": "Europe/Istanbul", "session": "1000-1805:23456"}


def frame(timeframe="1D", count=60, market="BIST"):
    values = 100 + np.arange(count) * 0.2 + np.sin(np.arange(count))
    index = pd.date_range(end="2026-10-13 07:00", periods=count, freq="B", tz="UTC")
    if market == "Kripto":
        index = pd.date_range(end="2026-10-13", periods=count, freq="D", tz="UTC")
    result = pd.DataFrame(
        {
            "Open": values,
            "High": values + 2,
            "Low": values - 2,
            "Close": values + 0.5,
            "Volume": 100.0,
        },
        index=index,
    )
    result.attrs.update(native_timeframe=timeframe, session_metadata=SESSION.copy())
    return result


class Provider:
    def __init__(self):
        self.generation = 1
        self.calls = []
        self.data = frame()

    def data_epoch(self):
        return self.generation

    def memory_epoch(self):
        return self.generation

    def custom_indicator_history(self, symbol, **kwargs):
        self.calls.append((symbol, kwargs))
        result = self.data.copy()
        result.attrs["native_timeframe"] = kwargs["timeframe"]
        return result


def inputs():
    return {
        **{f"en{i}": i == 1 for i in range(1, 11)},
        "requiredBuyVotes": 1,
        "requiredSellVotes": 1,
    }


def rule(number=1, *, output="buy_signal", market="BIST"):
    return {
        "id": str(number),
        "revision": 1,
        "enabled": True,
        "scope": "symbols",
        "trigger": "bar_close",
        "timeframe": "1d",
        "condition": {
            "op": "eq",
            "left": {
                "field": "custom",
                "indicator": "rsi_votes",
                "inputs": inputs(),
                "output": output,
            },
            "right": 1,
        },
        "symbols": [{"symbol": "THYAO" if market == "BIST" else "BTCUSDT", "market_type": market}],
    }


def test_preview_and_snapshot_only_register_demand_and_worker_shares_outputs():
    provider = Provider()
    service = CustomIndicatorData(provider=provider, clock=lambda: NOW)
    service.configure([rule(), rule(2, output="sell_signal")])
    assert service.status()["requested_rule_symbols"] == 1
    preview = service.preview("rsi_votes", inputs(), "THYAO")
    assert preview["state"] == "waiting"
    assert provider.calls == []
    service.process(*service._next_job())
    assert len(provider.calls) == 1
    assert service.status()["results"] == 1
    preview = service.preview("rsi_votes", inputs(), "THYAO")
    assert preview["state"] == "ready", preview["reason"]
    assert preview["source"] == "borsapy_tradingview:BIST"
    refs = condition_fields(rule()["condition"], "1d")
    observation = service.observation(refs[0], rule()["symbols"][0], "bar_close", NOW)
    assert observation["ready"]
    assert observation["bar_time"] < preview["latest"]["time"]
    assert len(provider.calls) == 1


def test_capacity_reports_distinct_blocked_configs_and_preview_cannot_activate_them(monkeypatch):
    from application.services import custom_indicator_data as data_service

    monkeypatch.setattr(data_service, "MAX_CONFIGS", 1)
    service = CustomIndicatorData(provider=Provider(), clock=lambda: NOW)
    first, blocked, duplicate, paused = rule(), rule(2), rule(3), rule(4)
    blocked["condition"]["left"]["inputs"]["len1"] = 15
    duplicate["condition"]["left"]["inputs"].update(len1=15, showTable=False)
    duplicate["condition"]["left"]["output"] = "sell_signal"
    paused["condition"]["left"]["inputs"]["len1"] = 16
    paused["enabled"] = False
    service.configure([first, blocked, duplicate, paused])
    assert service.status()["configured"] == 1
    assert service.status()["blocked_configurations"] == 1
    refs = condition_fields(blocked["condition"], "1d")
    result = service.observation(refs[0], blocked["symbols"][0], "bar_close", NOW)
    assert not result["ready"] and "etkin ayar sınırı" in result["reason"]

    service.preview("rsi_votes", refs[0]["inputs"], "THYAO")
    service.process(*service._next_job())
    service.process(*service._next_job())
    assert service.preview("rsi_votes", refs[0]["inputs"], "THYAO")["state"] == "ready"
    assert not service.observation(refs[0], blocked["symbols"][0], "bar_close", NOW)["ready"]
    service.configure([blocked, duplicate])
    assert service.status()["blocked_configurations"] == 0
    assert service.status()["configured"] == 1
    assert service.observation(refs[0], blocked["symbols"][0], "bar_close", NOW)["ready"]


def test_session_metadata_controls_daily_close_corrections_and_unknowns():
    stamp = datetime(2026, 10, 13, 7, tzinfo=UTC).timestamp()
    assert _bist_daily_end(stamp, SESSION) == datetime(2026, 10, 13, 15, 5, tzinfo=UTC).timestamp()
    correction = {**SESSION, "corrections": "1000-1300:20261013"}
    assert _bist_daily_end(stamp, correction) == datetime(2026, 10, 13, 10, tzinfo=UTC).timestamp()
    for extra in (
        {"timezone": "UTC"},
        {"session": "24x7"},
        {"corrections": "unrecognized"},
        {"session_holidays": "20261013"},
    ):
        assert _bist_daily_end(stamp, {**SESSION, **extra}) is None
    assert _bist_daily_end(stamp, {}) is None


def test_multiday_ends_come_from_native_daily_witness_never_calendar_addition():
    daily = native_bars(frame(), "1D", "BIST", NOW)
    selected = (daily[-5], daily[-2])
    result = with_native_ends(selected, daily, "3D", "BIST", NOW)
    assert result[0].end == daily[-3].end
    assert result[-1].end is None
    assert not result[-1].confirmed


def test_staleness_and_account_change_fail_closed_without_fetching():
    clock = [NOW]
    provider = Provider()
    service = CustomIndicatorData(provider=provider, clock=lambda: clock[0])
    service.configure([rule()])
    service.process(*service._next_job())
    clock[0] += 181
    assert service.preview("rsi_votes", inputs(), "THYAO")["state"] == "stale"
    provider.generation += 1
    assert service.preview("rsi_votes", inputs(), "THYAO")["state"] == "unknown"
    assert len(provider.calls) == 1


def test_historical_revision_resets_result_continuity():
    clock = [NOW]
    provider = Provider()
    service = CustomIndicatorData(provider=provider, clock=lambda: clock[0])
    service.configure([rule()])
    service.process(*service._next_job())
    before = service.preview("rsi_votes", inputs(), "THYAO")["continuity_id"]
    clock[0] += 31
    provider.data.iloc[5, provider.data.columns.get_loc("Close")] += 0.1
    service.native_refresh(("BIST", "THYAO", "1D"))
    service.process(*service._next_job())
    # A confirmed history revision invalidates every compact seed first;
    # the next bounded worker job installs the corrected native baseline.
    service.process(*service._next_job())
    after = service.preview("rsi_votes", inputs(), "THYAO")["continuity_id"]
    assert after != before


def test_native_crypto_gaps_are_not_filled_or_accepted():
    data = frame(market="Kripto")
    assert len(native_bars(data, "1D", "Kripto", NOW)) == 60
    with pytest.raises(ValueError, match="boşluk"):
        native_bars(data.drop(data.index[-3]), "1D", "Kripto", NOW)


def test_unknown_multiday_primary_end_is_not_mislabeled_calendar_stale():
    provider = Provider()
    service = CustomIndicatorData(provider=provider, clock=lambda: NOW)
    special = {**inputs(), "tf1": "3D"}
    service.preview("rsi_votes", special, "THYAO", chart_timeframe="3D")
    service.process(*service._next_job())
    result = service.preview("rsi_votes", special, "THYAO", chart_timeframe="3D")
    assert result["state"] == "unknown"
    assert "kapanış sınırı doğrulanamadı" in result["reason"]
    custom_ref = {
        "field": "custom",
        "indicator": "rsi_votes",
        "inputs": service._config("rsi_votes", special, "3D")[1]["inputs"],
        "output": "buy_signal",
        "timeframe": "3D",
    }
    closed = service.observation(
        custom_ref, {"symbol": "THYAO", "market_type": "BIST"}, "bar_close", NOW
    )
    assert closed["ready"]
    assert closed["bar_end"] is not None
    assert closed["bar_time"] < result["latest"]["time"]


def test_preview_only_result_cannot_hide_an_unfetched_alarm_member():
    provider = Provider()
    service = CustomIndicatorData(provider=provider, clock=lambda: NOW)
    service.preview("rsi_votes", inputs(), "GARAN")
    service.process(*service._next_job())
    service.configure([rule()])
    assert service.status()["results"] == 1
    assert service.status()["pending_or_stale_rule_symbols"] == 1


def test_late_configure_or_shutdown_does_not_repopulate_results():
    provider = Provider()
    service = CustomIndicatorData(provider=provider, clock=lambda: NOW)
    service.configure([rule()])
    job = service._next_job()
    service.configure([])
    service.process(*job)
    assert provider.calls == []
    assert service.status()["results"] == 0
    service.configure([rule()])
    job = service._next_job()
    service.stop()
    service.process(*job)
    assert provider.calls == []


def test_gateway_custom_native_path_preserves_metadata_and_rejects_account_change(
    tmp_path, monkeypatch
):
    settings = SimpleNamespace(
        borsapy_tradingview_enabled=True,
        borsapy_credentials_path=str(tmp_path / "credentials.enc"),
        jwt_secret_key="synthetic-key-never-a-real-account-key",
        database_path=str(tmp_path / "main.sqlite3"),
        borsapy_max_streams=3,
        borsapy_stream_idle_seconds=120,
    )
    gateway = BorsapyGateway(settings, loader=lambda: Module(), version_reader=lambda: "0.11.0")
    authenticate(gateway)
    captured = []

    class NativeProvider:
        change_account = False

        def status(self):
            return {"requests_completed": len(captured)}

        def get_histories(self, symbol, **kwargs):
            captured.append((symbol, kwargs))
            result = {tf: frame(tf) for tf in kwargs["requests"]}
            if self.change_account:
                gateway.clear()
            return result

        def close(self):
            pass

    provider = NativeProvider()
    monkeypatch.setattr(
        "infrastructure.providers.native_indicator_history.NativeIndicatorHistory",
        lambda *_args: provider,
    )
    try:
        assert gateway.custom_indicator_history_status() == {}
        result = gateway.custom_indicator_history(
            "BTCUSDT", exchange="BINANCE", timeframe="3D", bars=515
        )
        assert captured == [
            (
                "BTCUSDT",
                {
                    "exchange": "BINANCE",
                    "requests": {"3D": 515},
                    "token": gateway._token,
                    "epoch": gateway._data_epoch,
                },
            )
        ]
        assert result.attrs["native_timeframe"] == "3D"
        assert result.attrs["session_metadata"] == SESSION
        assert result.attrs["source"] == "borsapy_tradingview:BINANCE"
        assert gateway.custom_indicator_history_status() == {"requests_completed": 1}
        provider.change_account = True
        with pytest.raises(BorsapyGatewayError) as error:
            gateway.custom_indicator_history("THYAO", exchange="BIST", timeframe="2D", bars=515)
        assert error.value.status_code == 409
    finally:
        gateway.close()


def test_continuity_summary_survives_raw_eviction_and_detects_old_revision():
    bars = native_bars(frame(), "1D", "BIST", NOW)
    summary = HistorySummary.build(bars, NOW)
    assert summary.continues(bars, NOW + 30)
    changed = list(bars)
    changed[5] = replace(changed[5], close=changed[5].close + 0.1)
    assert not summary.continues(changed, NOW + 30)
    assert not summary.continues(bars, NOW + 181)
    for removed in range(1, 4):
        assert summary.continues(bars[removed:], NOW + 30)
        revised = list(bars[removed:])
        revised[0] = replace(revised[0], low=revised[0].low - 0.1)
        assert not summary.continues(revised, NOW + 30)
    assert not summary.continues(bars[4:], NOW + 30)


def test_preview_visual_setting_and_alarm_output_share_calculation_identity():
    provider = Provider()
    service = CustomIndicatorData(provider=provider, clock=lambda: NOW)
    service.configure([rule(), rule(2, output="sell_signal")])
    service.preview("rsi_votes", {**inputs(), "showTable": False}, "THYAO")
    service.process(*service._next_job())
    response = service.preview("rsi_votes", {**inputs(), "showTable": True}, "THYAO")
    assert response["state"] == "ready"
    assert len(provider.calls) == 1
    assert service.status()["results"] == 1
    assert service.status()["preview_leases"] == 1
    stored = next(iter(service._results.values()))
    assert len(stored["points"]) <= 4
    assert all(point["rows"] == [] for point in stored["points"])
    assert response["latest"]["rows"]


def test_many_rule_symbols_retain_compact_results_above_old_128_limit():
    provider = Provider()
    service = CustomIndicatorData(provider=provider, clock=lambda: NOW)
    selected = rule()
    selected["symbols"] = [{"symbol": f"S{i}", "market_type": "BIST"} for i in range(160)]
    service.configure([selected])
    for _ in range(160):
        service.process(*service._next_job())
    assert service.status()["results"] == 160
    assert service.status()["native_series"] <= 64
    assert service.status()["history_continuity_summaries"] == 160
    for result in service._results.values():
        assert len(result["points"]) <= 4
        assert "previous" not in (result.get("previous") or {})


def test_custom_only_hub_does_not_enqueue_ordinary_history(tmp_path):
    settings = SimpleNamespace(
        database_path=str(tmp_path / "db.sqlite"),
        advanced_alarm_cache_path=None,
        advanced_alarm_market_enabled=True,
        advanced_alarm_all_bist_enabled=False,
        advanced_alarm_max_symbols=2000,
        advanced_alarm_quote_stale_seconds=120,
    )
    hub = AdvancedMarketData(settings, cache=MemoryCache(), clock=lambda: NOW)
    hub._custom = CustomIndicatorData(provider=Provider(), clock=lambda: NOW)
    hub.configure([rule()])
    assert not hub._requests
    hub.custom.process(*hub.custom._next_job())
    observation = hub.snapshot(rule(), rule()["symbols"][0])
    assert observation["ready"]
    assert observation["observation_id"] and observation["continuity_id"]


def test_custom_and_ordinary_close_requires_the_same_primary_bar(tmp_path, monkeypatch):
    settings = SimpleNamespace(
        database_path=str(tmp_path / "db.sqlite"),
        advanced_alarm_cache_path=None,
        advanced_alarm_market_enabled=True,
        advanced_alarm_all_bist_enabled=False,
        advanced_alarm_max_symbols=2000,
        advanced_alarm_quote_stale_seconds=120,
    )
    ordinary = OrdinaryProvider()
    ordinary.frames["1d"] = frame()
    ordinary.frames["1d"].attrs["timeframe"] = "1d"
    hub = AdvancedMarketData(settings, provider=ordinary, cache=MemoryCache(), clock=lambda: NOW)
    hub._custom = CustomIndicatorData(provider=Provider(), clock=lambda: NOW)
    selected = rule()
    selected["condition"] = {
        "op": "and",
        "children": [selected["condition"], {"op": "gt", "left": {"field": "close"}, "right": 0}],
    }
    hub.configure([selected])
    hub.custom.process(*hub.custom._next_job())
    for key in hub._requests:
        hub.fetch_history(key, hub._refs(key), hub._reset_count)
    assert hub.snapshot(selected, selected["symbols"][0])["ready"]
    original = hub.custom.observation

    def shifted(*args, **kwargs):
        result = original(*args, **kwargs)
        return {**result, "bar_time": result["bar_time"] + 86400}

    monkeypatch.setattr(hub.custom, "observation", shifted)
    assert not hub.snapshot(selected, selected["symbols"][0])["ready"]


def test_custom_condition_cannot_combine_different_primary_observations(tmp_path, monkeypatch):
    settings = SimpleNamespace(
        database_path=str(tmp_path / "db.sqlite"),
        advanced_alarm_cache_path=None,
        advanced_alarm_market_enabled=True,
        advanced_alarm_all_bist_enabled=False,
        advanced_alarm_max_symbols=2000,
        advanced_alarm_quote_stale_seconds=120,
    )
    hub = AdvancedMarketData(settings, cache=MemoryCache(), clock=lambda: NOW)
    hub._custom = CustomIndicatorData(provider=Provider(), clock=lambda: NOW)
    selected = rule()
    selected["condition"] = {
        "op": "and",
        "children": [rule()["condition"], rule(2, output="sell_signal")["condition"]],
    }
    hub.configure([selected])
    hub.custom.process(*hub.custom._next_job())
    assert hub.snapshot(selected, selected["symbols"][0])["ready"]
    original = hub.custom.observation

    def shifted(ref, *args, **kwargs):
        result = original(ref, *args, **kwargs)
        return (
            {**result, "previous_bar_time": result["previous_bar_time"] - 86400}
            if ref["output"] == "sell_signal"
            else result
        )

    monkeypatch.setattr(hub.custom, "observation", shifted)
    assert not hub.snapshot(selected, selected["symbols"][0])["ready"]


@pytest.mark.parametrize("timeframe", ["1", "240", "1D", "2D", "7D", "2W", "3W", "1M", "15S"])
def test_native_resolution_mapping_is_local_and_never_defaults_to_daily(timeframe):
    from borsapy._providers.tradingview import TradingViewProvider

    before = TradingViewProvider.TIMEFRAMES.copy()
    validate_native_request("THYAO", "BIST", timeframe, 515)
    provider = history_provider("synthetic-token", timeframe, 515)
    assert {timeframe: timeframe} == provider.TIMEFRAMES
    assert provider._calculate_bars("max", timeframe, None, None) == 515
    assert before == TradingViewProvider.TIMEFRAMES
    with pytest.raises(ValueError):
        provider.get_history("THYAO", interval="invalid")


@pytest.mark.parametrize("volume", ["absent", None, 123.0])
def test_native_history_waits_for_completion_and_preserves_only_session_metadata(volume):
    provider = history_provider("synthetic-token", "2D", 515)

    def wire(packet):
        payload = json.dumps(packet)
        return f"~m~{len(payload)}~m~{payload}"

    resolved = {"m": "symbol_resolved", "p": ["cs", "sym", {**SESSION, "private": "discard"}]}
    provider._parse_packets(wire(resolved))
    assert provider.metadata == SESSION
    values = [1, 2, 3, 1, 2] + ([] if volume == "absent" else [volume])
    packet = {"m": "timescale_update", "p": ["cs", {"$prices": {"s": [{"v": values}]}}]}
    assert provider._parse_packets(wire(packet)) == []
    completed = {"m": "series_completed", "p": ["cs", "$prices"]}
    assert provider._parse_packets(wire(completed)) == [packet, completed]
    assert provider.complete


@pytest.mark.parametrize(
    "indicator", ["htf_rsi_score", "rsi_snapshot", "rsi_votes", "smi_votes", "rmi_votes"]
)
@pytest.mark.parametrize("missing", ["absent", "null"])
def test_all_five_ohlc_only_ports_accept_missing_volume_without_inventing_zero(indicator, missing):
    from application.services.custom_indicators.catalog import SPECS, evaluate, validate_config

    raw = frame()
    if missing == "absent":
        raw = raw.drop(columns="Volume")
    else:
        raw["Volume"] = np.nan
    clean = BorsapyGateway._validated_custom_history(raw)
    assert "Volume" not in clean
    bars = native_bars(clean, "1D", "BIST", NOW)
    changes = {}
    for item in SPECS[indicator]["inputs"]:
        key = item["key"]
        if key.startswith("en"):
            changes[key] = key in {"en1", "en_1d"}
        if key in {"requiredBuyVotes", "requiredSellVotes"}:
            changes[key] = 1
    values = validate_config(indicator, changes, "1D")
    result = evaluate(indicator, values, bars, {"1D": bars}, chart_timeframe="1D", as_of=NOW)
    assert result[-1]["ready"], result[-1]["reason"]


@pytest.mark.parametrize(
    "timeframe,bars",
    [
        ("2H", 500),
        ("0D", 500),
        ("366D", 500),
        ("53W", 500),
        ("13M", 500),
        ("2S", 500),
        ("1D", 12001),
        ("1D", True),
    ],
)
def test_native_request_rejects_unsupported_resolution_or_unbounded_history(timeframe, bars):
    with pytest.raises(ValueError):
        validate_native_request("THYAO", "BIST", timeframe, bars)


def test_running_intrabar_history_waits_for_its_own_complete_native_witnesses():
    provider = Provider()
    service = CustomIndicatorData(provider=provider, clock=lambda: NOW)
    selected = rule()
    selected["trigger"] = "intrabar"
    selected["condition"]["left"]["inputs"].update(en2=True)
    service.configure([selected])
    service._running = True
    assert service._next_job() is None
    connection = SimpleNamespace(connected=False, member_ready=lambda _member: True)
    service.live._connection = connection
    service.live._buckets[("BIST", "THYAO", "1D")] = object()
    assert service._next_job() is None
    service.live._buckets[("BIST", "THYAO", "2D")] = object()
    # Another shard being unavailable must not block this witnessed member.
    job = service._next_job()
    assert job[0][:2] == ("BIST", "THYAO")
    assert provider.calls == []
    connection.member_ready = lambda _member: False
    service._queue_seed(job[0])
    assert service._next_job() is None


def test_unavailable_member_does_not_starve_resolved_member_or_fetch_history():
    provider = Provider()
    service = CustomIndicatorData(provider=provider, clock=lambda: NOW)
    selected = rule()
    selected["trigger"] = "intrabar"
    selected["symbols"].insert(0, {"symbol": "AAINVALID", "market_type": "BIST"})
    service.configure([selected])
    service._running = True
    service.live._connection = SimpleNamespace(member_ready=lambda _member: True)
    service.live._buckets[("BIST", "THYAO", "1D")] = object()
    service.live._refused.add(("BIST", "AAINVALID", "1D"))
    job = service._next_job()
    assert job[0][:2] == ("BIST", "THYAO")
    assert provider.calls == []
    ref = condition_fields(selected["condition"], "1d")[0]
    unavailable = service.observation(ref, selected["symbols"][0], "intrabar", NOW)
    assert unavailable["ready"] is False
    assert "reddetti" in unavailable["reason"]
    assert service._jobs_requested == 2


def test_closed_bar_history_does_not_require_a_live_socket():
    provider = Provider()
    service = CustomIndicatorData(provider=provider, clock=lambda: NOW)
    service.configure([rule()])
    service._running = True
    assert service.live._connection is None
    service.process(*service._next_job())
    assert len(provider.calls) == 1
    ref = condition_fields(rule()["condition"], "1d")[0]
    assert service.observation(ref, rule()["symbols"][0], "bar_close", NOW)["ready"]


def test_failed_history_backoff_survives_gap_queue_and_resets_on_success(monkeypatch):
    clock = [NOW]
    provider = Provider()
    service = CustomIndicatorData(provider=provider, clock=lambda: clock[0])
    service.configure([rule()])
    original = provider.custom_indicator_history
    attempts = []

    def fail(*_args, **_kwargs):
        attempts.append(clock[0])
        raise ValueError("Synthetic unavailable symbol")

    monkeypatch.setattr(provider, "custom_indicator_history", fail)
    key = service._next_job()[0]
    for seconds in (30, 60, 120, 240, 480, 960, 1800, 1800):
        service.process(key, service.live._configs[key], service._generation)
        assert service._history_retries[key] == clock[0] + seconds
        service.live_gap("Synthetic connection gap", key[:2])
        assert service._next_job() is None
        assert service.status()["history_retry_waiting"] == 1
        clock[0] += seconds
        assert service._next_job()[0] == key
    assert len(attempts) == 8
    monkeypatch.setattr(provider, "custom_indicator_history", original)
    service.process(key, service.live._configs[key], service._generation)
    assert key not in service._history_retries
    assert key not in service._history_failures
    assert service._results[key]["error"] is None


def test_failed_history_retry_does_not_block_another_member_and_is_bounded_to_demand(monkeypatch):
    provider = Provider()
    service = CustomIndicatorData(provider=provider, clock=lambda: NOW)
    selected = rule()
    selected["symbols"].insert(0, {"symbol": "AAINVALID", "market_type": "BIST"})
    service.configure([selected])
    original = provider.custom_indicator_history

    def history(symbol, **kwargs):
        if symbol == "AAINVALID":
            raise ValueError("Synthetic unavailable symbol")
        return original(symbol, **kwargs)

    monkeypatch.setattr(provider, "custom_indicator_history", history)
    failed = service._next_job()
    assert failed[0][1] == "AAINVALID"
    service.process(*failed)
    service.live_gap("Synthetic connection gap")
    available = service._next_job()
    assert available[0][1] == "THYAO"
    service.process(*available)
    assert service._next_job() is None
    service.configure([selected])
    assert failed[0] in service._history_retries
    service.invalidate()
    assert not service._history_retries and not service._history_failures
    service.process(*service._next_job())
    service.configure([])
    assert not service._history_retries and not service._history_failures


def test_preview_share_survives_805_member_bootstrap_without_duplicate_seed_fetch():
    clock = [NOW]
    provider = Provider()
    service = CustomIndicatorData(provider=provider, clock=lambda: clock[0])
    selected = rule()
    selected["symbols"] = [
        {"market_type": "BIST", "symbol": f"SYM{index:04d}"} for index in range(805)
    ]
    service.configure([selected])
    service.preview("rsi_votes", inputs(), "ZZZFIRST")
    service.preview("rsi_votes", inputs(), "ZZZSECOND")
    observed = []
    for _ in range(8):
        job = service._next_job()
        observed.append(job[0][1])
        service.process(*job)
        clock[0] += 10
    assert observed == [
        "SYM0000",
        "SYM0001",
        "SYM0002",
        "ZZZFIRST",
        "SYM0003",
        "SYM0004",
        "SYM0005",
        "ZZZSECOND",
    ]
    assert len(provider.calls) == len(observed)
    assert service.preview("rsi_votes", inputs(), "ZZZFIRST")["state"] == "ready"
    assert service.preview("rsi_votes", inputs(), "ZZZSECOND")["state"] == "ready"
    assert not any(key[1].startswith("ZZZ") for key in service._seed_queued)
    assert len(service._seed_queue) == 799
