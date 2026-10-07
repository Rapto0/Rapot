"""Versioned advanced alarms, private watchlists and a transactional durable outbox."""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import delete, func, select, text, tuple_, update

from db_session import get_session_factory
from infrastructure.time import utc_now_naive
from models import AdvancedAlarmEvent as Event
from models import AdvancedAlarmRule as Rule
from models import AdvancedAlarmState as State
from models import AdvancedAlarmWatchlist as Watchlist
from models import BotStat

LIMITS = {
    "price": 1000,
    "technical": 1000,
    "watchlist": 1000,
    "total": 3000,
    "symbols_per_watchlist": 2000,
    "symbols_per_rule": 2000,
    "watchlists": 1000,
}
MAX_PENDING = 10000
MAX_ATTEMPTS = 5
HISTORY_DAYS = 30
MAX_TERMINAL_EVENTS = 100000
DISK_RESERVE_BYTES = (528 + 64) * 1024**2
DELIVERY_PAUSE_KEY = "advanced_alarm_delivery_pause"
_generation = 0
_storage_cache = None


class NotFound(ValueError):
    pass


class Conflict(ValueError):
    pass


class CapacityPressure(Conflict):
    """Preserve the fixed disk reserve and already queued events."""


def iso(value):
    return value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z") if value else None


def generation():
    return _generation


def _changed():
    global _generation
    _generation += 1


def _write(session):
    path = session.get_bind().url.database
    if (
        path
        and path != ":memory:"
        and shutil.disk_usage(Path(path).resolve().parent).free < DISK_RESERVE_BYTES
    ):
        raise CapacityPressure(
            "Disk rezervi nedeniyle kayıt bekletiliyor; mevcut kurallar ve kuyruk korundu."
        )
    session.execute(text("BEGIN IMMEDIATE"))


def storage_status():
    global _storage_cache
    with get_session_factory()() as session:
        path = session.get_bind().url.database
        if (
            _storage_cache
            and _storage_cache[0] == path
            and time.monotonic() - _storage_cache[1] < 10
        ):
            return dict(_storage_cache[2])
        location = Path(path).resolve() if path and path != ":memory:" else None
        free = shutil.disk_usage(location.parent).free if location else None
        result = {
            "persisted_states": session.scalar(select(func.count()).select_from(State)),
            "free_bytes": free,
            "required_reserve_bytes": DISK_RESERVE_BYTES,
            "backpressure": free is not None and free < DISK_RESERVE_BYTES,
            "database_bytes": location.stat().st_size if location and location.exists() else 0,
        }
        _storage_cache = (path, time.monotonic(), result)
        return dict(result)


def _rule(row):
    names = (
        "id",
        "owner",
        "name",
        "category",
        "scope",
        "watchlist_id",
        "timeframe",
        "trigger",
        "mode",
        "cooldown_seconds",
        "enabled",
        "notify_telegram",
        "revision",
        "last_error",
    )
    result = {name: getattr(row, name) for name in names}
    result.update(
        symbols=json.loads(row.symbols_json),
        condition=json.loads(row.condition_json),
        created_at=iso(row.created_at),
        updated_at=iso(row.updated_at),
        last_triggered_at=iso(row.last_triggered_at),
        state="paused" if not row.enabled else "error" if row.last_error else "pending",
    )
    return result


def _watchlist(row):
    return {
        "id": row.id,
        "name": row.name,
        "symbols": json.loads(row.symbols_json),
        "revision": row.revision,
        "created_at": iso(row.created_at),
        "updated_at": iso(row.updated_at),
    }


def _event(row):
    names = (
        "id",
        "rule_id",
        "rule_name",
        "category",
        "symbol",
        "market_type",
        "value",
        "bar_time",
        "observed_at",
        "delivery_status",
        "delivery_error",
        "delivery_attempts",
    )
    return {
        **{name: getattr(row, name) for name in names},
        "values": json.loads(row.values_json),
        "created_at": iso(row.created_at),
        "next_attempt_at": iso(row.next_attempt_at),
    }


def _owned(session, rule_id, owner):
    row = session.scalar(
        select(Rule).where(Rule.id == rule_id, Rule.owner == owner, Rule.deleted_at.is_(None))
    )
    if row is None:
        raise NotFound("Alarm bulunamadı.")
    return row


def _invalidate(session, row):
    row.revision += 1
    row.updated_at = utc_now_naive()
    session.execute(delete(State).where(State.rule_id == row.id))
    session.execute(
        update(Event)
        .where(Event.rule_id == row.id, Event.delivery_status == "pending")
        .values(delivery_status="cancelled", delivery_error="Alarm değiştirildi veya durduruldu.")
    )


