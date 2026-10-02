"""Offline acceptance of authenticated, persistent server alarm behavior."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from api.routes import alarm_routes
from application.services import server_alarm_evaluator as evaluator
from application.services import server_alarm_service as service
from db_session import get_session_factory
from infrastructure.repositories import server_alarm_repository as repository
from models import ServerAlarmRule, ServerAlarmSymbolState


def payload(**changes):
    return {
        "name": "Saatlik RSI",
        "symbols": [{"symbol": "BTCUSDT", "market_type": "Kripto"}],
        "indicator": "rsi",
        "timeframe": "1h",
        "side": "dip",
        "threshold": 30,
        "mode": "on_enter",
        "enabled": True,
        "notify_telegram": False,
        **changes,
    }


def evaluation(hour=10, *, matched=True, previous_matched=False):
    return {
        "bar_time": f"2026-10-02T{hour:02}:00:00Z",
        "bar_closed_at": f"2026-10-02T{hour + 1:02}:00:00Z",
        "value": 25.0,
        "matched": matched,
        "previous_matched": previous_matched,
        "detail": "sentetik",
    }


@pytest.fixture
def alarm_clock(monkeypatch):
    clock = {"now": datetime(2026, 10, 2, 10)}
    monkeypatch.setattr(repository, "utc_now_naive", lambda: clock["now"])
    monkeypatch.setattr(service, "utc_now_naive", lambda: clock["now"])
    monkeypatch.setattr(
        service, "_runtime", {"running": False, "last_cycle_at": None, "last_cycle_error": None}
    )
    return clock


@pytest.fixture
def admin_client(api_auth_users, monkeypatch, alarm_clock):
    users = alarm_routes.get_current_admin_user.__globals__["USERS_DB"]
    monkeypatch.setitem(users, "other-admin", {**users["admin"], "username": "other-admin"})
    app = FastAPI()
    app.include_router(alarm_routes.router)
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer " + api_auth_users.create_access_token(
            {"sub": "admin"}
        )
        yield client


def test_api_crud_owner_isolation_and_event_history(admin_client, api_auth_users):
    response = admin_client.post("/alarms", json=payload())
    assert response.status_code == 201
    rule = response.json()
    assert rule["state"] == "pending" and rule["created_at"].endswith("Z")
    repository.record_evaluation(rule, rule["symbols"][0], evaluation())
    assert admin_client.get("/alarms/events").json()["events"][0]["rule_name"] == rule["name"]

    admin_token = admin_client.headers["Authorization"]
    admin_client.headers["Authorization"] = "Bearer " + api_auth_users.create_access_token(
        {"sub": "other-admin"}
    )
    assert admin_client.get("/alarms").json()["rules"] == []
    assert admin_client.get("/alarms/events").json()["events"] == []
    assert admin_client.put(f"/alarms/{rule['id']}", json=payload()).status_code == 404
    assert admin_client.delete(f"/alarms/{rule['id']}").status_code == 404

    admin_client.headers["Authorization"] = admin_token
    updated = admin_client.put(f"/alarms/{rule['id']}", json=payload(enabled=False)).json()
    assert updated["state"] == "paused" and updated["revision"] == 2
    assert admin_client.delete(f"/alarms/{rule['id']}").json() == {"deleted": True}
    assert admin_client.get("/alarms").json()["rules"] == []
    assert len(admin_client.get("/alarms/events").json()["events"]) == 1


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/alarms"),
        ("get", "/alarms/events"),
        ("post", "/alarms"),
        ("put", "/alarms/a"),
        ("delete", "/alarms/a"),
    ],
)
def test_every_route_requires_admin(admin_client, api_auth_users, method, path):
    admin_client.headers.pop("Authorization")
    kwargs = {"json": payload()} if method in {"post", "put"} else {}
    assert getattr(admin_client, method)(path, **kwargs).status_code == 401
    admin_client.headers["Authorization"] = "Bearer " + api_auth_users.create_access_token(
        {"sub": "user"}
    )
    assert getattr(admin_client, method)(path, **kwargs).status_code == 403


@pytest.mark.parametrize(
    "changes",
    [
        {"name": " "},
        {"name": "alarm\nname"},
        {"indicator": "pine"},
        {"threshold": 101},
        {"indicator": "combo", "threshold": 0},
        {"indicator": "hunter", "threshold": 2.5},
        {"symbols": []},
        {"symbols": [{"symbol": "ETHBTC", "market_type": "Kripto"}]},
        {"symbols": [{"symbol": "BTCUSDT", "market_type": "Kripto"}] * 2},
        {"symbols": [{"symbol": "THYAO", "market_type": "BIST"}], "timeframe": "1h"},
        {"symbols": [{"symbol": "THYAO", "market_type": "BIST"}], "timeframe": "4h"},
        {"symbols": [{"symbol": "../.env", "market_type": "BIST"}]},
        {"owner": "other-admin"},
        {"telegram_chat_id": "attacker"},
    ],
)
def test_api_rejects_unsupported_or_unsafe_rules(admin_client, changes):
    assert admin_client.post("/alarms", json=payload(**changes)).status_code == 422
    assert admin_client.get("/alarms").json()["rules"] == []


def test_missing_telegram_rejected_without_losing_unnotified_rule(admin_client, monkeypatch):
    monkeypatch.setattr(service.settings, "telegram_token", "")
    assert admin_client.post("/alarms", json=payload(notify_telegram=True)).status_code == 422
    assert admin_client.post("/alarms", json=payload()).status_code == 201
    assert admin_client.get("/alarms").json()["runtime"]["telegram_configured"] is False


def test_can_pause_notified_rule_after_telegram_configuration_is_removed(admin_client, monkeypatch):
    created = admin_client.post("/alarms", json=payload(notify_telegram=True))
    assert created.status_code == 201
    rule = created.json()
    monkeypatch.setattr(service.settings, "telegram_token", "")
    paused = admin_client.put(
        f"/alarms/{rule['id']}", json=payload(notify_telegram=True, enabled=False)
    )
    assert paused.status_code == 200
    assert paused.json()["state"] == "paused"
    assert (
        admin_client.put(
            f"/alarms/{rule['id']}", json=payload(notify_telegram=True, enabled=True)
        ).status_code
        == 422
    )


def test_normalizes_bist_and_validates_limits(admin_client):
    rule = admin_client.post(
        "/alarms",
        json=payload(symbols=[{"symbol": "thyao.is", "market_type": "BIST"}], timeframe="1d"),
    ).json()
    assert rule["symbols"][0]["symbol"] == "THYAO"
    limits = admin_client.get("/alarms").json()["limits"]
    assert limits == {"max_rules": 50, "max_symbols_per_rule": 20, "max_subscriptions": 100}
    assert admin_client.get("/alarms/events?limit=201").status_code == 422


def test_global_caps_include_other_admin_and_paused_rules(alarm_clock):
    symbols = [{"symbol": f"COIN{i}USDT", "market_type": "Kripto"} for i in range(20)]
    for _ in range(5):
        service.save_rule("other-admin", payload(symbols=symbols, enabled=False))
    with pytest.raises(service.AlarmLimitError):
        service.save_rule("admin", payload())
    with get_session_factory()() as session:
        assert session.scalar(select(func.count()).select_from(ServerAlarmRule)) == 5


def test_rule_cap_and_update_at_cap(alarm_clock):
    rules = [service.save_rule("admin", payload(enabled=False)) for _ in range(50)]
    with pytest.raises(service.AlarmLimitError):
        service.save_rule("admin", payload())
    assert (
        service.save_rule("admin", payload(name="Updated"), rule_id=rules[0]["id"])["revision"] == 2
    )
    service.delete_rule("admin", rules[-1]["id"])
    assert service.save_rule("admin", payload())["id"]


def test_concurrent_saves_cannot_exceed_global_cap(alarm_clock):
    for _ in range(49):
        service.save_rule("admin", payload())

    def save_one():
        try:
            service.save_rule("admin", payload())
            return "created"
        except service.AlarmLimitError:
            return "full"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: save_one(), range(2))) == ["created", "full"]
    assert len(service.list_rules("admin")) == 50


def test_historical_baseline_then_new_close_persists_dedup_across_cycles(alarm_clock, monkeypatch):
    rule = service.save_rule("admin", payload())
    fake = AsyncMock(return_value=evaluation(8))
    monkeypatch.setattr(evaluator, "evaluate_alarm_symbol", fake)
    asyncio.run(service.run_alarm_cycle())
    assert service.list_events("admin") == []
    fake.return_value = evaluation(10)
    asyncio.run(service.run_alarm_cycle())
    # A new service loop has no in-memory previous-bar state; SQLite still suppresses duplicates.
    asyncio.run(service.run_alarm_cycle())
    assert len(service.list_events("admin")) == 1
    assert service.list_rules("admin")[0]["state"] == "active"
    with get_session_factory()() as session:
        state = session.scalar(
            select(ServerAlarmSymbolState).where(ServerAlarmSymbolState.rule_id == rule["id"])
        )
        assert state.bar_time == datetime(2026, 10, 2, 10)
        assert state.matched is True


@pytest.mark.parametrize("mode,expected", [("on_enter", 0), ("once_per_bar", 2)])
def test_condition_frequency_uses_closed_bar_and_never_replays_older_bar(
    alarm_clock, mode, expected
):
    rule = service.save_rule("admin", payload(mode=mode))
    for hour in (10, 11, 10, 11):
        repository.record_evaluation(
            rule, rule["symbols"][0], evaluation(hour, previous_matched=True)
        )
    assert len(service.list_events("admin")) == expected


@pytest.mark.parametrize("action", ["edit", "pause", "delete"])
def test_in_flight_snapshot_cannot_commit_after_revision_change(alarm_clock, monkeypatch, action):
    rule = service.save_rule("admin", payload())

    async def raced(**kwargs):
        if action == "delete":
            service.delete_rule("admin", rule["id"])
        else:
            service.save_rule("admin", payload(enabled=action != "pause"), rule_id=rule["id"])
        return evaluation()

    monkeypatch.setattr(evaluator, "evaluate_alarm_symbol", raced)
    asyncio.run(service.run_alarm_cycle())
    assert service.list_events("admin") == []
    if action != "delete":
        assert service.list_rules("admin")[0]["last_checked_at"] is None


def test_unknown_and_safe_evaluation_errors_keep_loop_alive_without_secret_leak(
    alarm_clock, monkeypatch
):
    service.save_rule("admin", payload())
    fake = AsyncMock(side_effect=RuntimeError("token=secret-chat-secret"))
    monkeypatch.setattr(evaluator, "evaluate_alarm_symbol", fake)
    asyncio.run(service.run_alarm_cycle())
    result = service.list_rules("admin")[0]
    assert result["state"] == "error" and "secret" not in result["last_error"]
    fake.side_effect = evaluator.AlarmEvaluationError("Veri eskimiş.")
    asyncio.run(service.run_alarm_cycle())
    assert "Veri eskimiş." in service.list_rules("admin")[0]["last_error"]
    assert service.runtime_status()["last_cycle_at"]
    fake.side_effect = None
    fake.return_value = evaluation()
    asyncio.run(service.run_alarm_cycle())
    assert service.list_rules("admin")[0]["last_error"] is None


def test_empty_and_stopped_cycles_do_not_fetch_or_send(alarm_clock, monkeypatch):
    fake = AsyncMock()
    sender = AsyncMock()
    monkeypatch.setattr(evaluator, "evaluate_alarm_symbol", fake)
    monkeypatch.setattr(service, "send_telegram_message", sender)
    asyncio.run(service.run_alarm_cycle())
    service.save_rule("admin", payload())
    asyncio.run(service.run_alarm_cycle(should_stop=lambda: True))
    fake.assert_not_called()
    sender.assert_not_called()


def test_stop_after_fetch_prevents_event_commit(alarm_clock, monkeypatch):
    service.save_rule("admin", payload())
    stopped = False

    async def stop_during_fetch(**kwargs):
        nonlocal stopped
        stopped = True
        return evaluation()

    monkeypatch.setattr(evaluator, "evaluate_alarm_symbol", stop_during_fetch)
    asyncio.run(service.run_alarm_cycle(should_stop=lambda: stopped))
    assert service.list_events("admin") == []


def queued_event():
    rule = service.save_rule("admin", payload(notify_telegram=True))
    repository.record_evaluation(rule, rule["symbols"][0], evaluation())
    return rule


def test_delivery_retry_is_durable_bounded_and_sanitized(alarm_clock, monkeypatch):
    queued_event()
    sender = AsyncMock(side_effect=RuntimeError("https://api.telegram.org/botSECRET/sendMessage"))
    monkeypatch.setattr(service, "send_telegram_message", sender)
    asyncio.run(service.deliver_pending_notifications())
    event = service.list_events("admin")[0]
    assert event["delivery_status"] == "pending" and "SECRET" not in event["delivery_error"]
    asyncio.run(service.deliver_pending_notifications())
    assert sender.await_count == 1
    for _ in range(3):
        alarm_clock["now"] += timedelta(minutes=10)
        asyncio.run(service.deliver_pending_notifications())
    assert sender.await_count == 3
    assert service.list_events("admin")[0]["delivery_status"] == "failed"


def test_missing_configuration_preserves_queue_then_sends_once(alarm_clock, monkeypatch):
    queued_event()
    monkeypatch.setattr(service, "telegram_configured", lambda: False)
    sender = AsyncMock()
    monkeypatch.setattr(service, "send_telegram_message", sender)
    asyncio.run(service.deliver_pending_notifications())
    assert service.list_events("admin")[0]["delivery_status"] == "pending"
    sender.assert_not_called()
    monkeypatch.setattr(service, "telegram_configured", lambda: True)
    asyncio.run(service.deliver_pending_notifications())
    asyncio.run(service.deliver_pending_notifications())
    assert sender.await_count == 1
    assert service.list_events("admin")[0]["delivery_status"] == "sent"
    assert "#" in sender.call_args.args[0]


def test_crashed_claim_recovers_after_persistent_lease(alarm_clock, monkeypatch):
    queued_event()
    event_id = service.list_events("admin")[0]["id"]
    assert repository.claim_delivery(event_id) is not None
    # Simulate exit before send/ack; a new worker cannot retry until the stored lease ends.
    sender = AsyncMock()
    monkeypatch.setattr(service, "send_telegram_message", sender)
    asyncio.run(service.deliver_pending_notifications())
    sender.assert_not_called()
    alarm_clock["now"] += timedelta(minutes=3)
    asyncio.run(service.deliver_pending_notifications())
    sender.assert_awaited_once()
    assert service.list_events("admin")[0]["delivery_status"] == "sent"


def test_shutdown_during_send_finishes_ack_and_leaves_rest_queued(alarm_clock, monkeypatch):
    queued_event()
    queued_event()
    stopped = False

    async def send_and_stop(message):
        nonlocal stopped
        stopped = True

    sender = AsyncMock(side_effect=send_and_stop)
    monkeypatch.setattr(service, "send_telegram_message", sender)
    asyncio.run(service.deliver_pending_notifications(should_stop=lambda: stopped))
    sender.assert_awaited_once()
    assert [event["delivery_status"] for event in service.list_events("admin")] == [
        "pending",
        "sent",
    ]


def test_edit_cancels_pending_outbox(alarm_clock, monkeypatch):
    rule = queued_event()
    service.save_rule("admin", payload(enabled=False), rule_id=rule["id"])
    sender = AsyncMock()
    monkeypatch.setattr(service, "send_telegram_message", sender)
    asyncio.run(service.deliver_pending_notifications())
    sender.assert_not_called()
    assert service.list_events("admin")[0]["delivery_status"] == "failed"


def test_retention_preserves_pending_and_bounds_own_terminal_history(alarm_clock, monkeypatch):
    rule = service.save_rule("admin", payload(mode="once_per_bar"))
    for hour in range(10, 15):
        repository.record_evaluation(rule, rule["symbols"][0], evaluation(hour))
    queued_event()
    monkeypatch.setattr(repository, "MAX_TERMINAL_EVENTS", 2)
    repository.prune_history()
    assert [event["delivery_status"] for event in service.list_events("admin")] == [
        "pending",
        "not_requested",
        "not_requested",
    ]
    alarm_clock["now"] += timedelta(days=31)
    repository.prune_history()
    assert [event["delivery_status"] for event in service.list_events("admin")] == ["pending"]


def test_full_outbox_records_failed_event_without_losing_pending(alarm_clock, monkeypatch):
    monkeypatch.setattr(repository, "MAX_PENDING_DELIVERIES", 1)
    queued_event()
    queued_event()
    assert [event["delivery_status"] for event in service.list_events("admin")] == [
        "failed",
        "pending",
    ]
    assert "kuyruğu dolu" in service.list_events("admin")[0]["delivery_error"]


def test_telegram_sender_plain_payload_bounded_timeout_no_secret_logs(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    calls = []
    monkeypatch.setattr(service.settings, "telegram_token", "SECRET-BOT-TOKEN")
    monkeypatch.setattr(service.settings, "telegram_chat_id", "SECRET-CHAT-ID")

    class FakeResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def json(self):
            return {"ok": True}

    class FakeSession(FakeResponse):
        def __init__(self, **kwargs):
            assert kwargs["timeout"].total == 15
            assert kwargs["trust_env"] is False

        def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return FakeResponse()

    monkeypatch.setattr(service.aiohttp, "ClientSession", FakeSession)
    asyncio.run(service.send_telegram_message("<b>Literal user name</b>"))
    assert calls[0][1] == {
        "json": {"chat_id": "SECRET-CHAT-ID", "text": "<b>Literal user name</b>"},
        "allow_redirects": False,
    }
    assert "SECRET" not in caplog.text
