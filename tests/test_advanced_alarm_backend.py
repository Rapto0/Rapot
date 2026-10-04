"""Synthetic advanced-alarm acceptance: quotas, continuity, ownership and delivery."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from api.routes import advanced_alarm_routes as routes
from application.services import advanced_alarm_service as service
from db_session import get_session_factory
from infrastructure.repositories import advanced_alarm_repository as repo
from models import AdvancedAlarmRule, AdvancedAlarmState


def payload(**changes):
    return {
        "name": "Fiyat koşulu",
        "category": "price",
        "scope": "symbols",
        "watchlist_id": None,
        "symbols": [{"symbol": "THYAO", "market_type": "BIST"}],
        "timeframe": "1m",
        "trigger": "intrabar",
        "condition": {"op": "gt", "left": {"field": "price"}, "right": 100},
        "mode": "on_enter",
        "cooldown_seconds": 60,
        "enabled": True,
        "notify_telegram": False,
        **changes,
    }


def snapshot(**changes):
    return {
        "ready": True,
        "matched": False,
        "observation_id": "q1",
        "continuity_id": "epoch1",
        "bar_time": "2026-10-04T10:00:00Z",
        "observed_at": "2026-10-04T10:00:01Z",
        "source_timestamp": "2026-10-04T10:00:01Z",
        "value": 99,
        "values": {"price": 99},
        **changes,
    }


class Hub:
    def __init__(self):
        self.rules = []
        self.configurations = 0
        self.current = snapshot()
        self.before = None
        self.calls = 0

    def configure(self, rules):
        self.rules = rules
        self.configurations += 1
        self.memberships = {rule["id"]: rule["symbols"] for rule in rules}

    def symbols(self, rule_id):
        return self.memberships[rule_id]

    def symbol_count(self, rule_id):
        return len(self.symbols(rule_id))

    def snapshot(self, rule, symbol, now=None):
        self.calls += 1
        if self.before:
            callback, self.before = self.before, None
            callback()
        return dict(self.current)

    def status(self):
        return {"state": "synthetic", "realtime_verified": False}


@pytest.fixture
def engine(monkeypatch):
    hub = Hub()
    value = service.AdvancedAlarmEngine(
        hub,
        clock=lambda: 10,
        wall_clock=lambda: datetime.now(UTC) + timedelta(seconds=hub.calls * 61),
    )
    monkeypatch.setattr(service, "_engine", value)
    monkeypatch.setattr(service, "_delivery_retry_until", 0)
    return value, hub


@pytest.fixture
def client(api_auth_users, monkeypatch, engine):
    users = routes.get_current_admin_user.__globals__["USERS_DB"]
    monkeypatch.setitem(users, "other", {**users["admin"], "username": "other"})
    app = FastAPI()
    app.include_router(routes.router)
    with TestClient(app) as value:
        value.headers["Authorization"] = "Bearer " + api_auth_users.create_access_token(
            {"sub": "admin"}
        )
        yield value


def test_private_crud_versions_and_owner_isolation(client, api_auth_users):
    result = client.post("/advanced-alarms", json=payload())
    assert result.status_code == 201, result.text
    assert result.headers["cache-control"] == "private, no-store"
    rule = result.json()
    assert rule["revision"] == 1 and "owner" not in rule
    assert client.put(f"/advanced-alarms/{rule['id']}", json=payload()).status_code == 422
    assert (
        client.put(
            f"/advanced-alarms/{rule['id']}", json=payload(revision=1, enabled=False)
        ).status_code
        == 200
    )
    assert client.put(f"/advanced-alarms/{rule['id']}", json=payload(revision=1)).status_code == 409
    original = client.headers["Authorization"]
    client.headers["Authorization"] = "Bearer " + api_auth_users.create_access_token(
        {"sub": "other"}
    )
    assert client.get("/advanced-alarms").json()["rules"] == []
    assert client.get("/advanced-alarms/events").json()["events"] == []
    assert client.delete(f"/advanced-alarms/{rule['id']}").status_code == 404
    client.headers["Authorization"] = original
    assert client.delete(f"/advanced-alarms/{rule['id']}").json() == {"deleted": True}


@pytest.mark.parametrize("path", ["", "/events", "/status", "/watchlists"])
def test_no_anonymous_or_regular_access(client, api_auth_users, path):
    client.headers.pop("Authorization")
    response = client.get("/advanced-alarms" + path)
    assert response.status_code == 401 and response.headers["cache-control"] == "private, no-store"
    client.headers["Authorization"] = "Bearer " + api_auth_users.create_access_token(
        {"sub": "user"}
    )
    assert client.get("/advanced-alarms" + path).status_code == 403


def test_price_quota_cannot_hide_technical_conditions_and_bounded_membership(client):
    technical = {"op": "gt", "left": {"field": "rsi"}, "right": 50}
    assert client.post("/advanced-alarms", json=payload(condition=technical)).status_code == 422
    symbols = [{"symbol": f"S{i}", "market_type": "BIST"} for i in range(2001)]
    assert client.post("/advanced-alarms", json=payload(symbols=symbols)).status_code == 422
    assert (
        client.post(
            "/advanced-alarms", json=payload(category="watchlist", scope="all_bist", symbols=[])
        ).status_code
        == 201
    )


def seed_rules(category, count, *, enabled=True):
    now = datetime.now(UTC).replace(tzinfo=None)
    import json

    with get_session_factory()() as session:
        session.add_all(
            [
                AdvancedAlarmRule(
                    id=f"{category}-{i:04}",
                    owner="admin",
                    name=f"Alarm {i}",
                    category=category,
                    scope="symbols",
                    symbols_json=json.dumps(payload()["symbols"]),
                    condition_json=json.dumps(payload()["condition"]),
                    timeframe="1m",
                    trigger="intrabar",
                    mode="on_enter",
                    cooldown_seconds=60,
                    enabled=enabled,
                    notify_telegram=False,
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
                for i in range(count)
            ]
        )
        session.commit()


def test_exact_thousand_per_category_independently_and_pauses_count():
    for category in ("price", "technical", "watchlist"):
        seed_rules(category, 999, enabled=False)
        rule = repo.save_rule("admin", payload(category=category))
        assert repo.usage("admin")[category] == 1000
        with pytest.raises(repo.Conflict):
            repo.save_rule("admin", payload(category=category))
        assert (
            repo.save_rule(
                "admin", payload(category=category, revision=rule["revision"]), rule["id"]
            )["revision"]
            == 2
        )
    assert sum(repo.usage("admin").values()) == 3000


def test_creation_baseline_transition_no_duplicate_restart_and_gap(engine):
    value, hub = engine
    repo.save_rule("admin", payload())
    hub.current = snapshot(matched=True)
    value.tick()
    assert repo.events("admin")["events"] == []
    hub.current = snapshot(observation_id="q2", matched=False)
    value.tick()
    hub.current = snapshot(observation_id="q3", matched=True, value=101)
    value.tick()
    assert len(repo.events("admin")["events"]) == 1
    restarted = service.AdvancedAlarmEngine(hub, clock=lambda: 10)
    restarted.tick()
    assert len(repo.events("admin")["events"]) == 1
    hub.current = snapshot(observation_id="q4", matched=True, continuity_id="reconnected")
    restarted.tick()
    assert len(repo.events("admin")["events"]) == 1
    hub.current = snapshot(ready=False, observation_id=None, continuity_id="reconnected")
    restarted.tick()
    hub.current = snapshot(observation_id="q5", matched=True, continuity_id="reconnected")
    restarted.tick()
    assert len(repo.events("admin")["events"]) == 1


def test_watchlist_membership_is_dynamic_and_edit_cancels_pending(engine):
    value, hub = engine
    watchlist = repo.save_watchlist("admin", {"name": "Liste", "symbols": payload()["symbols"]})
    rule = repo.save_rule(
        "admin",
        payload(
            category="watchlist",
            scope="watchlist",
            watchlist_id=watchlist["id"],
            symbols=[],
            notify_telegram=True,
        ),
    )
    value.tick()
    hub.current = snapshot(observation_id="q2", matched=True)
    value.tick()
    assert repo.events("admin")["events"][0]["delivery_status"] == "pending"
    symbols = [{"symbol": "EREGL", "market_type": "BIST"}]
    repo.save_watchlist(
        "admin", {"name": "Liste", "symbols": symbols, "revision": 1}, watchlist["id"]
    )
    assert repo.events("admin")["events"][0]["delivery_status"] == "cancelled"
    value.tick()
    assert list(hub.symbols(rule["id"])) == symbols
    repo.delete_watchlist("admin", watchlist["id"])
    assert repo.list_rules("admin")[0]["state"] == "paused"
    assert repo.active_rules() == []


def test_edit_between_observation_and_commit_discards_old_result(engine):
    value, hub = engine
    rule = repo.save_rule("admin", payload())
    value.tick()
    hub.current = snapshot(observation_id="q2", matched=True)
    hub.before = lambda: repo.save_rule("admin", payload(enabled=False, revision=1), rule["id"])
    value.tick()
    assert repo.events("admin")["events"] == []
    with get_session_factory()() as session:
        assert session.scalar(select(func.count()).select_from(AdvancedAlarmState)) == 0


def test_unchanged_quotes_do_not_write_every_second_and_warming_creates_no_states(engine):
    value, hub = engine
    repo.save_rule("admin", payload())
    hub.current = snapshot(ready=False)
    value.tick()
    with get_session_factory()() as session:
        assert session.scalar(select(func.count()).select_from(AdvancedAlarmState)) == 0
    hub.current = snapshot()
    value.tick()
    for number in range(2, 15):
        hub.current = snapshot(observation_id=f"q{number}")
        value.tick()
        assert value.status("admin")["evaluation"]["state_changes"] == 0


def test_thousand_rules_shared_input_batch_and_visible_backlog(engine):
    value, hub = engine
    seed_rules("price", 1000)
    seed_rules("technical", 1)
    value.tick()
    assert value.status("admin")["evaluation"]["checked"] == 250
    assert value.status("admin")["evaluation"]["backlog"] == 751
    for _ in range(4):
        value.tick()
    with get_session_factory()() as session:
        assert session.scalar(select(func.count()).select_from(AdvancedAlarmState)) == 1001
    assert value.status("admin")["evaluation"]["checked"] == 1001
    assert value.status("admin")["evaluation"]["state_changes"] == 1
    hub.current = snapshot(observation_id="changed-price-only")
    value.tick()
    assert value.status("admin")["evaluation"]["state_changes"] == 0
    assert value.status("admin")["last_error"] is None


def test_modes_once_per_bar_and_cooldown_are_not_each_poll():
    rule = payload(mode="once_per_bar")
    now = datetime.now(UTC)
    state, event = service.AdvancedAlarmEngine._evaluate(rule, snapshot(matched=True), None, now)
    assert event is None
    state, event = service.AdvancedAlarmEngine._evaluate(
        rule, snapshot(matched=True, observation_id="q2"), state, now
    )
    assert event is None
    state, event = service.AdvancedAlarmEngine._evaluate(
        rule,
        snapshot(matched=True, observation_id="q3", bar_time="2026-10-04T10:01:00Z"),
        state,
        now,
    )
    assert event
    rule["mode"] = "cooldown"
    state, event = service.AdvancedAlarmEngine._evaluate(
        rule, snapshot(matched=True, observation_id="q4"), state, now + timedelta(seconds=1)
    )
    assert event is None
    state, event = service.AdvancedAlarmEngine._evaluate(
        rule, snapshot(matched=True, observation_id="q5"), state, now + timedelta(seconds=61)
    )
    assert event


def test_outbox_retry_after_persists_and_blocks_shared_target(engine, monkeypatch):
    value, hub = engine
    repo.save_rule("admin", payload(notify_telegram=True))
    value.tick()
    hub.current = snapshot(matched=True, observation_id="q2")
    value.tick()
    sender = AsyncMock(side_effect=service.TelegramFailure(retry_after=300))
    assert asyncio.run(service.deliver_one(sender))
    row = repo.events("admin")["events"][0]
    assert row["delivery_status"] == "pending" and row["delivery_attempts"] == 1
    assert datetime.fromisoformat(row["next_attempt_at"].replace("Z", "+00:00")) >= datetime.now(
        UTC
    ) + timedelta(seconds=290)
    assert asyncio.run(service.deliver_one(sender)) is False
    assert sender.await_count == 1
    monkeypatch.setattr(service, "_delivery_retry_until", 0)
    assert (
        asyncio.run(service.deliver_one(AsyncMock())) is False
    )  # durable global pause survives worker restart
    future = datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=301)
    monkeypatch.setattr(repo, "utc_now_naive", lambda: future)
    assert asyncio.run(service.deliver_one(AsyncMock()))
    assert repo.events("admin")["events"][0]["delivery_status"] == "sent"


def test_outbox_backpressure_is_visible_not_silent_loss(engine, monkeypatch):
    value, hub = engine
    monkeypatch.setattr(repo, "MAX_PENDING", 1)
    repo.save_rule("admin", payload(notify_telegram=True))
    value.tick()
    for n, matched in [(2, True), (3, False), (4, True)]:
        hub.current = snapshot(observation_id=f"q{n}", matched=matched)
        value.tick()
    rows = repo.events("admin")["events"]
    assert len(rows) == 2
    assert {r["delivery_status"] for r in rows} == {"pending", "failed"}
    assert any("kuyruğu dolu" in (r["delivery_error"] or "") for r in rows)
    latest = repo.events("admin", limit=1)
    assert latest["events"][0]["id"] == rows[0]["id"]
    incremental = repo.events("admin", after_id=rows[1]["id"])
    assert incremental["events"][0]["id"] == rows[0]["id"]


def test_runtime_disabled_does_not_create_hub(monkeypatch):
    from api.runtime import advanced_alarms as runtime

    monkeypatch.setattr(runtime.settings, "advanced_alarms_enabled", False)
    monkeypatch.setattr(
        runtime, "get_advanced_alarm_engine", lambda: pytest.fail("No engine when disabled")
    )
    asyncio.run(runtime.start_advanced_alarms())
    asyncio.run(runtime.stop_advanced_alarms())


def test_on_enter_recross_obeys_global_cooldown():
    rule = payload(cooldown_seconds=60)
    now = datetime.now(UTC)
    state, _ = service.AdvancedAlarmEngine._evaluate(rule, snapshot(), None, now)
    state, fired = service.AdvancedAlarmEngine._evaluate(
        rule, snapshot(matched=True, observation_id="2"), state, now
    )
    assert fired
    state, _ = service.AdvancedAlarmEngine._evaluate(
        rule, snapshot(observation_id="3"), state, now + timedelta(seconds=1)
    )
    state, fired = service.AdvancedAlarmEngine._evaluate(
        rule, snapshot(matched=True, observation_id="4"), state, now + timedelta(seconds=2)
    )
    assert fired is None
    state, _ = service.AdvancedAlarmEngine._evaluate(
        rule, snapshot(observation_id="5"), state, now + timedelta(seconds=61)
    )
    _, fired = service.AdvancedAlarmEngine._evaluate(
        rule, snapshot(matched=True, observation_id="6"), state, now + timedelta(seconds=62)
    )
    assert fired


def test_delivery_actual_http429_parser_is_bounded_and_secret_free(monkeypatch, caplog):
    import logging

    monkeypatch.setattr(service.settings, "telegram_token", "SECRET-BOT-VALUE")
    monkeypatch.setattr(service.settings, "telegram_chat_id", "SECRET-TARGET")

    class Response:
        status = 429
        content = AsyncMock()
        content.read.return_value = b'{"ok":false,"parameters":{"retry_after":123}}'

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

    class Client:
        def __init__(self, **kwargs):
            assert kwargs["trust_env"] is False

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def post(self, url, **kwargs):
            assert kwargs["allow_redirects"] is False
            return Response()

    monkeypatch.setattr(service.aiohttp, "ClientSession", Client)
    caplog.set_level(logging.DEBUG)
    with pytest.raises(service.TelegramFailure) as error:
        asyncio.run(
            service.send_telegram(
                {
                    "id": 1,
                    "rule_name": "PRIVATE-NAME",
                    "symbol": "THYAO",
                    "market_type": "BIST",
                    "category": "price",
                    "value": 100,
                    "observed_at": "2026-10-04T10:00:00Z",
                }
            )
        )
    assert error.value.retry_after == 123
    assert all(
        secret not in caplog.text
        for secret in ("SECRET-BOT-VALUE", "SECRET-TARGET", "PRIVATE-NAME")
    )
    Response.content.read.assert_awaited_once_with(65537)


def test_worker_failure_drains_other_worker_before_return(monkeypatch):
    from api.runtime import advanced_alarms as runtime

    async def exercise():
        entered = asyncio.Event()
        release = asyncio.Event()
        drained = asyncio.Event()

        async def evaluate(stop, engine):
            await entered.wait()
            raise RuntimeError("synthetic failure")

        async def delivery(stop):
            entered.set()
            await release.wait()
            assert stop.is_set()
            drained.set()

        monkeypatch.setattr(runtime, "_evaluate", evaluate)
        monkeypatch.setattr(runtime, "_deliver", delivery)
        task = asyncio.create_task(runtime._workers(asyncio.Event(), object()))
        await entered.wait()
        for _ in range(5):
            await asyncio.sleep(0)
        assert not task.done()
        release.set()
        with pytest.raises(RuntimeError, match="synthetic"):
            await task
        assert drained.is_set()

    asyncio.run(exercise())


def test_private_history_is_memory_only(client, engine, monkeypatch):
    _, hub = engine
    captured = []

    def history(symbol, **kwargs):
        captured.append((symbol, kwargs))
        return {"candles": [], "state": "warming", "reason": "sentetik", "realtime_verified": False}

    monkeypatch.setattr(hub, "history", history, raising=False)
    response = client.get("/advanced-alarms/history?symbol=THYAO.IS&limit=1000")
    assert response.status_code == 200 and response.headers["cache-control"] == "private, no-store"
    assert captured == [("THYAO", {"market_type": "BIST", "timeframe": "1m", "limit": 1000})]
    assert client.get("/advanced-alarms/history?symbol=THYAO&limit=1501").status_code == 422


def test_once_per_bar_first_false_arms_same_bar_and_invalid_boolean_breaks_continuity():
    now = datetime.now(UTC)
    rule = payload(mode="once_per_bar")
    state, fired = service.AdvancedAlarmEngine._evaluate(rule, snapshot(), None, now)
    assert fired is None
    state, fired = service.AdvancedAlarmEngine._evaluate(
        rule, snapshot(matched=True, observation_id="q2"), state, now
    )
    assert fired is not None
    state, fired = service.AdvancedAlarmEngine._evaluate(
        rule, snapshot(matched="false", observation_id="q3"), state, now
    )
    assert state["ready"] is False and fired is None
    state, fired = service.AdvancedAlarmEngine._evaluate(
        rule, snapshot(matched=True, observation_id="q4"), state, now
    )
    assert fired is None


def test_disk_backpressure_preserves_pending_and_does_not_send(engine, monkeypatch):
    from collections import namedtuple

    value, hub = engine
    repo.save_rule("admin", payload(notify_telegram=True))
    value.tick()
    hub.current = snapshot(matched=True, observation_id="q2")
    value.tick()
    disk = namedtuple("usage", "total used free")
    monkeypatch.setattr(repo.shutil, "disk_usage", lambda path: disk(1000000000, 999999999, 1))
    monkeypatch.setattr(repo, "_storage_cache", None)
    hub.current = snapshot(matched=False, observation_id="q3")
    value.tick()
    assert value.status("admin")["backpressure"] == "disk_reserve"
    assert value.status("admin")["storage"]["backpressure"] is True
    assert repo.events("admin")["events"][0]["delivery_status"] == "pending"
    sender = AsyncMock()
    with pytest.raises(repo.CapacityPressure):
        asyncio.run(service.deliver_one(sender))
    sender.assert_not_called()


def test_retention_preserves_pending_and_active_rules_without_expiry(engine, monkeypatch):
    from models import AdvancedAlarmEvent

    value, hub = engine
    rule = repo.save_rule("admin", payload(notify_telegram=True))
    value.tick()
    hub.current = snapshot(matched=True, observation_id="q2")
    value.tick()
    row = repo.events("admin")["events"][0]
    now = datetime.now(UTC).replace(tzinfo=None)
    with get_session_factory()() as session:
        session.get(AdvancedAlarmEvent, row["id"]).created_at = now - timedelta(days=365)
        session.get(AdvancedAlarmRule, rule["id"]).created_at = now - timedelta(days=365)
        session.commit()
    repo.prune_history()
    assert len(repo.events("admin")["events"]) == 1
    assert repo.list_rules("admin")[0]["enabled"] is True


def test_three_thousand_rules_resource_sample(engine, tmp_path, monkeypatch):
    """Synthetic CPU/Python-memory measurements, explicitly not provider throughput."""
    import json
    import os
    import time
    import tracemalloc

    value, hub = engine
    for category in ("price", "technical", "watchlist"):
        seed_rules(category, 1000)
    tracemalloc.start()
    before, _ = tracemalloc.get_traced_memory()
    started = time.perf_counter()
    cpu = time.process_time()
    for _ in range(12):
        value.tick()
    warm_seconds = time.perf_counter() - started
    warm_cpu = time.process_time() - cpu
    retained, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    with get_session_factory()() as session:
        assert session.scalar(select(func.count()).select_from(AdvancedAlarmState)) == 3000
    durations = []
    cpu = time.process_time()
    for i in range(6):
        hub.current = snapshot(observation_id=f"updated-{i}")
        started = time.perf_counter()
        value.tick()
        durations.append(time.perf_counter() - started)
        assert value.status("admin")["evaluation"]["state_changes"] == 0
    cpu_seconds = time.process_time() - cpu
    assert len(value._states) == 3000
    sample = {
        "kind": "synthetic_cached_input_no_provider_io",
        "rules": 3000,
        "rule_symbol_pairs": 3000,
        "cold_ticks": 12,
        "cold_wall_seconds": warm_seconds,
        "cold_cpu_seconds": warm_cpu,
        "python_retained_bytes": retained - before,
        "python_peak_bytes": peak - before,
        "warm_ticks": 6,
        "warm_max_wall_seconds": max(durations),
        "warm_cpu_seconds": cpu_seconds,
        "warm_checkpoint_writes": 0,
        "state_cache_limit": service.STATE_CACHE_LIMIT,
    }
    destination = os.environ.get("RAPOT_ADVANCED_ALARM_REPORT")
    if destination:
        from pathlib import Path

        Path(destination).write_text(json.dumps(sample, indent=2), encoding="utf8")
    assert sample["python_retained_bytes"] < 32 * 1024**2


def test_hundred_thousand_state_storage_sample(tmp_path):
    """Measure real SQLite pages with synthetic rows; no production database is opened."""
    import json
    import os
    import time

    from sqlalchemy import insert, text

    seed_rules("price", 50)
    now = datetime.now(UTC).replace(tzinfo=None)
    started = time.perf_counter()
    with get_session_factory()() as session:
        before = session.scalar(text("PRAGMA page_count")) * session.scalar(
            text("PRAGMA page_size")
        )
        for rule in range(50):
            for offset in range(0, 2000, 1000):
                rows = [
                    {
                        "rule_id": f"price-{rule:04}",
                        "revision": 1,
                        "symbol": f"S{i}",
                        "market_type": "BIST",
                        "observation_id": "a" * 64,
                        "continuity_id": "b" * 64,
                        "matched": False,
                        "ready": True,
                        "last_bar": "2026-10-04T10:00:00Z",
                        "last_triggered_at": now,
                        "updated_at": now,
                    }
                    for i in range(offset, offset + 1000)
                ]
                session.execute(insert(AdvancedAlarmState), rows)
        session.commit()
        assert session.scalar(select(func.count()).select_from(AdvancedAlarmState)) == 100000
        after = session.scalar(text("PRAGMA page_count")) * session.scalar(text("PRAGMA page_size"))
    result = {
        "kind": "synthetic_sqlite_rows_and_indexes",
        "rows": 100000,
        "page_bytes_increase": after - before,
        "bytes_per_state": (after - before) / 100000,
        "elapsed_seconds": time.perf_counter() - started,
        "estimate_600000_states_bytes": (after - before) * 6,
        "estimate_6000000_states_bytes": (after - before) * 60,
        "excludes": [
            "provider_cache",
            "rule_definitions",
            "events",
            "WAL_headroom",
            "fragmentation",
        ],
    }
    destination = os.environ.get("RAPOT_ADVANCED_STATE_REPORT")
    if destination:
        from pathlib import Path

        Path(destination).write_text(json.dumps(result, indent=2), encoding="utf8")
    assert after > before


def test_pause_while_send_in_flight_reports_actual_delivery(engine):
    value, hub = engine
    rule = repo.save_rule("admin", payload(notify_telegram=True))
    value.tick()
    hub.current = snapshot(matched=True, observation_id="q2")
    value.tick()

    async def accepted_then_paused(event):
        repo.save_rule(
            "admin", payload(notify_telegram=True, enabled=False, revision=1), rule["id"]
        )

    assert asyncio.run(service.deliver_one(accepted_then_paused))
    assert repo.events("admin")["events"][0]["delivery_status"] == "sent"
    assert repo.list_rules("admin")[0]["enabled"] is False


def test_per_rule_failure_is_visible_only_to_its_owner(engine):
    value, hub = engine
    repo.save_rule("admin", payload())
    hub.current = snapshot(ready=False, reason="Mum verisi henüz hazır değil.")
    value.tick()
    row = value.rules("admin")[0]
    assert row["state"] == "error" and row["last_checked_at"]
    assert row["last_error"] == "Mum verisi henüz hazır değil."
    assert value.rules("other") == []


def test_unchanged_rule_refresh_does_not_reconfigure_provider_jobs(engine):
    value, hub = engine
    clock = [10.0]
    value._clock = lambda: clock[0]
    rule = repo.save_rule("admin", payload())
    value.tick()
    assert hub.configurations == 1
    clock[0] = 16.0
    value.tick()
    assert hub.configurations == 1
    repo.save_rule("admin", payload(revision=1, name="Yeni ad"), rule["id"])
    value.tick()
    assert hub.configurations == 2
