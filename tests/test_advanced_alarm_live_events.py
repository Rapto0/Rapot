"""Ordered synchronous event delivery with real persistence and no network I/O."""

from datetime import UTC, datetime

import pytest

from application.services import advanced_alarm_service as service
from infrastructure.repositories import advanced_alarm_repository as repository
from tests.test_advanced_alarm_backend import Hub, payload, snapshot


class LiveHub(Hub):
    def __init__(self):
        super().__init__()
        self.listener = None
        self.observations = {}
        self.checked = []

    def set_update_listener(self, listener):
        self.listener = listener

    def snapshot(self, rule, symbol, now=None):
        self.checked.append((rule["id"], symbol["symbol"]))
        return self.observations.get(symbol["symbol"], snapshot())

    def publish(self, symbol, value, sequence, *, continuity="epoch1"):
        self.observations[symbol] = snapshot(
            matched=value, observation_id=f"q{sequence}", continuity_id=continuity
        )
        self.listener("BIST", symbol)


def custom_rule(symbol="THYAO", **changes):
    return payload(
        category="technical",
        timeframe="1d",
        symbols=[{"market_type": "BIST", "symbol": symbol}],
        condition=changes.pop(
            "condition",
            {
                "op": "eq",
                "left": {
                    "field": "custom",
                    "indicator": "rsi_votes",
                    "output": "buy_signal",
                    "inputs": {},
                },
                "right": 1,
            },
        ),
        **{"cooldown_seconds": 1, **changes},
    )


def make_engine():
    hub = LiveHub()
    engine = service.AdvancedAlarmEngine(
        hub, clock=lambda: 10, wall_clock=lambda: datetime.now(UTC)
    )
    engine.bind_live_updates()
    return engine, hub


def test_transient_signal_is_committed_before_next_update_and_only_targeted_rules_run(monkeypatch):
    selected = repository.save_rule("admin", custom_rule())
    unrelated = repository.save_rule("admin", custom_rule("GARAN"))
    ordinary = repository.save_rule("admin", payload())
    engine, hub = make_engine()
    engine.tick()
    hub.checked.clear()
    wakes = []
    engine.set_delivery_listener(lambda: wakes.append(True))
    # Three updates occur before the next one-second maintenance pass. The
    # intermediate true result must not disappear behind the last false result.
    hub.publish("THYAO", False, 2)
    hub.publish("THYAO", True, 3)
    assert len(repository.events("admin")["events"]) == 1
    hub.publish("THYAO", False, 4)
    assert len(repository.events("admin")["events"]) == 1
    assert hub.checked == [(selected["id"], "THYAO")] * 3
    assert all(key[0] not in {unrelated["id"], ordinary["id"]} for key in hub.checked)
    assert wakes == [True]
    assert engine._runtime["live_evaluation"]["checked"] == 3
    engine.tick()
    key = (selected["id"], selected["revision"], "THYAO", "BIST")
    assert repository.load_states([key])[key]["matched"] is False


def test_unchanged_live_prices_do_not_write_sqlite_or_reload_states(monkeypatch):
    repository.save_rule("admin", custom_rule())
    engine, hub = make_engine()
    engine.tick()
    writes, reads = [], []
    original = repository.apply_batch
    monkeypatch.setattr(
        repository, "apply_batch", lambda changes: writes.append(changes) or original(changes)
    )
    monkeypatch.setattr(repository, "load_states", lambda keys: reads.append(keys) or {})
    for sequence in range(2, 1002):
        hub.publish("THYAO", False, sequence)
    assert writes == [] and reads == []
    assert engine._runtime["live_evaluation"]["updates"] == 1000
    assert repository.events("admin")["events"] == []


def test_live_state_churn_batches_but_each_signal_event_remains_durable(monkeypatch):
    repository.save_rule("admin", custom_rule(mode="cooldown", cooldown_seconds=86400))
    engine, hub = make_engine()
    engine.tick()
    writes = []
    original = repository.apply_batch
    monkeypatch.setattr(
        repository, "apply_batch", lambda changes: writes.append(changes) or original(changes)
    )
    hub.publish("THYAO", True, 2)
    assert len(repository.events("admin")["events"]) == 1
    writes.clear()
    # Cooldown prevents further events. State changes can share the latest
    # checkpoint; a per-quote transaction would turn these into 500 writes.
    for sequence in range(3, 503):
        hub.publish("THYAO", sequence % 2 == 0, sequence)
    assert len(writes) <= 1
    assert len(engine._pending_live_states) <= 1
    engine.tick()
    assert not engine._pending_live_states


