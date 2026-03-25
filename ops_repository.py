"""
Operational data-access helpers backed by SQLAlchemy.

This module centralizes health/special-tag/stat queries so callers do not need
to use legacy sqlite3 helpers directly.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, text
from sqlalchemy.orm import aliased

from db_session import get_session
from logger import get_logger
from models import BotStat, Order, Signal, Trade

logger = get_logger(__name__)

SYNC_SCAN_COUNT_STAT_KEY = "sync_scan_count"
SYNC_SIGNAL_COUNT_STAT_KEY = "sync_signal_count"
ASYNC_SCAN_COUNT_STAT_KEY = "async_scan_count"
ASYNC_SIGNAL_COUNT_STAT_KEY = "async_signal_count"

ACTIVE_ORDER_STATUSES = ("NEW", "PENDING", "OPEN", "PARTIALLY_FILLED")

SPECIAL_TAG_RULES: tuple[dict[str, Any], ...] = (
    {
        "tag": "BELES",
        "signal_type": "AL",
        "target_timeframe": "ME",
        "required_timeframes": ("1D", "2W-FRI", "ME"),
    },
    {
        "tag": "COK_UCUZ",
        "signal_type": "AL",
        "target_timeframe": "3W-FRI",
        "required_timeframes": ("1D", "W-FRI", "3W-FRI"),
    },
    {
        "tag": "PAHALI",
        "signal_type": "SAT",
        "target_timeframe": "W-FRI",
        "required_timeframes": ("1D", "W-FRI"),
    },
    {
        "tag": "FAHIS_FIYAT",
        "signal_type": "SAT",
        "target_timeframe": "ME",
        "required_timeframes": ("1D", "W-FRI", "ME"),
    },
)


def get_bot_stat(name: str) -> str | None:
    """Read a bot stat value."""
    with get_session() as session:
        row = session.query(BotStat.stat_value).filter(BotStat.stat_name == name).first()
        return str(row[0]) if row else None


def set_bot_stat(name: str, value: str) -> None:
    """Create or update a bot stat value."""
    with get_session() as session:
        stat = session.query(BotStat).filter(BotStat.stat_name == name).first()
        if stat is None:
            session.add(BotStat(stat_name=name, stat_value=value))
            return
        stat.stat_value = value
        session.add(stat)


def get_bot_stat_int(name: str, default: int = 0) -> int:
    raw_value = get_bot_stat(name)
    if raw_value is None:
        return default
    try:
        return int(str(raw_value).strip())
    except (TypeError, ValueError):
        return default


def set_bot_stat_int(name: str, value: int) -> None:
    set_bot_stat(name, str(int(value)))


def increment_bot_stat_int(name: str, step: int = 1) -> int:
    now = datetime.utcnow()
    with get_session() as session:
        session.execute(
            text(
                """
                INSERT INTO bot_stats (stat_name, stat_value, updated_at)
                VALUES (:name, :step_value, :updated_at)
                ON CONFLICT(stat_name) DO UPDATE SET
                    stat_value = CAST(bot_stats.stat_value AS INTEGER) + :step_value,
                    updated_at = :updated_at
                """
            ),
            {"name": name, "step_value": int(step), "updated_at": now},
        )
        row = session.query(BotStat.stat_value).filter(BotStat.stat_name == name).first()
        return int(str(row[0])) if row else 0


def _lock_stat_name(lock_name: str) -> str:
    return f"distributed_lock:{lock_name}"


def acquire_distributed_lock(lock_name: str, owner: str, ttl_seconds: int = 900) -> bool:
    """
    Acquire distributed lock backed by bot_stats table.
    """
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=max(1, int(ttl_seconds)))
    lock_key = _lock_stat_name(lock_name)

    with get_session() as session:
        row = session.query(BotStat).filter(BotStat.stat_name == lock_key).first()

        if row is None:
            payload = {"owner": owner, "expires_at": expires_at.isoformat()}
            session.add(BotStat(stat_name=lock_key, stat_value=json.dumps(payload)))
            return True

        try:
            payload = json.loads(str(row.stat_value or "{}"))
        except json.JSONDecodeError:
            payload = {}
        current_owner = str(payload.get("owner", ""))
        expires_raw = str(payload.get("expires_at", ""))
        current_expires_at: datetime | None = None
        if expires_raw:
            with_expires = expires_raw.replace("Z", "+00:00")
            try:
                current_expires_at = datetime.fromisoformat(with_expires).replace(tzinfo=None)
            except ValueError:
                current_expires_at = None

        is_expired = current_expires_at is None or current_expires_at <= now
        if is_expired or current_owner == owner:
            new_payload = {"owner": owner, "expires_at": expires_at.isoformat()}
            row.stat_value = json.dumps(new_payload)
            session.add(row)
            return True

        return False


def release_distributed_lock(lock_name: str, owner: str) -> bool:
    """
    Release distributed lock if current owner matches.
    """
    lock_key = _lock_stat_name(lock_name)
    with get_session() as session:
        row = session.query(BotStat).filter(BotStat.stat_name == lock_key).first()
        if row is None:
            return False

        try:
            payload = json.loads(str(row.stat_value or "{}"))
        except json.JSONDecodeError:
            payload = {}
        current_owner = str(payload.get("owner", ""))
        if current_owner != owner:
            return False

        session.delete(row)
        return True


def get_distributed_lock_state(lock_name: str) -> dict[str, Any]:
    """
    Return distributed lock state for observability endpoints.
    """
    lock_key = _lock_stat_name(lock_name)
    now = datetime.utcnow()

    with get_session() as session:
        row = session.query(BotStat).filter(BotStat.stat_name == lock_key).first()
        if row is None:
            return {"locked": False, "owner": None, "expires_at": None}

        try:
            payload = json.loads(str(row.stat_value or "{}"))
        except json.JSONDecodeError:
            payload = {}

        owner = str(payload.get("owner") or "").strip() or None
        expires_at_raw = str(payload.get("expires_at") or "").strip()
        expires_at: datetime | None = None
        if expires_at_raw:
            with_expires = expires_at_raw.replace("Z", "+00:00")
            try:
                expires_at = datetime.fromisoformat(with_expires).replace(tzinfo=None)
            except ValueError:
                expires_at = None

        locked = bool(expires_at and expires_at > now and owner)
        return {
            "locked": locked,
            "owner": owner,
            "expires_at": expires_at.isoformat() if expires_at else None,
        }


def get_bot_stats_last_updated(stat_names: tuple[str, ...]) -> datetime | None:
    """Get max updated_at among selected bot stats."""
    if not stat_names:
        return None
    with get_session() as session:
        return (
            session.query(func.max(BotStat.updated_at))
            .filter(BotStat.stat_name.in_(stat_names))
            .scalar()
        )


def _build_special_tag_candidate_query(
    *,
    session,
    signal_type: str,
    target_timeframe: str,
    required_timeframes: tuple[str, ...],
    window_seconds: int,
    market_type: str | None = None,
    strategy: str | None = None,
    since_hours: int | None = None,
):
    target = aliased(Signal)
    query = session.query(target.id, target.special_tag).filter(
        target.signal_type == signal_type,
        target.timeframe == target_timeframe,
    )

    if market_type:
        query = query.filter(target.market_type == market_type)
    if strategy:
        query = query.filter(target.strategy == strategy)
    if since_hours is not None and since_hours > 0:
        since_dt = datetime.utcnow() - timedelta(hours=since_hours)
        query = query.filter(target.created_at >= since_dt)

    for timeframe in required_timeframes:
        if timeframe == target_timeframe:
            continue
        required = aliased(Signal)
        query = query.filter(
            session.query(required.id)
            .filter(
                required.symbol == target.symbol,
                required.market_type == target.market_type,
                required.strategy == target.strategy,
                required.signal_type == target.signal_type,
                required.timeframe == timeframe,
                func.abs(
                    func.strftime("%s", required.created_at)
                    - func.strftime("%s", target.created_at)
                )
                <= window_seconds,
            )
            .exists()
        )

    return query, target


def get_special_tag_coverage(
    since_hours: int | None = 24,
    market_type: str | None = "BIST",
    strategy: str | None = None,
    window_seconds: int = 900,
) -> list[dict[str, Any]]:
    """
    Return coverage stats for special tags.
    """
    rows: list[dict[str, Any]] = []
    strategies = (strategy,) if strategy else ("COMBO", "HUNTER")

    with get_session() as session:
        for strategy_name in strategies:
            for rule in SPECIAL_TAG_RULES:
                candidate_query, target_alias = _build_special_tag_candidate_query(
                    session=session,
                    signal_type=str(rule["signal_type"]),
                    target_timeframe=str(rule["target_timeframe"]),
                    required_timeframes=tuple(rule["required_timeframes"]),
                    window_seconds=window_seconds,
                    market_type=market_type,
                    strategy=strategy_name,
                    since_hours=since_hours,
                )
                candidates = int(candidate_query.count())
                tagged = int(
                    candidate_query.filter(target_alias.special_tag == str(rule["tag"])).count()
                )
                rows.append(
                    {
                        "tag": str(rule["tag"]),
                        "strategy": strategy_name,
                        "signal_type": str(rule["signal_type"]),
                        "target_timeframe": str(rule["target_timeframe"]),
                        "candidates": candidates,
                        "tagged": tagged,
                        "missing": max(0, candidates - tagged),
                    }
                )

    return rows


def get_trade_stats() -> dict[str, Any]:
    """Return trade stats summary."""
    with get_session() as session:
        total = int(session.query(func.count(Trade.id)).scalar() or 0)
        closed = int(
            session.query(func.count(Trade.id)).filter(Trade.status == "CLOSED").scalar() or 0
        )
        winners = int(
            session.query(func.count(Trade.id))
            .filter(Trade.status == "CLOSED", Trade.pnl > 0)
            .scalar()
            or 0
        )
        total_pnl = float(
            session.query(func.coalesce(func.sum(Trade.pnl), 0.0))
            .filter(Trade.status == "CLOSED")
            .scalar()
            or 0.0
        )
        win_rate = (winners / closed * 100.0) if closed > 0 else 0.0
        return {
            "total_trades": total,
            "closed_trades": closed,
            "winning_trades": winners,
            "total_pnl": total_pnl,
            "win_rate": win_rate,
        }


def get_active_orders(statuses: tuple[str, ...] = ACTIVE_ORDER_STATUSES) -> list[dict[str, Any]]:
    with get_session() as session:
        rows = (
            session.query(Order).filter(Order.status.in_(statuses)).order_by(Order.id.asc()).all()
        )
        return [row.to_dict() for row in rows]


def reconcile_active_orders_on_startup(stale_minutes: int = 180) -> dict[str, Any]:
    """
    Reconcile active orders at startup.

    - Marks stale active orders as STALE when they exceed stale_minutes.
    - Best-effort exchange check for crypto orders with Binance open-orders endpoint.
    """
    now = datetime.utcnow()
    stale_before = now - timedelta(minutes=max(1, int(stale_minutes)))
    summary: dict[str, Any] = {
        "checked": 0,
        "marked_stale": 0,
        "marked_unknown": 0,
        "exchange_sync_attempted": False,
        "exchange_errors": 0,
    }

    with get_session() as session:
        active_orders = (
            session.query(Order)
            .filter(Order.status.in_(ACTIVE_ORDER_STATUSES))
            .order_by(Order.id.asc())
            .all()
        )
        summary["checked"] = len(active_orders)

        for order in active_orders:
            updated_at = order.updated_at or order.created_at or now
            if updated_at <= stale_before:
                order.status = "STALE"
                order.closed_at = now
                session.add(order)
                summary["marked_stale"] += 1

        crypto_active_orders = [
            order
            for order in active_orders
            if str(order.market_type).strip().lower() in {"kripto", "crypto"}
            and order.exchange_order_id
            and order.status in ACTIVE_ORDER_STATUSES
        ]
        if not crypto_active_orders:
            return summary

        try:
            from binance.client import Client

            from settings import settings

            if not settings.binance_api_key or not settings.binance_secret_key:
                return summary

            summary["exchange_sync_attempted"] = True
            client = Client(settings.binance_api_key, settings.binance_secret_key)
            open_ids_by_symbol: dict[str, set[str]] = {}

            for symbol in sorted({str(order.symbol).upper() for order in crypto_active_orders}):
                try:
                    open_orders = client.get_open_orders(symbol=symbol)
                    open_ids_by_symbol[symbol] = {
                        str(row.get("orderId"))
                        for row in open_orders or []
                        if row.get("orderId") is not None
                    }
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Open order fetch failed during startup reconcile (%s): %s", symbol, exc
                    )
                    summary["exchange_errors"] += 1
                    open_ids_by_symbol[symbol] = set()

            for order in crypto_active_orders:
                symbol = str(order.symbol).upper()
                exchange_order_id = str(order.exchange_order_id)
                if exchange_order_id not in open_ids_by_symbol.get(symbol, set()):
                    order.status = "UNKNOWN"
                    order.closed_at = now
                    session.add(order)
                    summary["marked_unknown"] += 1

        except Exception as exc:  # noqa: BLE001
            logger.warning("Exchange reconciliation skipped: %s", exc)

    return summary


def get_recent_signals(limit: int = 20) -> list[dict[str, Any]]:
    """Return latest signal rows as dictionaries."""
    with get_session() as session:
        signals = session.query(Signal).order_by(Signal.created_at.desc()).limit(limit).all()
        return [signal.to_dict() for signal in signals]
