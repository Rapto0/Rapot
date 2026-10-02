"""SQLite persistence and transactional concurrency guards for server alarms."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, func, select, text, update

from db_session import get_session_factory
from infrastructure.time import utc_now_naive
from models import BotStat, ServerAlarmEvent, ServerAlarmRule, ServerAlarmSymbolState

LIMITS = {"max_rules": 50, "max_symbols_per_rule": 20, "max_subscriptions": 100}
MAX_DELIVERIES_PER_CYCLE = 20
MAX_DELIVERY_ATTEMPTS = 3
MAX_PENDING_DELIVERIES = 1000
MAX_TERMINAL_EVENTS = 20_000
MAX_EMPTY_DELETED_RULES = 2000
HISTORY_DAYS = 30
_CURSOR_KEY = "server_alarm_cursor"


class AlarmNotFoundError(ValueError):
    """Rule does not exist or belongs to another administrator."""


class AlarmLimitError(ValueError):
    """The installation's bounded rule/subscription budget has been reached."""


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


def _rule_dict(rule: ServerAlarmRule) -> dict[str, Any]:
    if not rule.enabled:
        state = "paused"
    elif rule.last_error:
        state = "error"
    elif rule.last_checked_at:
        state = "active"
    else:
        state = "pending"
    return {
        "id": rule.id,
        "name": rule.name,
        "symbols": json.loads(rule.symbols_json),
        "indicator": rule.indicator,
        "timeframe": rule.timeframe,
        "side": rule.side,
        "threshold": rule.threshold,
        "mode": rule.mode,
        "enabled": rule.enabled,
        "notify_telegram": rule.notify_telegram,
        "revision": rule.revision,
        "created_at": _iso(rule.created_at),
        "updated_at": _iso(rule.updated_at),
        "last_checked_at": _iso(rule.last_checked_at),
        "last_triggered_at": _iso(rule.last_triggered_at),
        "last_error": rule.last_error,
        "state": state,
    }


def list_rules(owner: str) -> list[dict[str, Any]]:
    with get_session_factory()() as session:
        rows = session.scalars(
            select(ServerAlarmRule)
            .where(ServerAlarmRule.owner == owner, ServerAlarmRule.deleted_at.is_(None))
            .order_by(ServerAlarmRule.created_at.desc(), ServerAlarmRule.id)
        ).all()
        return [_rule_dict(row) for row in rows]


def _begin_write(session: Any) -> None:
    # Serialize the global budget check and revision checks with concurrent API edits.
    session.execute(text("BEGIN IMMEDIATE"))


def _cancel_pending(session: Any, rule_id: str) -> None:
    session.execute(
        update(ServerAlarmEvent)
        .where(ServerAlarmEvent.rule_id == rule_id, ServerAlarmEvent.delivery_status == "pending")
        .values(delivery_status="failed", delivery_error="Kural değiştirildi veya silindi.")
    )


def save_rule(owner: str, payload: dict[str, Any], *, rule_id: str | None = None) -> dict:
    """Save an already validated API rule and invalidate all prior in-flight work."""
    with get_session_factory()() as session:
        _begin_write(session)
        rules = session.scalars(
            select(ServerAlarmRule).where(ServerAlarmRule.deleted_at.is_(None))
        ).all()
        existing = next(
            (item for item in rules if item.id == rule_id and item.owner == owner), None
        )
        if rule_id is not None and existing is None:
            raise AlarmNotFoundError()
        if existing is None and len(rules) >= LIMITS["max_rules"]:
            raise AlarmLimitError("Sunucu en fazla 50 alarm kuralı saklayabilir.")
        subscriptions = sum(
            len(json.loads(item.symbols_json)) for item in rules if item.id != rule_id
        ) + len(payload["symbols"])
        if subscriptions > LIMITS["max_subscriptions"]:
            raise AlarmLimitError("Sunucu alarmlarında toplam en fazla 100 sembol izlenebilir.")
        now = utc_now_naive()
        rule = existing or ServerAlarmRule(id=str(uuid4()), owner=owner, created_at=now, revision=1)
        if existing is not None:
            rule.revision += 1
            _cancel_pending(session, rule.id)
            session.execute(
                delete(ServerAlarmSymbolState).where(ServerAlarmSymbolState.rule_id == rule.id)
            )
        for name in (
            "name",
            "indicator",
            "timeframe",
            "side",
            "threshold",
            "mode",
            "enabled",
            "notify_telegram",
        ):
            setattr(rule, name, payload[name])
        rule.symbols_json = json.dumps(payload["symbols"], ensure_ascii=False)
        rule.updated_at = now
        rule.last_checked_at = None
        rule.last_error = None
        session.add(rule)
        session.commit()
        return _rule_dict(rule)