def test_callback_failure_resets_memory_and_propagates_to_source_continuity_guard(monkeypatch):
    selected = repository.save_rule("admin", custom_rule())
    engine, hub = make_engine()
    engine.tick()
    original = repository.apply_batch
    monkeypatch.setattr(
        repository,
        "apply_batch",
        lambda changes: (_ for _ in ()).throw(repository.CapacityPressure()),
    )
    with pytest.raises(repository.CapacityPressure):
        hub.publish("THYAO", True, 2)
    key = (selected["id"], selected["revision"], "THYAO", "BIST")
    assert engine._states[key] is None
    assert engine._runtime["live_evaluation"]["last_error"]
    monkeypatch.setattr(repository, "apply_batch", original)
    hub.publish("THYAO", True, 3, continuity="after-gap")
    assert repository.events("admin")["events"] == []


def test_shared_membership_bitmap_does_not_expand_rule_symbol_object_pairs(monkeypatch):
    engine, hub = make_engine()
    members = tuple({"market_type": "BIST", "symbol": f"SYM{index}"} for index in range(2000))
    rules = [
        {"id": str(i), "revision": 1, "condition": custom_rule()["condition"]} for i in range(3000)
    ]
    engine._rules = rules
    hub.memberships = {rule["id"]: members for rule in rules}
    engine._index_live_rules()
    assert len(engine._live_index) == 2000
    assert all(mask.bit_count() == 3000 for mask in engine._live_index.values())
    assert engine._runtime["live_evaluation"]["membership_groups"] == 1
    # IDs and revisions are stable; the same index survives the maintenance pass.
    previous = engine._live_index
    engine._index_live_rules()
    assert engine._live_index is previous


def test_rule_revision_change_blocks_stale_tick_until_reconfigured():
    selected = repository.save_rule("admin", custom_rule())
    engine, hub = make_engine()
    engine.tick()
    repository.save_rule(
        "admin", custom_rule(revision=selected["revision"], enabled=False), selected["id"]
    )
    hub.publish("THYAO", True, 2)
    assert repository.events("admin")["events"] == []
    engine.tick()
    assert engine._live_index == {}


def test_durable_event_wakes_delivery_without_waiting_for_poll_interval(monkeypatch):
    import asyncio

    from api.runtime import advanced_alarms as runtime

    async def exercise():
        engine, _ = make_engine()
        waiting, delivered, stop = asyncio.Event(), asyncio.Event(), asyncio.Event()
        calls = 0

        async def deliver():
            nonlocal calls
            calls += 1
            if calls == 1:
                waiting.set()
                return False
            delivered.set()
            stop.set()
            return True

        monkeypatch.setattr(runtime, "get_advanced_alarm_engine", lambda: engine)
        monkeypatch.setattr(runtime, "deliver_one", deliver)
        monkeypatch.setattr(repository, "prune_history", lambda: None)
        task = asyncio.create_task(runtime._deliver(stop))
        try:
            await asyncio.wait_for(waiting.wait(), timeout=1)
            engine._wake_delivery()
            await asyncio.wait_for(delivered.wait(), timeout=0.5)
            assert calls == 2
        finally:
            stop.set()
            await task
        assert engine._delivery_listener is None

    asyncio.run(exercise())


def test_live_rules_use_five_second_fair_maintenance_without_delaying_price_events():
    custom = repository.save_rule("admin", custom_rule(trigger="bar_close"))
    ordinary = repository.save_rule("admin", payload())
    engine, hub = make_engine()
    clock = [0.0]
    engine._clock = lambda: clock[0]
    engine.tick()
    hub.checked.clear()
    for elapsed in (1, 2, 3, 4):
        clock[0] = elapsed
        engine.tick()
    assert hub.checked == [(ordinary["id"], "THYAO")] * 4
    clock[0] = 5
    engine.tick()
    assert hub.checked[-2:] == [(ordinary["id"], "THYAO"), (custom["id"], "THYAO")]
    # A custom update consumes the corresponding symbol immediately between the
    # maintenance passes; explicit bar-close selection remains a hub decision.
    hub.publish("THYAO", False, 2)
    assert hub.checked[-1] == (custom["id"], "THYAO")


