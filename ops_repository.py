"""
Operational data-access helpers backed by SQLAlchemy.

This module centralizes health/special-tag/stat queries so callers do not need
to use legacy sqlite3 helpers directly.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import aliased

from db_session import get_session
from models import BotStat, Signal, Trade

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


def get_recent_signals(limit: int = 20) -> list[dict[str, Any]]:
    """Return latest signal rows as dictionaries."""
    with get_session() as session:
        signals = session.query(Signal).order_by(Signal.created_at.desc()).limit(limit).all()
        return [signal.to_dict() for signal in signals]