def list_rules(owner):
    with get_session_factory()() as session:
        rows = session.scalars(
            select(Rule)
            .where(Rule.owner == owner, Rule.deleted_at.is_(None))
            .order_by(Rule.created_at.desc(), Rule.id)
        ).all()
        return [{k: v for k, v in _rule(row).items() if k != "owner"} for row in rows]


def usage(owner):
    with get_session_factory()() as session:
        counts = dict(
            session.execute(
                select(Rule.category, func.count())
                .where(Rule.owner == owner, Rule.deleted_at.is_(None))
                .group_by(Rule.category)
            ).all()
        )
        return {
            category: counts.get(category, 0) for category in ("price", "technical", "watchlist")
        }


def save_rule(owner, payload, rule_id=None):
    with get_session_factory()() as session:
        _write(session)
        row = _owned(session, rule_id, owner) if rule_id else None
        if row and payload.get("revision") is not None and payload["revision"] != row.revision:
            raise Conflict("Alarm başka bir işlemde değişti; listeyi yenileyin.")
        count = session.scalar(
            select(func.count())
            .select_from(Rule)
            .where(
                Rule.category == payload["category"],
                Rule.deleted_at.is_(None),
                Rule.id != (rule_id or ""),
            )
        )
        if count >= LIMITS[payload["category"]]:
            raise Conflict(
                "Bu kategoride 1000 alarm sınırına ulaşıldı; duraklatılanlar da sayılır."
            )
        if payload["scope"] == "watchlist":
            target = session.get(Watchlist, payload["watchlist_id"])
            if target is None or target.owner != owner:
                raise NotFound("İzleme listesi bulunamadı.")
        if row:
            _invalidate(session, row)
        else:
            row = Rule(id=str(uuid4()), owner=owner, revision=1, created_at=utc_now_naive())
        for name in (
            "name",
            "category",
            "scope",
            "watchlist_id",
            "timeframe",
            "trigger",
            "mode",
            "cooldown_seconds",
            "enabled",
            "notify_telegram",
        ):
            setattr(row, name, payload[name])
        row.symbols_json = json.dumps(payload["symbols"], separators=(",", ":"))
        row.condition_json = json.dumps(
            payload["condition"], separators=(",", ":"), allow_nan=False
        )
        row.updated_at = utc_now_naive()
        row.last_error = None
        session.add(row)
        session.commit()
        result = _rule(row)
        result.pop("owner")
    _changed()
    return result


def delete_rule(owner, rule_id):
    with get_session_factory()() as session:
        _write(session)
        row = _owned(session, rule_id, owner)
        _invalidate(session, row)
        row.enabled = False
        row.deleted_at = utc_now_naive()
        session.commit()
    _changed()


def list_watchlists(owner):
    with get_session_factory()() as session:
        return [
            _watchlist(row)
            for row in session.scalars(
                select(Watchlist)
                .where(Watchlist.owner == owner)
                .order_by(Watchlist.created_at, Watchlist.id)
            )
        ]


def save_watchlist(owner, payload, watchlist_id=None):
    with get_session_factory()() as session:
        _write(session)
        row = session.get(Watchlist, watchlist_id) if watchlist_id else None
        if watchlist_id and (row is None or row.owner != owner):
            raise NotFound("İzleme listesi bulunamadı.")
        if row and payload.get("revision") is not None and payload["revision"] != row.revision:
            raise Conflict("İzleme listesi değişti; yenileyin.")
        if row is None:
            count = session.scalar(select(func.count()).select_from(Watchlist))
            if count >= LIMITS["watchlists"]:
                raise Conflict("1000 izleme listesi sınırına ulaşıldı.")
            row = Watchlist(id=str(uuid4()), owner=owner, revision=1, created_at=utc_now_naive())
        else:
            row.revision += 1
            for rule in session.scalars(
                select(Rule).where(Rule.watchlist_id == row.id, Rule.deleted_at.is_(None))
            ):
                _invalidate(session, rule)
        row.name = payload["name"]
        row.symbols_json = json.dumps(payload["symbols"], separators=(",", ":"))
        row.updated_at = utc_now_naive()
        session.add(row)
        session.commit()
        result = _watchlist(row)
    _changed()
    return result


def delete_watchlist(owner, watchlist_id):
    with get_session_factory()() as session:
        _write(session)
        row = session.get(Watchlist, watchlist_id)
        if row is None or row.owner != owner:
            raise NotFound("İzleme listesi bulunamadı.")
        for rule in session.scalars(
            select(Rule).where(Rule.watchlist_id == row.id, Rule.deleted_at.is_(None))
        ):
            _invalidate(session, rule)
            rule.enabled = False
            rule.last_error = "İzleme listesi silindi; yeni liste seçilene kadar duraklatıldı."
        session.delete(row)
        session.commit()
    _changed()


