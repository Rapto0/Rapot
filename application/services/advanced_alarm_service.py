"""One-second bounded evaluation of cached observations; delivery has its own worker."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import time
import uuid
from collections import OrderedDict
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime
from itertools import islice
from pathlib import Path
from threading import RLock

import aiohttp

from application.services.alarm_acceptance_lease import PREFIX, AcceptanceLeaseGate
from application.services.server_alarm_service import telegram_configured
from infrastructure.repositories import advanced_alarm_repository as repository
from settings import settings

MAX_EVALUATIONS_PER_TICK = settings.advanced_alarm_eval_batch
MAX_CHANGES_PER_TICK = 250
EVALUATION_SECONDS = settings.advanced_alarm_eval_budget_seconds
STATE_CACHE_LIMIT = settings.advanced_alarm_state_cache
STATE_LOAD_BATCH = 128
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
        self._evaluation_lock = RLock()
        self._live_index_signature = None
        self._live_index = {}
        self._live_custom_ids = set()
        self._live_plan_keys = {}
        self._live_bound = False
        self._custom_cursor = (0, 0)
        self._custom_remaining = 0
        self._custom_maintenance_at = -math.inf
        self._pending_live_states: OrderedDict = OrderedDict()
        self._last_live_flush = -math.inf
        self._delivery_listener = None
        self._clock = clock or time.monotonic
        self._wall_clock = wall_clock or (lambda: datetime.now(UTC))
        self._rules = []
        self._source_rules = []
        self._rules_at = -math.inf
        self._generation = -1
        self._cursor = (0, 0)
        self._states: OrderedDict = OrderedDict()
        self._rule_health = {}
        self._lease_gate = AcceptanceLeaseGate(
            Path(settings.database_path).resolve().parent / "alarm-acceptance-leases"
        )
        self._diagnostic_rules: OrderedDict = OrderedDict()
        self._diagnostic_epoch = uuid.uuid4().hex
        self._diagnostic_totals = {"cycles": 0, "failed_cycles": 0, "checked": 0, "ready": 0}
        self._owner_diagnostics = {}
        self._published_totals = dict(self._diagnostic_totals)
        self._diagnostics_at = None
        self._runtime = {
            "running": False,
            "last_cycle_at": None,
            "last_error": None,
            "live_evaluation": {
                "updates": 0,
                "checked": 0,
                "last_update_at": None,
                "last_duration_ms": None,
                "last_error": None,
                "indexed_symbols": 0,
                "membership_groups": 0,
            },
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

    def bind_live_updates(self):
        """The data worker blocks here until this observation has been consumed."""
        listener = getattr(self.hub, "set_update_listener", None)
        if listener:
            listener(self.market_updated)
            self._live_bound = True

    def set_delivery_listener(self, callback):
        self._delivery_listener = callback

    def _wake_delivery(self):
        callback = self._delivery_listener
        if callback:
            # Shutdown may close the asyncio loop after the durable commit.
            # The outbox remains pending for the next delivery worker.
            with suppress(RuntimeError):
                callback()

    @staticmethod
    def _has_custom(condition):
        if condition["op"] in {"and", "or"}:
            return any(AdvancedAlarmEngine._has_custom(row) for row in condition["children"])
        return any(
            isinstance(condition.get(side), dict) and condition[side].get("field") == "custom"
            for side in ("left", "right")
        )

    def _index_live_rules(self):
        # A symbol's rule membership is one Python integer bitmap, not thousands
        # of (rule, symbol) objects. Shared watchlists are expanded only once.
        memberships = [self.hub.symbols(rule["id"]) for rule in self._rules]
        shared_live = getattr(self.hub, "uses_live_updates", lambda rule: False)
        live_rules = [
            self._has_custom(rule["condition"]) or shared_live(rule) for rule in self._rules
        ]
        signature = tuple(
            (rule["id"], rule["revision"], id(members), live)
            for rule, members, live in zip(self._rules, memberships, live_rules, strict=True)
        )
        if signature == self._live_index_signature:
            return
        groups, custom_ids, plan_keys, interned = {}, set(), {}, {}
        for position, (rule, members) in enumerate(zip(self._rules, memberships, strict=True)):
            if not live_rules[position]:
                continue
            custom_ids.add(rule["id"])
            signature_key = (
                rule.get("timeframe"),
                rule.get("trigger"),
                rule.get("mode"),
                json.dumps(rule["condition"], sort_keys=True),
            )
            plan_keys[rule["id"]] = interned.setdefault(signature_key, len(interned))
            group = groups.setdefault(id(members), [members, 0])
            group[1] |= 1 << position
        index = {}
        for members, mask in groups.values():
            for member in members:
                key = member["market_type"], member["symbol"]
                index[key] = index.get(key, 0) | mask
        self._live_index, self._live_index_signature = index, signature
        self._live_custom_ids = custom_ids
        self._live_plan_keys = plan_keys
        self._custom_cursor, self._custom_remaining = (0, 0), 0
        self._custom_maintenance_at = -math.inf
        self._runtime["live_evaluation"].update(
            indexed_symbols=len(index), membership_groups=len(groups), maintenance_seconds=5
        )

    def _flush_live_states(self, *, force=False):
        if not self._pending_live_states:
            return
        if not force and self._clock() - self._last_live_flush < 0.1:
            return
        while self._pending_live_states:
            batch = list(islice(self._pending_live_states.values(), MAX_CHANGES_PER_TICK))
            repository.apply_batch(batch)
            for change in batch:
                self._pending_live_states.pop(change["key"], None)
        self._last_live_flush = self._clock()

    def market_updated(self, market, symbol):
        """Consume every published symbol snapshot before the next one replaces it.

        Called synchronously, outside provider/data locks. Incoming events have a
        separate bounded queue with explicit continuity reset on loss. Events are
        committed immediately; non-event state transitions share bounded batches.
        """
        with self._evaluation_lock:
            mask = self._live_index.get((market, symbol), 0)
            if not mask or self._generation != repository.generation():
                return
            started = self._clock()
            status = self._runtime["live_evaluation"]
            checked = 0
            keys = []
            now = self._wall_clock()
            try:
                rules = []
                snapshots = {}
                while mask:
                    bit = mask & -mask
                    rules.append(self._rules[bit.bit_length() - 1])
                    mask ^= bit
                # Diagnostic TEST leases can expire between maintenance passes;
                # ordinary user rules do not depend on a lease.
                rules = self._lease_gate.filter_rules(rules)
                member = {"market_type": market, "symbol": symbol}
                for offset in range(0, len(rules), STATE_LOAD_BATCH):
                    chunk = rules[offset : offset + STATE_LOAD_BATCH]
                    keys = [(r["id"], r["revision"], symbol, market) for r in chunk]
                    missing = [key for key in keys if key not in self._states]
                    if missing:
                        restored = repository.load_states(missing)
                        for key in missing:
                            self._states[key] = restored.get(key)
                    events = []
                    for rule, key in zip(chunk, keys, strict=True):
                        previous = self._states.get(key)
                        plan_key = self._live_plan_keys[rule["id"]]
                        if plan_key not in snapshots:
                            snapshots[plan_key] = self.hub.snapshot(rule, member, now=now)
                        observation = snapshots[plan_key]
                        state, event = self._evaluate(rule, observation, previous, now)
                        checked += 1
                        self._observe_rule(rule, observation, state.get("ready"), now.isoformat())
                        self._diagnostic_totals["checked"] += 1
                        self._diagnostic_totals["ready"] += int(bool(state.get("ready")))
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
                            change = {"key": key, "state": state, "event": event}
                            if event:
                                events.append(change)
                                self._pending_live_states.pop(key, None)
                            else:
                                self._pending_live_states[key] = change
                        self._states[key] = state
                        self._states.move_to_end(key)
                    if events:
                        accepted = repository.apply_batch(events)
                        if any(change["key"] in accepted for change in events):
                            self._wake_delivery()
                    self._flush_live_states(
                        force=len(self._pending_live_states) >= MAX_CHANGES_PER_TICK
                    )
                while len(self._states) > STATE_CACHE_LIMIT:
                    self._states.popitem(last=False)
                status["last_error"] = None
            except Exception:
                # Never invent a crossing after an uncommitted event or a write
                # failure. The caller also resets source continuity before retry.
                for key in list(self._states):
                    if key[2:] == (symbol, market):
                        self._states[key] = None
                        self._pending_live_states.pop(key, None)
                status["last_error"] = (
                    "Canlı alarm değerlendirmesi kesildi; devamlılık yeniden hazırlanıyor."
                )
                raise
            finally:
                status["updates"] += 1
                status["checked"] += checked
                status["last_update_at"] = now.isoformat()
                status["last_duration_ms"] = round((self._clock() - started) * 1000, 3)

    def heartbeat(self, owner, *, test_run_id=None):
        """Constant-size, provider/DB-free counters; global cycles are labelled explicitly."""
        selected = PREFIX + test_run_id if test_run_id is not None else owner
        return {
            "schema": "rapot-advanced-heartbeat-v1",
            "observed_at": _now(),
            "process_epoch": self._diagnostic_epoch,
            "running": self._runtime["running"],
            "last_cycle_at": self._runtime["last_cycle_at"],
            "last_cycle_failed": self._runtime["last_error"] is not None,
            "evaluation_scope": "global_engine",
            "evaluation": dict(self._runtime["evaluation"]),
            "live_evaluation": dict(self._runtime["live_evaluation"]),
            "cumulative": dict(self._published_totals),
            "counters_as_of": self._diagnostics_at,
            "selected_scope": "acceptance_run" if test_run_id is not None else "current_owner",
            "selected": self._owner_diagnostics.get(selected, {}),
            "lease": dict(self._lease_gate.status),
            "tracked_rule_limit": 3000,
            "observations_meaning": "ready_observation_transitions_per_rule_revision",
            "diagnostics_retention": "latest_3000_rule_revisions_in_this_process",
            "provider_calls": False,
            "database_calls": False,
        }

    def _observe_rule(self, rule, snapshot, ready, now):
        key = (rule["id"], rule["revision"])
        row = self._diagnostic_rules.get(key)
        if row is None:
            row = {
                "owner": rule["owner"],
                "category": rule["category"],
                "checked": 0,
                "ready": 0,
                "unknown": 0,
                "observations": 0,
                "first_checked_at": now,
                "last_checked_at": now,
                "first_ready_at": None,
                "last_ready_at": None,
                "last_observation": None,
            }
            self._diagnostic_rules[key] = row
        row["checked"] += 1
        row["ready" if ready else "unknown"] += 1
        row["last_checked_at"] = now
        row["latest_ready"] = bool(ready)
        observation = (snapshot.get("continuity_id"), snapshot.get("observation_id"))
        if ready:
            if observation != row["last_observation"]:
                row["observations"] += 1
                row["last_observation"] = observation
            row["first_ready_at"] = row["first_ready_at"] or now
            row["last_ready_at"] = now
        self._diagnostic_rules.move_to_end(key)
        while len(self._diagnostic_rules) > 3000:
            self._diagnostic_rules.popitem(last=False)

    def _publish_diagnostics(self):
        grouped = {}
        now = self._wall_clock()
        for row in self._diagnostic_rules.values():
            result = grouped.setdefault(row["owner"], {}).setdefault(
                row["category"],
                {
                    "distinct_rule_revisions_checked": 0,
                    "distinct_rule_revisions_ready": 0,
                    "checked": 0,
                    "ready": 0,
                    "unknown": 0,
                    "observations": 0,
                    "first_checked_at": None,
                    "last_checked_at": None,
                    "first_ready_at": None,
                    "last_ready_at": None,
                    "checked_rules_last_60s": 0,
                    "ready_rules_last_60s": 0,
                    "latest_ready_rules_last_60s": 0,
                    "oldest_last_checked_at": None,
                    "max_rule_check_age_seconds": 0,
                },
            )
            age = max(0, (now - datetime.fromisoformat(row["last_checked_at"])).total_seconds())
            result["checked_rules_last_60s"] += age <= 60
            result["latest_ready_rules_last_60s"] += age <= 60 and row["latest_ready"]
            if row["last_ready_at"]:
                ready_age = (now - datetime.fromisoformat(row["last_ready_at"])).total_seconds()
                result["ready_rules_last_60s"] += 0 <= ready_age <= 60
            result["max_rule_check_age_seconds"] = max(result["max_rule_check_age_seconds"], age)
            oldest = result["oldest_last_checked_at"]
            result["oldest_last_checked_at"] = (
                min(oldest, row["last_checked_at"]) if oldest else row["last_checked_at"]
            )
            result["distinct_rule_revisions_checked"] += 1
            result["distinct_rule_revisions_ready"] += bool(row["ready"])
            for key in ("checked", "ready", "unknown", "observations"):
                result[key] += row[key]
            for key in ("first_checked_at", "first_ready_at"):
                if row[key]:
                    result[key] = min(result[key], row[key]) if result[key] else row[key]
            for key in ("last_checked_at", "last_ready_at"):
                if row[key]:
                    result[key] = max(result[key], row[key]) if result[key] else row[key]
        self._owner_diagnostics = grouped
        self._diagnostics_at = now.isoformat()

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
        generation = repository.generation()
        if self._generation == generation and self._clock() - self._rules_at < 5:
            return
        rules = repository.active_rules()
        identity = [(r["id"], r["revision"]) for r in rules]
        changed = self._generation == -1 or identity != [
            (r["id"], r["revision"]) for r in self._source_rules
        ]
        if changed:
            self._cursor = (0, 0)
            valid = set(identity)
            self._states = OrderedDict((k, v) for k, v in self._states.items() if k[:2] in valid)
            self._rule_health = {k: v for k, v in self._rule_health.items() if k in valid}
        self._source_rules = rules
        self._rules_at, self._generation = self._clock(), generation

    def _jobs(self, mode="all", cursor=None):
        """Store only membership lists, not the potentially six-million-rule cross product."""
        # The provider may replace its universe during this tick. Retain the
        # existing immutable tuples so the count and iterator see one snapshot;
        # otherwise an emptied universe can spin forever without yielding work.
        memberships = [
            tuple(self.hub.symbols(rule["id"]))
            if mode == "all" or (rule["id"] in self._live_custom_ids) == (mode == "custom")
            else ()
            for rule in self._rules
        ]
        total = sum(len(symbols) for symbols in memberships)
        if not total:
            return iter(()), 0

        def jobs():
            ri, si = self._cursor if cursor is None else cursor
            ri %= len(self._rules)
            visited = 0
            while visited < min(total, MAX_EVALUATIONS_PER_TICK):
                symbols = memberships[ri]
                if si >= len(symbols):
                    ri, si = (ri + 1) % len(self._rules), 0
                    continue
                rule, symbol = self._rules[ri], symbols[si]
                si += 1
                visited += 1
                yield rule, symbol, (ri, si)

        return jobs(), total

    def _maintenance_jobs(self):
        if not self._live_bound:
            return self._jobs()
        ordinary, ordinary_total = self._jobs("ordinary")
        custom, custom_total = self._jobs("custom", self._custom_cursor)
        if not self._custom_remaining and self._clock() - self._custom_maintenance_at >= 5:
            self._custom_remaining = custom_total
            self._custom_maintenance_at = self._clock()
        custom_limit = min(custom_total, self._custom_remaining)
        custom = islice(custom, custom_limit)

        def interleaved():
            lanes = [(ordinary, "ordinary"), (custom, "custom")]
            count = 0
            while lanes and count < MAX_EVALUATIONS_PER_TICK:
                for lane in lanes.copy():
                    iterator, name = lane
                    job = next(iterator, None)
                    if job is None:
                        lanes.remove(lane)
                        continue
                    rule, symbol, cursor = job
                    yield rule, symbol, (*cursor, name)
                    count += 1
                    if count >= MAX_EVALUATIONS_PER_TICK:
                        break

        return interleaved(), ordinary_total + custom_limit

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
        with self._evaluation_lock:
            self._tick()

    def _tick(self):
        started = self._clock()
        original_cursor = self._cursor
        original_custom = (self._custom_cursor, self._custom_remaining, self._custom_maintenance_at)
        self._runtime["last_error"] = None
        self._runtime["backpressure"] = None
        try:
            self._flush_live_states(force=True)
            self._refresh()
            eligible = self._lease_gate.filter_rules(self._source_rules)
            if [(row["id"], row["revision"]) for row in eligible] != [
                (row["id"], row["revision"]) for row in self._rules
            ]:
                self._cursor = (0, 0)
                self.hub.configure(eligible)
            self._rules = eligible
            self._index_live_rules()
            jobs, total = self._maintenance_jobs()
            changes, ephemeral = [], []
            health = {}
            checked = ready_count = 0
            now = self._wall_clock()
            observed_at = now.isoformat()
            while True:
                if checked and (
                    self._clock() - started >= EVALUATION_SECONDS
                    or len(changes) >= MAX_CHANGES_PER_TICK
                ):
                    break
                # Do not restore thousands of states that cannot fit this tick's
                # time/write budget. Advance the durable cursor only for evaluated pairs.
                batch = list(
                    islice(jobs, min(STATE_LOAD_BATCH, MAX_CHANGES_PER_TICK - len(changes)))
                )
                if not batch:
                    break
                keys = [
                    (r["id"], r["revision"], s["symbol"], s["market_type"]) for r, s, _ in batch
                ]
                missing = [key for key in keys if key not in self._states]
                if missing:
                    restored = repository.load_states(missing)
                    for key in missing:
                        self._states[key] = restored.get(key)
                for (rule, symbol, cursor), key in zip(batch, keys, strict=True):
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
                    self._observe_rule(rule, snapshot, state.get("ready", False), observed_at)
                    self._diagnostic_totals["checked"] += 1
                    self._diagnostic_totals["ready"] += int(state.get("ready", False))
                    rule_key = (rule["id"], rule["revision"])
                    if rule_key not in health:
                        health[rule_key] = {
                            "checked_this_tick": 0,
                            "ready_this_tick": 0,
                            "total_symbols": self.hub.symbol_count(rule["id"]),
                            "last_checked_at": observed_at.replace("+00:00", "Z"),
                            "last_error": None,
                        }
                    result = health[rule_key]
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
                    if len(cursor) == 3 and cursor[2] == "custom":
                        self._custom_cursor = cursor[:2]
                        self._custom_remaining = max(0, self._custom_remaining - 1)
                    else:
                        self._cursor = cursor[:2]
            accepted = repository.apply_batch(changes)
            if any(change.get("event") and change["key"] in accepted for change in changes):
                self._wake_delivery()
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
            self._custom_cursor, self._custom_remaining, self._custom_maintenance_at = (
                original_custom
            )
            self._runtime["last_error"] = (
                "Disk rezervi korunuyor; değerlendirme kaydı ve teslim bekletiliyor."
            )
            self._runtime["backpressure"] = "disk_reserve"
        except Exception:
            self._cursor = original_cursor
            self._custom_cursor, self._custom_remaining, self._custom_maintenance_at = (
                original_custom
            )
            self._runtime["last_error"] = (
                "Değerlendirme tamamlanamadı; kaydedilen sıra sonraki turda yeniden denenecek."
            )
        finally:
            self._runtime["last_cycle_at"] = _now()
            self._diagnostic_totals["cycles"] += 1
            self._diagnostic_totals["failed_cycles"] += int(self._runtime["last_error"] is not None)
            self._publish_diagnostics()
            self._diagnostic_totals["last_cycle_ms"] = round((self._clock() - started) * 1000, 2)
            self._diagnostic_totals["max_cycle_ms"] = max(
                self._diagnostic_totals.get("max_cycle_ms", 0),
                self._diagnostic_totals["last_cycle_ms"],
            )
            self._published_totals = dict(self._diagnostic_totals)


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
