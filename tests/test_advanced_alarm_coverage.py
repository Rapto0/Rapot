"""Offline sampled coverage, lease expiry, counter isolation and delivery guards."""

import copy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import advanced_alarm_routes as routes
from application.services import advanced_alarm_service as service
from application.services.advanced_alarm_market_data import AdvancedMarketData, Quote, Work
from application.services.advanced_alarm_series import Point, Series
from application.services.alarm_acceptance_lease import (
    PREFIX,
    AcceptanceLeaseGate,
    lease_entries,
    lease_manifest_sha256,
    validate_lease,
)
from db_session import get_session_factory
from infrastructure.repositories import advanced_alarm_repository as repo
from models import AdvancedAlarmEvent

NOW = datetime(2026, 10, 8, 7, 0, tzinfo=UTC)
RUN = "a" * 32


def payload():
    return {
        "name": "TEST coverage",
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
    }


def lease(rules):
    entries = lease_entries(rules)
    return {
        "schema": "rapot-alarm-acceptance-lease-v1",
        "run_id": RUN,
        "owner": PREFIX + RUN,
        "not_before": (NOW - timedelta(seconds=1)).isoformat(),
        "expires_at": (NOW + timedelta(hours=1)).isoformat(),
        "heartbeat_at": NOW.isoformat(),
        "approved_rules": entries,
        "manifest_sha256": lease_manifest_sha256(entries),
        "controller_manifest_sha256": "b" * 64,
    }


def test_coverage_missing_stale_and_invalidated_stay_distinct_without_io(tmp_path):
    settings = SimpleNamespace(
        database_path=str(tmp_path / "main.db"),
        advanced_alarm_cache_path=None,
        advanced_alarm_market_enabled=True,
        advanced_alarm_max_symbols=2000,
        advanced_alarm_quote_stale_seconds=120,
    )
    provider = SimpleNamespace(memory_epoch=lambda: 1)
    hub = AdvancedMarketData(
        settings, provider=provider, cache=object(), clock=lambda: NOW.timestamp()
    )
    hub._epoch = 1
    hub._state = "waiting"
    hub._connection = SimpleNamespace(connected=True)
    hub._universe = tuple(
        {"symbol": s, "market_type": "BIST"} for s in ("THYAO", "GARAN", "UNKNOWN")
    )
    hub._subscriptions = ("THYAO", "GARAN", "UNKNOWN")
    hub._quotes[("BIST", "THYAO")] = (Quote(123, NOW.timestamp() - 2, NOW.timestamp() - 1, 5), None)
    hub._quotes[("BIST", "GARAN")] = (
        Quote(50, NOW.timestamp() - 500, NOW.timestamp() - 499, 2),
        None,
    )
    point = Point(NOW.timestamp() - 60, NOW.timestamp(), True, {"private_price": 123})
    series = Series(
        (point,),
        NOW.timestamp() - 1,
        NOW.timestamp() - 60,
        "test",
        "v1",
        NOW.timestamp(),
        (NOW.timestamp() - 120,),
    )
    hub._series[("BIST", "THYAO", "1m")] = (series, None)
    hub._requests[("BIST", "UNKNOWN", "1m")] = Work(reason="provider", failures=3)
    result = hub.coverage()
    rows = {row["symbol"]: row for row in result["rows"]}
    assert rows["THYAO"]["quote"]["state"] == "fresh"
    assert rows["GARAN"]["quote"]["state"] == "stale"
    assert rows["UNKNOWN"]["quote"]["state"] == "missing"
    assert rows["UNKNOWN"]["quote"]["source_timestamp"] is None
    assert rows["THYAO"]["history_1m"]["native_gap_count"] == 1
    assert result["universe"]["equity_membership_verified"] is False
    assert "private_price" not in str(result) and "123" not in str(result)
    hub._connection.connected = False
    assert all(row["quote"]["state"] == "invalidated" for row in hub.coverage()["rows"])


