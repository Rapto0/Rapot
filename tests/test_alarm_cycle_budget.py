"""Bounded cyclic progress survives slow providers, restart and rule removal."""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from application.services import server_alarm_evaluator as evaluator
from application.services import server_alarm_service as service
from infrastructure.repositories import server_alarm_repository as repository


def rule_payload(symbols, **changes):
    return {
        "name": "Sunucu bütçe testi",
        "symbols": [{"symbol": name, "market_type": "Kripto"} for name in symbols],
        "indicator": "rsi",
        "timeframe": "1h",
        "side": "dip",
        "threshold": 30,
        "mode": "on_enter",
        "enabled": True,
        "notify_telegram": False,
        **changes,
    }


def result():
    # Service persistence fixture: evaluator's closed-candle validation is tested separately.
    bar = datetime.now(UTC) + timedelta(hours=1)
    return {
        "bar_time": bar.isoformat(),
        "bar_closed_at": (bar + timedelta(hours=1)).isoformat(),
        "value": 25.0,
        "matched": True,
        "previous_matched": False,
    }


def queued_event():
    rule = repository.save_rule("admin", rule_payload(["BTCUSDT"], notify_telegram=True))
    repository.record_evaluation(rule, rule["symbols"][0], result())
    return rule


def test_hundred_slow_subscriptions_resume_fairly_after_restart_and_deleted_cursor(monkeypatch):
    for group in range(5):
        repository.save_rule(
            "admin", rule_payload([f"COIN{group * 20 + number}USDT" for number in range(20)])
        )
    virtual = {"seconds": 0.0}
    monkeypatch.setattr(service, "time", SimpleNamespace(monotonic=lambda: virtual["seconds"]))
    calls = []

    async def slow(**kwargs):
        calls.append(kwargs["symbol"])
        virtual["seconds"] += 22.5
        raise evaluator.AlarmEvaluationError("Veri sağlayıcı yanıtlamadı.")

    monkeypatch.setattr(evaluator, "evaluate_alarm_symbol", slow)
    asyncio.run(service.run_alarm_cycle())
    assert len(calls) == 2
    first_cursor = repository.evaluation_cursor()
    checked = [rule for rule in repository.list_rules("admin") if rule["last_checked_at"]]
    assert len(checked) == 1
    assert "2/20" in checked[0]["last_error"]
    assert checked[0]["state"] == "error"
    # A new asyncio loop and discarded process status still resume from SQLite.
    monkeypatch.setattr(service, "_runtime", {"running": False})
    asyncio.run(service.run_alarm_cycle())
    assert len(calls) == 4 and len(set(calls)) == 4
    assert repository.evaluation_cursor() != first_cursor
    removed = repository.evaluation_cursor()[0]
    repository.delete_rule("admin", removed)
    asyncio.run(service.run_alarm_cycle())
    assert len(calls) == 6 and len(set(calls)) == 6
    assert repository.evaluation_cursor()[0] != removed


def test_pending_delivery_precedes_slow_evaluation_and_newest_unchecked_rule_is_not_active(
    monkeypatch,
):
    queued_event()
    virtual = {"seconds": 0.0}
    monkeypatch.setattr(service, "time", SimpleNamespace(monotonic=lambda: virtual["seconds"]))
    actions = []

    async def send(message):
        actions.append("send")

    async def fail(**kwargs):
        actions.append("evaluate")
        virtual["seconds"] += 45
        raise evaluator.AlarmEvaluationError("Sağlayıcı zaman aşımı.")

    monkeypatch.setattr(service, "send_telegram_message", send)
    monkeypatch.setattr(evaluator, "evaluate_alarm_symbol", fail)
    asyncio.run(service.run_alarm_cycle())
    assert actions == ["send", "evaluate"]
    assert repository.list_events("admin")[0]["delivery_status"] == "sent"


def test_hard_cycle_deadline_cancels_await_and_persists_cursor(monkeypatch):
    rule = repository.save_rule("admin", rule_payload(["BTCUSDT", "ETHUSDT"]))
    cancelled = []

    async def hanging(**kwargs):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(kwargs["symbol"])

    monkeypatch.setattr(service, "EVALUATION_BUDGET_SECONDS", 0.02)
    monkeypatch.setattr(evaluator, "evaluate_alarm_symbol", hanging)
    asyncio.run(service.run_alarm_cycle())
    assert cancelled == ["BTCUSDT"]
    assert repository.evaluation_cursor() == (rule["id"], "BTCUSDT", "Kripto")
    saved = repository.list_rules("admin")[0]
    assert "1/2" in saved["last_error"] and "kontrol süresi doldu" in saved["last_error"]
    assert repository.list_events("admin") == []


def test_delivery_deadline_leaves_remaining_events_pending(monkeypatch):
    queued_event()
    queued_event()
    calls = []

    async def hanging(message):
        calls.append(message)
        await asyncio.Event().wait()

    monkeypatch.setattr(service, "send_telegram_message", hanging)
    asyncio.run(service.deliver_pending_notifications(time_budget_seconds=0.02))
    assert len(calls) == 1
    events = repository.list_events("admin")
    assert all(event["delivery_status"] == "pending" for event in events)
    assert events[0]["delivery_error"] is None
    assert "başarısız" in events[1]["delivery_error"]


def test_stop_before_cycle_has_no_fetch_send_or_persistence(monkeypatch):
    repository.save_rule("admin", rule_payload(["BTCUSDT"]))
    fake = AsyncMock()
    sender = AsyncMock()
    monkeypatch.setattr(evaluator, "evaluate_alarm_symbol", fake)
    monkeypatch.setattr(service, "send_telegram_message", sender)
    monkeypatch.setattr(repository, "prune_history", lambda: pytest.fail("Stopped cycle wrote DB"))
    asyncio.run(service.run_alarm_cycle(should_stop=lambda: True))
    fake.assert_not_called()
    sender.assert_not_called()
    assert repository.evaluation_cursor() is None
    assert repository.list_rules("admin")[0]["last_checked_at"] is None


def test_completed_fast_rules_clear_partial_status_and_wrap_cursor(monkeypatch):
    rule = repository.save_rule("admin", rule_payload(["BTCUSDT", "ETHUSDT"]))
    repository.record_cycle_result(rule, ["Önceki turda 1/2 sembol kontrol edildi."])
    fake = AsyncMock(return_value={**result(), "matched": False})
    monkeypatch.setattr(evaluator, "evaluate_alarm_symbol", fake)
    asyncio.run(service.run_alarm_cycle())
    assert repository.list_rules("admin")[0]["state"] == "active"
    assert repository.evaluation_cursor() == (rule["id"], "ETHUSDT", "Kripto")
    asyncio.run(service.run_alarm_cycle())
    assert [item.kwargs["symbol"] for item in fake.await_args_list] == ["BTCUSDT", "ETHUSDT"] * 2


def test_two_delivery_phases_share_one_cycle_attempt_limit(monkeypatch):
    queued_event()
    queued_event()
    monkeypatch.setattr(repository, "MAX_DELIVERIES_PER_CYCLE", 1)
    sender = AsyncMock()
    monkeypatch.setattr(service, "send_telegram_message", sender)
    monkeypatch.setattr(
        evaluator, "evaluate_alarm_symbol", AsyncMock(return_value={**result(), "matched": False})
    )
    asyncio.run(service.run_alarm_cycle())
    sender.assert_awaited_once()
    assert sorted(event["delivery_status"] for event in repository.list_events("admin")) == [
        "pending",
        "sent",
    ]
