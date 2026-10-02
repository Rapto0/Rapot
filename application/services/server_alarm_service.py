"""Persistent rule management, closed-candle evaluation and Telegram outbox.

The API runtime owns the cross-process worker lock. No database transaction is
held while waiting for a market provider or Telegram. Delivery is at least once:
a process crash after Telegram accepts a message can cause a retry of that message.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import aiohttp

from infrastructure.repositories import server_alarm_repository as repository
from infrastructure.time import utc_now_naive
from settings import settings

POLL_INTERVAL_SECONDS = 60
EVALUATION_BUDGET_SECONDS = 45
DELIVERY_BUDGET_SECONDS = 30
_runtime: dict[str, Any] = {"running": False, "last_cycle_at": None, "last_cycle_error": None}
LIMITS = repository.LIMITS
AlarmNotFoundError = repository.AlarmNotFoundError
AlarmLimitError = repository.AlarmLimitError
list_rules = repository.list_rules
save_rule = repository.save_rule
delete_rule = repository.delete_rule
list_events = repository.list_events


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


def telegram_configured() -> bool:
    return bool(
        str(settings.telegram_token or "").strip() and str(settings.telegram_chat_id or "").strip()
    )


def set_runtime_running(running: bool) -> None:
    _runtime["running"] = running


def runtime_status() -> dict[str, Any]:
    return {
        **_runtime,
        "telegram_configured": telegram_configured(),
        "poll_interval_seconds": POLL_INTERVAL_SECONDS,
        "evaluation_budget_seconds": EVALUATION_BUDGET_SECONDS,
        "delivery_budget_seconds": DELIVERY_BUDGET_SECONDS,
    }


async def send_telegram_message(message: str) -> None:
    """Use only the configured destination; no formatting or user-controlled URL."""
    async with (
        aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15), trust_env=False) as client,
        client.post(
            f"https://api.telegram.org/bot{settings.telegram_token}/sendMessage",
            json={"chat_id": settings.telegram_chat_id, "text": message},
            allow_redirects=False,
        ) as response,
    ):
        if response.status != 200 or (await response.json()).get("ok") is not True:
            # No per-request URL logging: the bot token is part of Telegram's URL.
            raise RuntimeError("Telegram gönderimi başarısız.")


async def deliver_pending_notifications(
    *,
    should_stop: Callable[[], bool] | None = None,
    time_budget_seconds: float = DELIVERY_BUDGET_SECONDS,
    max_deliveries: int = repository.MAX_DELIVERIES_PER_CYCLE,
) -> int:
    stop = should_stop or (lambda: False)
    if stop() or time_budget_seconds <= 0 or max_deliveries <= 0 or not telegram_configured():
        return 0
    deadline = time.monotonic() + time_budget_seconds
    event_ids = repository.pending_delivery_ids()[:max_deliveries]
    attempts = 0
    for position, event_id in enumerate(event_ids):
        if stop() or time.monotonic() >= deadline:
            return attempts
        if position:
            # All messages target the shared configured chat; avoid burst delivery.
            await asyncio.sleep(min(1.1, max(0, deadline - time.monotonic())))
        if stop() or time.monotonic() >= deadline:
            return attempts
        event = repository.claim_delivery(event_id)
        if event is None:
            continue
        attempts += 1
        if stop():
            return attempts
        message = (
            f"Rapot sunucu alarmı #{event['id']}\n{event['rule_name']}\n"
            f"{event['symbol']} ({event['market_type']}) · {event['timeframe']}\n"
            f"{event['indicator'].upper()} · {'Dip' if event['side'] == 'dip' else 'Tepe'} "
            f"· Değer: {event['value']:.4g}\nMum zamanı (UTC): {event['bar_time']}"
        )
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return attempts
            await asyncio.wait_for(send_telegram_message(message), timeout=remaining)
        except Exception:
            repository.finish_delivery(event_id, sent=False)
        else:
            repository.finish_delivery(event_id, sent=True)
    return attempts


async def run_alarm_cycle(*, should_stop: Callable[[], bool] | None = None) -> None:
    """Evaluate a bounded rule snapshot, then drain a bounded part of the outbox."""
    from application.services.server_alarm_evaluator import (
        AlarmEvaluationError,
        evaluate_alarm_symbol,
    )

    stop = should_stop or (lambda: False)
    if stop():
        return
    _runtime["last_cycle_error"] = None
    try:
        repository.prune_history()
        # A slow market-data provider cannot hold already queued messages hostage.
        delivery_started = time.monotonic()
        delivered_attempts = await deliver_pending_notifications(
            should_stop=stop,
            time_budget_seconds=DELIVERY_BUDGET_SECONDS,
            max_deliveries=repository.MAX_DELIVERIES_PER_CYCLE,
        )
        delivery_spent = time.monotonic() - delivery_started
        if stop():
            return
        snapshots = repository.active_snapshots()
        subscriptions = sorted(
            ((snapshot["id"], symbol["symbol"], symbol["market_type"]), snapshot, symbol)
            for snapshot in snapshots
            for symbol in snapshot["symbols"]
        )
        cursor = repository.evaluation_cursor()
        if cursor is not None:
            # Lexicographic successor also works when the saved rule/symbol was deleted.
            start = next((i for i, (key, _, _) in enumerate(subscriptions) if key > cursor), 0)
            subscriptions = subscriptions[start:] + subscriptions[:start]
        deadline = time.monotonic() + EVALUATION_BUDGET_SECONDS
        checked: dict[str, int] = {}
        errors: dict[str, list[str]] = {}
        for key, snapshot, symbol in subscriptions:
            if stop():
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            rule_errors = errors.setdefault(snapshot["id"], [])
            budget_expired = False
            try:
                result = await asyncio.wait_for(
                    evaluate_alarm_symbol(
                        **symbol,
                        timeframe=snapshot["timeframe"],
                        indicator=snapshot["indicator"],
                        side=snapshot["side"],
                        threshold=snapshot["threshold"],
                    ),
                    timeout=remaining,
                )
                if stop():
                    return
                repository.record_evaluation(snapshot, symbol, result)
            except AlarmEvaluationError as exc:
                rule_errors.append(f"{symbol['symbol']}: {exc}")
            except TimeoutError:
                budget_expired = True
                rule_errors.append(f"{symbol['symbol']}: bu turun kontrol süresi doldu.")
            except Exception:
                # Provider errors may embed request URLs and credentials. Do not save them.
                rule_errors.append(
                    f"{symbol['symbol']}: kapalı mum verisi veya hesaplama kullanılamıyor."
                )
            if stop():
                return
            checked[snapshot["id"]] = checked.get(snapshot["id"], 0) + 1
            repository.advance_evaluation_cursor(key)
            if budget_expired:
                break
        for snapshot in snapshots:
            if stop():
                return
            count = checked.get(snapshot["id"], 0)
            if count:
                rule_errors = errors[snapshot["id"]]
                total = len(snapshot["symbols"])
                if count < total:
                    rule_errors.insert(
                        0,
                        f"Bu turda {count}/{total} sembol kontrol edildi; kalanlar sonraki turlarda.",
                    )
                repository.record_cycle_result(snapshot, rule_errors)
        await deliver_pending_notifications(
            should_stop=stop,
            time_budget_seconds=max(0, DELIVERY_BUDGET_SECONDS - delivery_spent),
            max_deliveries=repository.MAX_DELIVERIES_PER_CYCLE - delivered_attempts,
        )
        if not stop():
            repository.prune_history()
    except Exception:
        _runtime["last_cycle_error"] = "Alarm döngüsü tamamlanamadı; sonraki döngüde denenecek."
    finally:
        _runtime["last_cycle_at"] = _iso(utc_now_naive())