@pytest.mark.parametrize(
    "change",
    ["expired", "heartbeat", "manifest", "revision", "duplicate", "owner", "future", "too_long"],
)
def test_lease_rejects_malformed_or_expired_grants(change):
    rule = {**payload(), "id": str(uuid4()), "revision": 1, "owner": PREFIX + RUN}
    value = lease([rule])
    assert validate_lease(value, RUN, NOW.timestamp())
    if change == "expired":
        value["expires_at"] = NOW.isoformat()
    elif change == "heartbeat":
        value["heartbeat_at"] = (NOW - timedelta(seconds=91)).isoformat()
    elif change == "manifest":
        value["manifest_sha256"] = "c" * 64
    elif change == "revision":
        value["approved_rules"][0]["revision"] = True
    elif change == "duplicate":
        value["approved_rules"] *= 2
    elif change == "owner":
        value["owner"] = "admin"
    elif change == "future":
        value["not_before"] = (NOW + timedelta(seconds=1)).isoformat()
    else:
        value["expires_at"] = (NOW + timedelta(days=2)).isoformat()
    with pytest.raises(ValueError):
        validate_lease(value, RUN, NOW.timestamp())


class Hub:
    def __init__(self):
        self.calls = 0
        self.sequence = 1

    def configure(self, rules):
        self.members = {r["id"]: r["symbols"] for r in rules}

    def symbols(self, rule_id):
        return self.members[rule_id]

    def symbol_count(self, rule_id):
        return len(self.members[rule_id])

    def snapshot(self, rule, symbol, now=None):
        self.calls += 1
        return {
            "ready": True,
            "matched": False,
            "observation_id": str(self.sequence),
            "continuity_id": "epoch",
            "bar_time": NOW.isoformat(),
            "observed_at": NOW.isoformat(),
            "value": 50,
            "values": {},
        }

    def status(self):
        return {}


def test_cached_rules_lose_lease_each_tick_but_regular_rules_continue(tmp_path):
    row = repo.save_rule(PREFIX + RUN, payload())
    repo.save_rule("admin", payload())
    rules = [{**row, "owner": PREFIX + RUN}]
    value = lease(rules)
    clock = [NOW.timestamp()]
    gate = AcceptanceLeaseGate(tmp_path, clock=lambda: clock[0], reader=lambda run: value)
    hub = Hub()
    engine = service.AdvancedAlarmEngine(hub, clock=lambda: 10, wall_clock=lambda: NOW)
    engine._lease_gate = gate
    engine.tick()
    assert hub.calls == 2
    clock[0] += 91
    engine.tick()
    assert hub.calls == 3
    assert gate.status["blocked_rules"] == 1
    engine.tick()
    assert hub.calls == 4 and gate.status["blocked_rules"] == 1
    data = engine.heartbeat("admin", test_run_id=RUN)
    assert data["selected"]["price"]["distinct_rule_revisions_ready"] == 1
    assert data["selected"]["price"]["checked"] == 1
    assert engine.heartbeat("other")["selected"] == {}
    assert engine.heartbeat("admin")["selected"]["price"]["checked"] == 3


def test_ordinary_rules_never_read_lease_and_test_payload_or_notify_changes_fail(tmp_path):
    rule = {**payload(), "id": str(uuid4()), "revision": 1, "owner": PREFIX + RUN}
    value = lease([rule])
    calls = []
    gate = AcceptanceLeaseGate(
        tmp_path, clock=lambda: NOW.timestamp(), reader=lambda run: (calls.append(run) or value)
    )
    normal = {**rule, "owner": "admin"}
    assert gate.filter_rules([normal]) == [normal] and calls == []
    assert gate.filter_rules([rule]) == [rule]
    changed = copy.deepcopy(rule)
    changed["condition"]["right"] = 999
    assert gate.filter_rules([changed]) == []
    changed = {**rule, "notify_telegram": True}
    assert gate.filter_rules([changed]) == []


