"""Standard RSI uses an existing native stream without changing rule definitions."""

from types import SimpleNamespace

import pytest

from application.services import advanced_alarm_service as service
from application.services.advanced_alarm_market_data import AdvancedMarketData
from infrastructure.repositories import advanced_alarm_repository as repository
from tests.test_advanced_alarm_backend import payload
from tests.test_advanced_alarm_live_events import LiveHub
from tests.test_advanced_alarm_market_data import NOW, MemoryCache, Provider, rule, snapshot


@pytest.fixture
def hub(tmp_path):
    settings = SimpleNamespace(
        database_path=str(tmp_path / "main.sqlite3"),
        advanced_alarm_cache_path=None,
        advanced_alarm_market_enabled=True,
        advanced_alarm_all_bist_enabled=False,
        advanced_alarm_max_symbols=2000,
        advanced_alarm_quote_stale_seconds=120,
    )
    return AdvancedMarketData(settings, provider=Provider(), cache=MemoryCache(), clock=lambda: NOW)


class SharedRSI:
    def __init__(self):
        self.supported = {("BIST", "THYAO", "1D"), ("BIST", "THYAO", "1W")}
        self.demands = {}
        self.reads = []
        self.ready = True
        self.live = SimpleNamespace(set_listener=lambda callback: None)

    def configure(self, rules, *, universe):
        pass

    def set_universe(self, universe):
        pass

    def supports_standard_rsi(self, member, timeframe):
        return (*member, timeframe) in self.supported

    def configure_standard_rsi(self, demands):
        self.demands = demands

    def standard_rsi_observation(self, ref, symbol, trigger, now):
        self.reads.append((ref, symbol, trigger))
        return {
            "ready": self.ready,
            "reason": "Native RSI hazırlanıyor.",
            "current": 9.0,
            "previous": 11.0,
            "continuity_id": "native-epoch-1",
            "observation_id": "native-quote-2",
            "observed_at": NOW,
            "source_timestamp": NOW,
            "bar_time": NOW - 3600,
            "bar_end": NOW + 3600,
            "live_price": 100.0,
        }


def setup_shared(hub, timeframe="1d"):
    shared = SharedRSI()
    hub._custom = shared
    selected = rule("rsi", timeframe=timeframe, op="lte", right=10)
    selected["mode"] = "once_per_bar"
    hub.configure([selected])
    return shared, selected


@pytest.mark.parametrize("timeframe,native", [("1d", "1D"), ("1wk", "1W")])
def test_shared_rsi_has_no_duplicate_history_job_and_uses_same_tick(hub, timeframe, native):
    shared, selected = setup_shared(hub, timeframe)
    assert shared.demands == {("BIST", "THYAO", native): {14}}
    assert hub._requests == {}
    assert hub.uses_live_updates(selected)
    before = list(hub._provider.calls)
    observed = snapshot(hub, selected)
    assert observed["ready"] and observed["matched"]
    assert observed["value"] == 9 and observed["previous_matched"] is False
    assert observed["continuity_id"] == "native-epoch-1"
    assert observed["bar_time"]
    assert hub._provider.calls == before


def test_missing_native_seed_does_not_fall_back_to_stale_history(hub):
    shared, selected = setup_shared(hub)
    shared.ready = False
    observed = snapshot(hub, selected)
    assert not observed["ready"]
    assert observed["reason"] == "Native RSI hazırlanıyor."
    assert hub._requests == {} and hub._provider.calls == []


def test_uncovered_members_keep_history_and_rule_maintenance(hub):
    shared, selected = setup_shared(hub)
    selected["symbols"].append({"market_type": "BIST", "symbol": "GARAN"})
    selected["symbols"].append({"market_type": "Kripto", "symbol": "BTCUSDT"})
    hub.configure([selected])
    assert set(hub._requests) == {("BIST", "GARAN", "1d"), ("Kripto", "BTCUSDT", "1d")}
    assert not hub.uses_live_updates(selected)
    assert shared.demands == {("BIST", "THYAO", "1D"): {14}}


def test_other_condition_and_chart_retain_their_own_history_jobs(hub):
    _, selected = setup_shared(hub)
    other = {**rule("ema", timeframe="1d"), "id": 2}
    hub.configure([selected, other])
    key = ("BIST", "THYAO", "1d")
    assert key in hub._requests
    assert snapshot(hub, selected)["ready"]
    hub.configure([selected])
    assert key not in hub._requests
    hub._chart_leases[key] = NOW + 120
    hub._rebuild_requests()
    assert key in hub._requests


@pytest.mark.parametrize("changes", [{"trigger": "bar_close"}, {"timeframe": "1m"}])
def test_unsupported_rules_keep_normal_path(hub, changes):
    shared, selected = setup_shared(hub)
    selected.update(changes)
    hub.configure([selected])
    assert shared.demands == {}
    assert not hub.uses_live_updates(selected)
    assert len(hub._requests) == 1


def test_native_plan_removal_restores_normal_history(hub):
    shared, selected = setup_shared(hub)
    shared.supported.clear()
    hub.configure([selected])
    assert shared.demands == {}
    assert not hub.uses_live_updates(selected)
    assert set(hub._requests) == {("BIST", "THYAO", "1d")}


def test_pure_standard_rule_processes_transient_native_updates_before_next_tick():
    selected = repository.save_rule(
        "admin",
        payload(
            category="technical",
            timeframe="1d",
            condition={
                "op": "lte",
                "left": {"field": "rsi", "period": 14},
                "right": 10,
            },
        ),
    )
    hub = LiveHub()
    hub.uses_live_updates = lambda rule: True
    engine = service.AdvancedAlarmEngine(hub)
    engine.bind_live_updates()
    engine.tick()
    hub.checked.clear()
    hub.publish("THYAO", False, 2)
    hub.publish("THYAO", True, 3)
    hub.publish("THYAO", False, 4)
    assert len(repository.events("admin")["events"]) == 1
    assert hub.checked == [(selected["id"], "THYAO")] * 3
    hub.uses_live_updates = lambda rule: False
    engine._index_live_rules()
    assert engine._live_index == {}