def delete_rule(owner: str, rule_id: str) -> None:
    with get_session_factory()() as session:
        _begin_write(session)
        rule = session.scalar(
            select(ServerAlarmRule).where(
                ServerAlarmRule.id == rule_id,
                ServerAlarmRule.owner == owner,
                ServerAlarmRule.deleted_at.is_(None),
            )
        )
        if rule is None:
            raise AlarmNotFoundError()
        rule.deleted_at = utc_now_naive()
        rule.enabled = False
        rule.revision += 1
        _cancel_pending(session, rule.id)
        session.execute(
            delete(ServerAlarmSymbolState).where(ServerAlarmSymbolState.rule_id == rule.id)
        )
        session.commit()


def _event_dict(event: ServerAlarmEvent) -> dict[str, Any]:
    return {
        name: getattr(event, name)
        for name in (
            "id",
            "rule_id",
            "rule_name",
            "symbol",
            "market_type",
            "indicator",
            "timeframe",
            "side",
            "value",
            "delivery_status",
            "delivery_error",
        )
    } | {"bar_time": _iso(event.bar_time), "created_at": _iso(event.created_at)}


def list_events(owner: str, limit: int = 100) -> list[dict[str, Any]]:
    with get_session_factory()() as session:
        events = session.scalars(
            select(ServerAlarmEvent)
            .where(ServerAlarmEvent.owner == owner)
            .order_by(ServerAlarmEvent.id.desc())
            .limit(min(max(limit, 1), 200))
        ).all()
        return [_event_dict(event) for event in events]


def active_snapshots() -> list[dict[str, Any]]:
    with get_session_factory()() as session:
        return [
            _rule_dict(rule)
            for rule in session.scalars(
                select(ServerAlarmRule)
                .where(ServerAlarmRule.enabled.is_(True), ServerAlarmRule.deleted_at.is_(None))
                .order_by(ServerAlarmRule.created_at, ServerAlarmRule.id)
                .limit(LIMITS["max_rules"])
            ).all()
        ]


def evaluation_cursor() -> tuple[str, str, str] | None:
    """Resume the bounded scan after its last attempted subscription across restarts."""
    with get_session_factory()() as session:
        raw = session.scalar(select(BotStat.stat_value).where(BotStat.stat_name == _CURSOR_KEY))
    try:
        value = json.loads(raw) if raw else None
    except (TypeError, ValueError):
        return None
    if isinstance(value, list) and len(value) == 3 and all(isinstance(item, str) for item in value):
        return tuple(value)
    return None


def advance_evaluation_cursor(key: tuple[str, str, str]) -> None:
    with get_session_factory()() as session:
        _begin_write(session)
        cursor = session.scalar(select(BotStat).where(BotStat.stat_name == _CURSOR_KEY))
        if cursor is None:
            cursor = BotStat(stat_name=_CURSOR_KEY)
            session.add(cursor)
        cursor.stat_value = json.dumps(key)
        cursor.updated_at = utc_now_naive()
        session.commit()


def _current_rule(session: Any, snapshot: dict) -> ServerAlarmRule | None:
    return session.scalar(
        select(ServerAlarmRule).where(
            ServerAlarmRule.id == snapshot["id"],
            ServerAlarmRule.revision == snapshot["revision"],
            ServerAlarmRule.enabled.is_(True),
            ServerAlarmRule.deleted_at.is_(None),
        )
    )


def record_evaluation(snapshot: dict, symbol: dict, result: dict) -> None:
    bar = datetime.fromisoformat(result["bar_time"].replace("Z", "+00:00"))
    closed_at = datetime.fromisoformat(result["bar_closed_at"].replace("Z", "+00:00"))
    if bar.tzinfo is None or closed_at.tzinfo is None or not math.isfinite(result["value"]):
        raise ValueError("Invalid evaluator result")
    bar = bar.astimezone(UTC).replace(tzinfo=None)
    closed_at = closed_at.astimezone(UTC).replace(tzinfo=None)
    with get_session_factory()() as session:
        _begin_write(session)
        rule = _current_rule(session, snapshot)
        if rule is None:
            return
        identity = (rule.id, rule.revision, symbol["symbol"], symbol["market_type"])
        state = session.get(ServerAlarmSymbolState, identity)
        if state is not None and bar <= state.bar_time:
            return
        matched = bool(result["matched"])
        trigger = (
            closed_at >= rule.updated_at
            and matched
            and (rule.mode == "once_per_bar" or not result["previous_matched"])
        )
        if state is None:
            state = ServerAlarmSymbolState(
                rule_id=rule.id, revision=rule.revision, **symbol, bar_time=bar, matched=matched
            )
            session.add(state)
        else:
            state.bar_time = bar
            state.matched = matched
        if trigger:
            now = utc_now_naive()
            delivery_status = "pending" if rule.notify_telegram else "not_requested"
            delivery_error = None
            if rule.notify_telegram:
                pending_count = session.scalar(
                    select(func.count())
                    .select_from(ServerAlarmEvent)
                    .where(ServerAlarmEvent.delivery_status == "pending")
                )
                if pending_count >= MAX_PENDING_DELIVERIES:
                    delivery_status = "failed"
                    delivery_error = "Telegram kuyruğu dolu; bu olay için gönderim yapılmadı."
            session.add(
                ServerAlarmEvent(
                    rule_id=rule.id,
                    revision=rule.revision,
                    owner=rule.owner,
                    rule_name=rule.name,
                    **symbol,
                    indicator=rule.indicator,
                    timeframe=rule.timeframe,
                    side=rule.side,
                    value=float(result["value"]),
                    bar_time=bar,
                    created_at=now,
                    delivery_status=delivery_status,
                    delivery_error=delivery_error,
                    next_attempt_at=now if delivery_status == "pending" else None,
                    delivery_attempts=0,
                )
            )
            rule.last_triggered_at = now
        session.commit()