def active_rules():
    with get_session_factory()() as session:
        symbols, memberships = {}, {}

        def intern(raw):
            digest = hashlib.sha256(raw.encode()).digest()
            if digest not in memberships:
                entries = []
                for item in json.loads(raw):
                    key = (item["symbol"], item["market_type"])
                    entries.append(symbols.setdefault(key, item))
                memberships[digest] = tuple(entries)
            return memberships[digest]

        referenced = select(Rule.watchlist_id).where(
            Rule.enabled.is_(True), Rule.deleted_at.is_(None), Rule.watchlist_id.is_not(None)
        )
        lists = {}
        for row in session.scalars(select(Watchlist).where(Watchlist.id.in_(referenced))).yield_per(
            20
        ):
            lists[row.id] = (row.owner, intern(row.symbols_json))
        result = []
        for row in session.scalars(
            select(Rule).where(Rule.enabled.is_(True), Rule.deleted_at.is_(None)).order_by(Rule.id)
        ).yield_per(50):
            item = _rule(row)
            item["symbols"] = intern(row.symbols_json)
            if row.scope == "watchlist":
                target = lists.get(row.watchlist_id)
                item["symbols"] = target[1] if target and target[0] == row.owner else []
            result.append(item)
        return result


def load_states(keys):
    if not keys:
        return {}
    result = {}
    with get_session_factory()() as session:
        for offset in range(0, len(keys), 200):
            rows = session.scalars(
                select(State).where(
                    tuple_(State.rule_id, State.revision, State.symbol, State.market_type).in_(
                        keys[offset : offset + 200]
                    )
                )
            )
            for row in rows:
                key = (row.rule_id, row.revision, row.symbol, row.market_type)
                result[key] = {
                    "observation_id": row.observation_id,
                    "continuity_id": row.continuity_id,
                    "matched": row.matched,
                    "ready": row.ready,
                    "last_bar": row.last_bar,
                    "last_triggered_at": iso(row.last_triggered_at),
                }
    return result


def apply_batch(changes):
    """One transaction; reject stale revisions before state or event changes."""
    if not changes:
        return set()
    accepted = set()
    with get_session_factory()() as session:
        _write(session)
        rule_ids = {item["key"][0] for item in changes}
        rules = {row.id: row for row in session.scalars(select(Rule).where(Rule.id.in_(rule_ids)))}
        pending = session.scalar(
            select(func.count()).select_from(Event).where(Event.delivery_status == "pending")
        )
        states = {}
        keys = [change["key"] for change in changes]
        for offset in range(0, len(keys), 200):
            for row in session.scalars(
                select(State).where(
                    tuple_(State.rule_id, State.revision, State.symbol, State.market_type).in_(
                        keys[offset : offset + 200]
                    )
                )
            ):
                states[(row.rule_id, row.revision, row.symbol, row.market_type)] = row
        for change in changes:
            key = change["key"]
            rule = rules.get(key[0])
            if rule is None or rule.deleted_at or not rule.enabled or rule.revision != key[1]:
                continue
            state = states.get(key)
            if state is None:
                state = State(rule_id=key[0], revision=key[1], symbol=key[2], market_type=key[3])
                session.add(state)
                states[key] = state
            values = change["state"]
            for name in ("observation_id", "continuity_id", "matched", "ready", "last_bar"):
                setattr(state, name, values.get(name))
            last = values.get("last_triggered_at")
            state.last_triggered_at = (
                datetime.fromisoformat(last.replace("Z", "+00:00")).replace(tzinfo=None)
                if last
                else None
            )
            state.updated_at = utc_now_naive()
            event = change.get("event")
            if event:
                exists = session.scalar(
                    select(Event.id).where(
                        Event.rule_id == rule.id,
                        Event.revision == rule.revision,
                        Event.symbol == key[2],
                        Event.market_type == key[3],
                        Event.observation_id == event["observation_id"],
                    )
                )
                if exists is None:
                    status = "pending" if rule.notify_telegram else "not_requested"
                    error = None
                    if status == "pending" and pending >= MAX_PENDING:
                        status, error = "failed", "Bildirim kuyruğu dolu; bu olay teslim edilmedi."
                    if status == "pending":
                        pending += 1
                    session.add(
                        Event(
                            owner=rule.owner,
                            rule_id=rule.id,
                            revision=rule.revision,
                            rule_name=rule.name,
                            category=rule.category,
                            symbol=key[2],
                            market_type=key[3],
                            observation_id=event["observation_id"],
                            value=event.get("value"),
                            values_json=json.dumps(event.get("values", {}), allow_nan=False),
                            bar_time=event.get("bar_time"),
                            observed_at=event.get("observed_at"),
                            created_at=utc_now_naive(),
                            delivery_status=status,
                            delivery_error=error,
                        )
                    )
                    rule.last_triggered_at = state.last_triggered_at
            accepted.add(key)
        session.commit()
    return accepted