def test_missing_lease_never_configures_reserved_rule_or_touches_normal_rule(tmp_path):
    reserved = repo.save_rule(PREFIX + RUN, payload())
    normal = repo.save_rule("admin", payload())
    hub = Hub()
    configured = []
    original = hub.configure

    def configure(rows):
        configured.extend(row["id"] for row in rows)
        original(rows)

    hub.configure = configure
    engine = service.AdvancedAlarmEngine(hub, wall_clock=lambda: NOW)
    engine._lease_gate = AcceptanceLeaseGate(tmp_path / "missing")
    engine.tick()
    assert configured == [normal["id"]] and reserved["id"] not in configured
    assert engine.heartbeat("admin", test_run_id=RUN)["selected"] == {}


def test_diagnostics_count_distinct_revisions_and_observation_transitions_bounded():
    clock = [NOW]
    engine = service.AdvancedAlarmEngine(Hub(), wall_clock=lambda: clock[0])
    rule = {**payload(), "id": str(uuid4()), "revision": 1, "owner": PREFIX + RUN}
    observation = {"continuity_id": "epoch1", "observation_id": "q1"}
    for _ in range(3):
        engine._observe_rule(rule, observation, True, NOW.isoformat())
    engine._observe_rule(rule, {}, False, NOW.isoformat())
    engine._publish_diagnostics()
    result = engine.heartbeat("admin", test_run_id=RUN)["selected"]["price"]
    assert result["checked"] == 4 and result["ready"] == 3 and result["unknown"] == 1
    assert result["observations"] == 1 and result["distinct_rule_revisions_ready"] == 1
    assert result["checked_rules_last_60s"] == result["ready_rules_last_60s"] == 1
    assert result["latest_ready_rules_last_60s"] == 0
    clock[0] += timedelta(seconds=61)
    engine._publish_diagnostics()
    expired = engine.heartbeat("admin", test_run_id=RUN)
    assert expired["selected"]["price"]["checked_rules_last_60s"] == 0
    assert expired["selected"]["price"]["ready_rules_last_60s"] == 0
    assert expired["selected"]["price"]["max_rule_check_age_seconds"] == 61
    assert expired["counters_as_of"] == clock[0].isoformat()
    engine._observe_rule(rule, {**observation, "continuity_id": "epoch2"}, True, NOW.isoformat())
    for index in range(3000):
        engine._observe_rule(
            {**rule, "id": str(index), "owner": "other"}, {}, False, NOW.isoformat()
        )
    engine._publish_diagnostics()
    assert len(engine._diagnostic_rules) == 3000
    assert engine.heartbeat("admin", test_run_id=RUN)["selected"] == {}
    assert engine.heartbeat("other")["selected"]["price"]["distinct_rule_revisions_checked"] == 3000


def test_reserved_owner_outbox_is_cancelled_before_any_sender():
    with get_session_factory()() as db:
        event = AdvancedAlarmEvent(
            owner=PREFIX + RUN,
            rule_id=str(uuid4()),
            revision=1,
            rule_name="TEST",
            category="price",
            symbol="THYAO",
            market_type="BIST",
            observation_id="q1",
            delivery_status="pending",
        )
        db.add(event)
        db.commit()
        identity = event.id
    assert repo.claim_delivery() is None
    with get_session_factory()() as db:
        event = db.get(AdvancedAlarmEvent, identity)
        assert event.delivery_status == "cancelled" and event.delivery_attempts == 0


def test_diagnostics_are_admin_private_and_do_not_read_repository(api_auth_users, monkeypatch):
    engine = service.AdvancedAlarmEngine(Hub())
    engine.hub.coverage = lambda: {"schema": "synthetic", "provider_calls": False}
    monkeypatch.setattr(service, "_engine", engine)
    monkeypatch.setattr(repo, "usage", lambda owner: pytest.fail("diagnostics read DB"))
    app = FastAPI()
    app.include_router(routes.router)
    with TestClient(app) as client:
        for path in ("/advanced-alarms/heartbeat", "/advanced-alarms/coverage"):
            assert client.get(path).status_code == 401
            response = client.get(
                path,
                headers={
                    "Authorization": "Bearer "
                    + api_auth_users.create_access_token({"sub": "admin"})
                },
            )
            assert (
                response.status_code == 200
                and response.headers["cache-control"] == "private, no-store"
            )