def test_large_shared_live_rule_set_reads_real_hub_snapshot_once_per_price(tmp_path, monkeypatch):
    import json
    import os
    import time
    from pathlib import Path
    from types import SimpleNamespace

    from sqlalchemy import func, select

    from api.routes.advanced_alarm_routes import AlarmWrite
    from application.services.advanced_alarm_market_data import AdvancedMarketData
    from application.services.custom_indicator_data import CustomIndicatorData
    from db_session import get_session_factory
    from models import AdvancedAlarmEvent, AdvancedAlarmRule
    from tests.test_advanced_alarm_market_data import MemoryCache, Provider
    from tests.test_custom_indicator_engine import START, NativeProvider, score_leaf

    clock = [START]
    params = AlarmWrite(**custom_rule(condition=score_leaf())).model_dump()
    # This is an isolated engine sizing fixture, not API quota/production capacity
    # acceptance: 3,000 identical technical rows are inserted only into temp SQLite.
    with get_session_factory()() as session:
        for number in range(3000):
            session.add(
                AdvancedAlarmRule(
                    id=f"synthetic-live-{number}",
                    owner="admin",
                    revision=1,
                    symbols_json=json.dumps(params["symbols"]),
                    condition_json=json.dumps(params["condition"]),
                    created_at=datetime.now(UTC).replace(tzinfo=None),
                    updated_at=datetime.now(UTC).replace(tzinfo=None),
                    **{
                        key: value
                        for key, value in params.items()
                        if key not in {"symbols", "condition", "revision"}
                    },
                )
            )
        session.commit()
    settings = SimpleNamespace(
        database_path=str(tmp_path / "sizing.sqlite3"),
        advanced_alarm_cache_path=None,
        advanced_alarm_market_enabled=True,
        advanced_alarm_all_bist_enabled=False,
        advanced_alarm_max_symbols=2000,
        advanced_alarm_quote_stale_seconds=120,
    )
    hub = AdvancedMarketData(
        settings, provider=Provider(), cache=MemoryCache(), clock=lambda: clock[0]
    )
    hub._custom = CustomIndicatorData(provider=NativeProvider(), clock=lambda: clock[0])
    engine = service.AdvancedAlarmEngine(
        hub, wall_clock=lambda: datetime.fromtimestamp(clock[0], UTC)
    )
    engine.bind_live_updates()
    engine.tick()
    identity, config = next(iter(hub.custom._configs.items()))
    key = ("BIST", "THYAO", identity)
    calls, writes = [], []
    original_snapshot, original_apply = hub.snapshot, repository.apply_batch
    monkeypatch.setattr(
        hub,
        "snapshot",
        lambda *args, **kwargs: calls.append(1) or original_snapshot(*args, **kwargs),
    )
    monkeypatch.setattr(
        repository,
        "apply_batch",
        lambda changes: writes.append(len(changes)) or original_apply(changes),
    )

    def publish(score, serial):
        clock[0] += 0.01
        point = {
            "time": START - 30,
            "end": START + 30,
            "confirmed": False,
            "ready": True,
            "outputs": {"score": score},
            "rows": [],
        }
        hub.custom.publish_live(
            [(key, config, point)],
            source=clock[0],
            received=clock[0],
            serial=serial,
            price=100,
            publication_epoch=hub.custom.publication_token(key[:2]),
            live_generation=hub.custom.live._generation,
            expected_epoch=hub.custom.provider.memory_epoch(),
        )
        started = time.perf_counter()
        engine.market_updated("BIST", "THYAO")
        return time.perf_counter() - started

    publish(60, 1)  # Durable baseline, no event.
    engine._flush_live_states(force=True)
    calls.clear()
    writes.clear()
    durations = [publish(60, serial) for serial in range(2, 7)]
    assert calls == [1] * 5 and writes == []
    assert engine._runtime["live_evaluation"]["checked"] == 18000
    event_seconds = publish(20, 7)
    assert len(calls) == 6
    with get_session_factory()() as session:
        assert session.scalar(select(func.count()).select_from(AdvancedAlarmEvent)) == 3000
    report = {
        "kind": "synthetic_temp_sqlite_3000_rules_single_shared_custom_observation",
        "api_category_quota_exercised": False,
        "production_capacity_proven": False,
        "rules_per_update": 3000,
        "shared_snapshot_reads_per_update": 1,
        "steady_durations_seconds": durations,
        "steady_database_writes": 0,
        "crossing_3000_durable_events_seconds": event_seconds,
        "crossing_write_batches": writes,
        "telegram_requests": 0,
        "provider_requests": 0,
    }
    if destination := os.environ.get("RAPOT_LIVE_RULE_REPORT"):
        Path(destination).write_text(json.dumps(report, indent=2), encoding="utf8")
