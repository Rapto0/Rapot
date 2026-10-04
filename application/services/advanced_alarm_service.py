"""One-second bounded evaluation of cached observations; delivery has its own worker."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import time
from collections import OrderedDict
from collections.abc import Callable
from datetime import UTC, datetime

import aiohttp

from application.services.server_alarm_service import telegram_configured
from infrastructure.repositories import advanced_alarm_repository as repository
from settings import settings

MAX_EVALUATIONS_PER_TICK = settings.advanced_alarm_eval_batch
MAX_CHANGES_PER_TICK = 250
EVALUATION_SECONDS = settings.advanced_alarm_eval_budget_seconds
STATE_CACHE_LIMIT = settings.advanced_alarm_state_cache
_delivery_retry_until = 0.0


def _now():
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _identity(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


class AdvancedAlarmEngine:
    def __init__(self, hub=None, *, clock=None, wall_clock=None):
        self._hub = hub
        self._clock = clock or time.monotonic
        self._wall_clock = wall_clock or (lambda: datetime.now(UTC))
        self._rules = []
        self._rules_at = -math.inf
        self._generation = -1
        self._cursor = (0, 0)
        self._states: OrderedDict = OrderedDict()
        self._rule_health = {}
        self._runtime = {
            "running": False,
            "last_cycle_at": None,
            "last_error": None,
            "evaluation": {
                "total": 0,
                "checked": 0,
                "ready": 0,
                "backlog": 0,
                "cursor": [0, 0],
                "cycle_ms": 0,
            },
        }

    @property
    def hub(self):
        if self._hub is None:
            from application.services.advanced_alarm_market_data import get_advanced_market_data

            self._hub = get_advanced_market_data()
        return self._hub

    def set_running(self, value):
        self._runtime["running"] = bool(value)

    def status(self, owner):
        # No provider I/O. Detailed account-wide coverage contains no other owner's rules.
        return {
            **self._runtime,
            "market": self.hub.status(),
            "limits": repository.LIMITS,
            "usage": repository.usage(owner),
            "delivery": repository.delivery_status(owner),
            "telegram_configured": telegram_configured(),
            "storage": repository.storage_status(),
        }

    def rules(self, owner):
        rows = repository.list_rules(owner)
        for row in rows:
            health = self._rule_health.get((row["id"], row["revision"]))
            if row["enabled"] and health:
                row.update(health)
        return rows

    def _refresh(self):
        if self._generation == repository.generation() and self._clock() - self._rules_at < 5:
            return
        rules = repository.active_rules()
        identity = [(r["id"], r["revision"]) for r in rules]
        changed = self._generation == -1 or identity != [
            (r["id"], r["revision"]) for r in self._rules
        ]
        if changed:
            self._cursor = (0, 0)
            valid = set(identity)
            self._states = OrderedDict((k, v) for k, v in self._states.items() if k[:2] in valid)
            self._rule_health = {k: v for k, v in self._rule_health.items() if k in valid}
        self._rules = rules
        if changed:
            self.hub.configure(rules)
        self._rules_at, self._generation = self._clock(), repository.generation()

    def _jobs(self):
        """Store only membership lists, not the potentially six-million-rule cross product."""
        counts = [self.hub.symbol_count(rule["id"]) for rule in self._rules]
        total = sum(counts)
        if not total:
            return [], 0
        ri, si = self._cursor
        ri %= len(self._rules)
        jobs = []
        visited = 0
        while visited < total and len(jobs) < MAX_EVALUATIONS_PER_TICK:
            symbols = self.hub.symbols(self._rules[ri]["id"])
            if si >= len(symbols):
                ri, si = (ri + 1) % len(self._rules), 0
                continue
            rule, symbol = self._rules[ri], symbols[si]
            si += 1
            visited += 1
            jobs.append((rule, symbol, (ri, si)))
        return jobs, total

    @staticmethod
    def _evaluate(rule, snapshot, previous, now):
        """Baseline after creation/gaps; no invented crossing across a discontinuity."""
        ready = snapshot.get("ready") is True
        if not isinstance(snapshot.get("matched"), bool):
            ready = False
        observation = snapshot.get("observation_id")
        continuity = snapshot.get("continuity_id")
        if ready and (not observation or not continuity):
            ready = False
        obs = _identity(observation) if observation else None
        epoch = _identity(continuity) if continuity else None
        state = dict(previous or {})
        if not ready:
            state.update(ready=False, matched=None, observation_id=obs, continuity_id=epoch)
            return state, None
        matched = snapshot.get("matched") is True
        bar = snapshot.get("bar_time")
        valid_previous = bool(
            previous and previous.get("ready") and previous.get("continuity_id") == epoch
        )
        if valid_previous and previous.get("observation_id") == obs:
            return state, None
        state.update(ready=True, matched=matched, observation_id=obs, continuity_id=epoch)
        emit = False
        if valid_previous and matched:
            if rule["mode"] == "on_enter":
                emit = previous.get("matched") is False
            elif rule["mode"] == "once_per_bar":
                emit = bool(bar and bar != previous.get("last_bar"))
            else:
                last = previous.get("last_triggered_at")
                emit = (
                    last is None
                    or (now - datetime.fromisoformat(last.replace("Z", "+00:00"))).total_seconds()
                    >= rule["cooldown_seconds"]
                )
        # First ready observation is a baseline even if a prior historical condition is true.
        if not valid_previous and bar and matched:
            state["last_bar"] = bar
        if emit and previous.get("last_triggered_at"):
            since = now - datetime.fromisoformat(
                previous["last_triggered_at"].replace("Z", "+00:00")
            )
            emit = since.total_seconds() >= rule["cooldown_seconds"]
        if not emit:
            return state, None
        state["last_bar"] = bar
        state["last_triggered_at"] = now.isoformat().replace("+00:00", "Z")
        value = snapshot.get("value")
        values = snapshot.get("values") or {}
        values = (
            {str(k)[:120]: float(v) for k, v in values.items() if _finite(v)}
            if isinstance(values, dict)
            else {}
        )
        event = {
            "observation_id": _identity("bar:" + bar) if rule["mode"] == "once_per_bar" else obs,
            "value": float(value) if _finite(value) else None,
            "values": dict(list(values.items())[:64]),
            "bar_time": bar,
            "observed_at": snapshot.get("observed_at"),
        }
        return state, event

    def tick(self):
        started = self._clock()
        original_cursor = self._cursor
        self._runtime["last_error"] = None
        self._runtime["backpressure"] = None
        try:
            self._refresh()
            jobs, total = self._jobs()
            keys = [(r["id"], r["revision"], s["symbol"], s["market_type"]) for r, s, _ in jobs]
            missing = [key for key in keys if key not in self._states]
            restored = repository.load_states(missing)
            for key in missing:
                self._states[key] = restored.get(key)
            changes, ephemeral = [], []
            health = {}
            checked = ready_count = 0
            now = self._wall_clock()
            for (rule, symbol, cursor), key in zip(jobs, keys, strict=True):
                if checked and (
                    self._clock() - started >= EVALUATION_SECONDS
                    or len(changes) >= MAX_CHANGES_PER_TICK
                ):
                    break
                previous = self._states.get(key)
                snapshot = self.hub.snapshot(rule, symbol, now=now)
                state, event = self._evaluate(rule, snapshot, previous, now)
                checked += 1
                ready_count += int(state.get("ready", False))
                rule_key = (rule["id"], rule["revision"])
                result = health.setdefault(
                    rule_key,
                    {
                        "checked_this_tick": 0,
                        "ready_this_tick": 0,
                        "total_symbols": self.hub.symbol_count(rule["id"]),
                        "last_checked_at": now.isoformat().replace("+00:00", "Z"),
                        "last_error": None,
                    },
                )
                result["checked_this_tick"] += 1
                result["ready_this_tick"] += int(state.get("ready", False))
                if not state.get("ready"):
                    reason = snapshot.get("reason")
                    result["last_error"] = (
                        reason[:240] if isinstance(reason, str) else "Veri hazır değil."
                    )
                # Quote receipt/observation churn does not generate writes each second.
                meaningful = (
                    event
                    or (previous is None and state.get("ready"))
                    or (
                        previous is not None
                        and any(
                            state.get(k) != previous.get(k)
                            for k in (
                                "ready",
                                "matched",
                                "continuity_id",
                                "last_bar",
                                "last_triggered_at",
                            )
                        )
                    )
                )
                if meaningful:
                    changes.append({"key": key, "state": state, "event": event})
                ephemeral.append((key, state))
                self._cursor = cursor
            accepted = repository.apply_batch(changes)
            for key, result in health.items():
                result["state"] = (
                    "error"
                    if result["last_error"]
                    else "active"
                    if result["ready_this_tick"] == result["total_symbols"]
                    else "partial"
                )
                self._rule_health[key] = result
            changed = {item["key"] for item in changes}
            for key, state in ephemeral:
                if key not in changed or key in accepted:
                    self._states[key] = state
                    self._states.move_to_end(key)
            while len(self._states) > STATE_CACHE_LIMIT:
                self._states.popitem(last=False)
            self._runtime["evaluation"] = {
                "total": total,
                "checked": checked,
                "ready": ready_count,
                "backlog": max(0, total - checked),
                "cursor": list(self._cursor),
                "cycle_ms": round((self._clock() - started) * 1000, 2),
                "state_changes": len(changes),
                "complete_pass_this_tick": total <= checked,
                "budget_seconds": EVALUATION_SECONDS,
                "max_comparisons": MAX_EVALUATIONS_PER_TICK,
                "state_cache_limit": STATE_CACHE_LIMIT,
            }
        except repository.CapacityPressure:
            self._cursor = original_cursor
            self._runtime["last_error"] = (
                "Disk rezervi korunuyor; değerlendirme kaydı ve teslim bekletiliyor."
            )
            self._runtime["backpressure"] = "disk_reserve"
        except Exception:
            self._cursor = original_cursor
            self._runtime["last_error"] = (
                "Değerlendirme tamamlanamadı; kaydedilen sıra sonraki turda yeniden denenecek."
            )
        finally:
            self._runtime["last_cycle_at"] = _now()


class TelegramFailure(Exception):
    def __init__(self, retry_after=None):
        self.retry_after = retry_after
        super().__init__("Telegram teslimi doğrulanamadı.")


async def send_telegram(event):
    """No client request logger, redirects or provider error bodies enter logs/storage."""
    message = (
        f"Rapot alarmı #{event['id']}\n{event['rule_name']}\n"
        f"{event['symbol']} ({event['market_type']}) · {event['category']}\n"
        f"Değer: {event['value']}\nGözlem (UTC): {event['observed_at']}"
    )
    try:
        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15), trust_env=False
            ) as client,
            client.post(
                f"https://api.telegram.org/bot{settings.telegram_token}/sendMessage",
                json={"chat_id": settings.telegram_chat_id, "text": message},
                allow_redirects=False,
            ) as response,
        ):
            raw = await response.content.read(65537)
            if len(raw) > 65536:
                raise TelegramFailure()
            try:
                result = json.loads(raw)
            except (ValueError, UnicodeError):
                raise TelegramFailure() from None
            if response.status == 429:
                delay = result.get("parameters", {}).get("retry_after")
                if not _finite(delay):
                    delay = None
                raise TelegramFailure(min(86400, max(1, delay)) if delay is not None else 60)
            if response.status != 200 or result.get("ok") is not True:
                raise TelegramFailure()
    except TelegramFailure:
        raise
    except Exception:
        raise TelegramFailure() from None


async def deliver_one(sender: Callable | None = None):
    global _delivery_retry_until
    if not telegram_configured() or time.monotonic() < _delivery_retry_until:
        return False
    event = await asyncio.to_thread(repository.claim_delivery)
    if event is None:
        return False
    try:
        await (sender or send_telegram)(event)
    except TelegramFailure as error:
        if error.retry_after is not None:
            _delivery_retry_until = time.monotonic() + error.retry_after
        await asyncio.to_thread(
            repository.finish_delivery, event["id"], retry_after=error.retry_after
        )
    except Exception:
        await asyncio.to_thread(repository.finish_delivery, event["id"])
    else:
        await asyncio.to_thread(repository.finish_delivery, event["id"], sent=True)
    return True


_engine = None


def get_advanced_alarm_engine():
    global _engine
    if _engine is None:
        _engine = AdvancedAlarmEngine()
    return _engine