def record_cycle_result(snapshot: dict, errors: list[str]) -> None:
    with get_session_factory()() as session:
        _begin_write(session)
        rule = _current_rule(session, snapshot)
        if rule is None:
            return
        rule.last_checked_at = utc_now_naive()
        rule.last_error = "; ".join(errors)[:300] if errors else None
        session.commit()


def claim_delivery(event_id: int) -> dict | None:
    with get_session_factory()() as session:
        _begin_write(session)
        event = session.get(ServerAlarmEvent, event_id)
        now = utc_now_naive()
        if event is None or event.delivery_status != "pending":
            return None
        if event.next_attempt_at and event.next_attempt_at > now:
            return None
        rule = session.get(ServerAlarmRule, event.rule_id)
        if rule is None or rule.deleted_at or not rule.enabled or rule.revision != event.revision:
            event.delivery_status = "failed"
            event.delivery_error = "Kural değiştirildi veya silindi."
            session.commit()
            return None
        if event.delivery_attempts >= MAX_DELIVERY_ATTEMPTS:
            event.delivery_status = "failed"
            event.delivery_error = "Telegram teslimi doğrulanamadı; deneme sınırına ulaşıldı."
            session.commit()
            return None
        event.delivery_attempts += 1
        # Durable lease: a crash recovers the item after this bounded delay.
        event.next_attempt_at = now + timedelta(minutes=2**event.delivery_attempts)
        snapshot = _event_dict(event)
        session.commit()
        return snapshot


def finish_delivery(event_id: int, sent: bool) -> None:
    with get_session_factory()() as session:
        _begin_write(session)
        event = session.get(ServerAlarmEvent, event_id)
        if event is None:
            return
        if sent:
            # An edit after the HTTP request cannot retract a delivered message.
            event.delivery_status = "sent"
            event.delivery_error = None
            event.next_attempt_at = None
        elif event.delivery_status == "pending":
            event.delivery_error = "Telegram gönderimi başarısız; yeniden denenecek."
            if event.delivery_attempts >= MAX_DELIVERY_ATTEMPTS:
                event.delivery_status = "failed"
                event.delivery_error = "Telegram gönderimi 3 denemede başarısız oldu."
        session.commit()


def pending_delivery_ids() -> list[int]:
    with get_session_factory()() as session:
        return list(
            session.scalars(
                select(ServerAlarmEvent.id)
                .where(
                    ServerAlarmEvent.delivery_status == "pending",
                    ServerAlarmEvent.next_attempt_at <= utc_now_naive(),
                )
                .order_by(ServerAlarmEvent.id)
                .limit(MAX_DELIVERIES_PER_CYCLE)
            )
        )


def prune_history() -> None:
    """Bound only these new tables; pending outbox records are never pruned."""
    with get_session_factory()() as session:
        _begin_write(session)
        cutoff = utc_now_naive() - timedelta(days=HISTORY_DAYS)
        terminal = ServerAlarmEvent.delivery_status != "pending"
        session.execute(
            delete(ServerAlarmEvent).where(terminal, ServerAlarmEvent.created_at < cutoff)
        )
        overflow = (
            select(ServerAlarmEvent.id)
            .where(terminal)
            .order_by(ServerAlarmEvent.id.desc())
            .offset(MAX_TERMINAL_EVENTS)
        )
        session.execute(delete(ServerAlarmEvent).where(ServerAlarmEvent.id.in_(overflow)))
        no_events = (
            ~select(ServerAlarmEvent.id)
            .where(ServerAlarmEvent.rule_id == ServerAlarmRule.id)
            .exists()
        )
        empty_deleted = (ServerAlarmRule.deleted_at.is_not(None), no_events)
        session.execute(
            delete(ServerAlarmRule).where(*empty_deleted, ServerAlarmRule.deleted_at < cutoff)
        )
        rule_overflow = (
            select(ServerAlarmRule.id)
            .where(*empty_deleted)
            .order_by(ServerAlarmRule.deleted_at.desc(), ServerAlarmRule.id)
            .offset(MAX_EMPTY_DELETED_RULES)
        )
        session.execute(delete(ServerAlarmRule).where(ServerAlarmRule.id.in_(rule_overflow)))
        session.commit()