def events(owner, after_id=None, limit=100):
    with get_session_factory()() as session:
        query = select(Event).where(Event.owner == owner)
        if after_id is None:
            query = query.order_by(Event.id.desc())
        else:
            query = query.where(Event.id > after_id).order_by(Event.id)
        rows = session.scalars(query.limit(limit + 1)).all()
        return {
            "events": [_event(row) for row in rows[:limit]],
            "next_after_id": max((row.id for row in rows[:limit]), default=after_id or 0),
            "has_more": len(rows) > limit,
        }


def delivery_status(owner):
    with get_session_factory()() as session:
        counts = dict(
            session.execute(
                select(Event.delivery_status, func.count())
                .where(Event.owner == owner)
                .group_by(Event.delivery_status)
            ).all()
        )
    return {
        key: counts.get(key, 0)
        for key in ("pending", "sent", "failed", "cancelled", "not_requested")
    }


def claim_delivery(now=None):
    now = now or utc_now_naive()
    with get_session_factory()() as session:
        _write(session)
        pause = session.scalar(select(BotStat).where(BotStat.stat_name == DELIVERY_PAUSE_KEY))
        if pause and datetime.fromisoformat(pause.stat_value) > now:
            return None
        row = session.scalar(
            select(Event)
            .where(
                Event.delivery_status == "pending",
                (Event.next_attempt_at.is_(None)) | (Event.next_attempt_at <= now),
            )
            .order_by(Event.id)
            .limit(1)
        )
        if row is None:
            return None
        if row.owner.startswith("__acceptance__:"):
            row.delivery_status, row.delivery_error, row.next_attempt_at = (
                "cancelled",
                "Kabul testi bildirim gönderemez.",
                None,
            )
            session.commit()
            return None
        rule = session.get(Rule, row.rule_id)
        if rule is None or rule.deleted_at or not rule.enabled or rule.revision != row.revision:
            row.delivery_status, row.delivery_error = (
                "cancelled",
                "Alarm değiştirildi veya durduruldu.",
            )
            session.commit()
            return None
        if row.delivery_attempts >= MAX_ATTEMPTS:
            row.delivery_status, row.delivery_error = "failed", "Teslim deneme sınırına ulaşıldı."
            session.commit()
            return None
        row.delivery_attempts += 1
        row.next_attempt_at = now + timedelta(seconds=120)
        session.commit()
        return _event(row)


def finish_delivery(event_id, *, sent=False, retry_after=None):
    with get_session_factory()() as session:
        _write(session)
        row = session.get(Event, event_id)
        if row is None:
            return
        if retry_after is not None:
            pause_until = utc_now_naive() + timedelta(seconds=min(86400, max(1, retry_after)))
            pause = session.scalar(select(BotStat).where(BotStat.stat_name == DELIVERY_PAUSE_KEY))
            if pause is None:
                session.add(
                    BotStat(stat_name=DELIVERY_PAUSE_KEY, stat_value=pause_until.isoformat())
                )
            elif datetime.fromisoformat(pause.stat_value) < pause_until:
                pause.stat_value = pause_until.isoformat()
        if sent and row.delivery_attempts:
            # An edit cannot retract an HTTP request already accepted by Telegram.
            row.delivery_status, row.delivery_error, row.next_attempt_at = "sent", None, None
        elif row.delivery_status != "pending":
            session.commit()
            return
        elif row.delivery_attempts >= MAX_ATTEMPTS:
            row.delivery_status, row.delivery_error = (
                "failed",
                "Telegram teslimi 5 denemede doğrulanamadı.",
            )
        else:
            delay = min(86400, max(2**row.delivery_attempts * 30, retry_after or 0))
            row.next_attempt_at = utc_now_naive() + timedelta(seconds=delay)
            row.delivery_error = "Telegram gönderimi başarısız; yeniden denenecek."
        session.commit()


def prune_history():
    with get_session_factory()() as session:
        _write(session)
        terminal = Event.delivery_status != "pending"
        session.execute(
            delete(Event).where(
                terminal, Event.created_at < utc_now_naive() - timedelta(days=HISTORY_DAYS)
            )
        )
        cutoff = session.scalar(
            select(Event.id)
            .where(terminal)
            .order_by(Event.id.desc())
            .offset(MAX_TERMINAL_EVENTS)
            .limit(1)
        )
        if cutoff:
            session.execute(delete(Event).where(terminal, Event.id <= cutoff))
        session.execute(
            delete(Rule).where(
                Rule.deleted_at < utc_now_naive() - timedelta(days=HISTORY_DAYS),
                ~select(Event.id).where(Event.rule_id == Rule.id).exists(),
            )
        )
        session.commit()
