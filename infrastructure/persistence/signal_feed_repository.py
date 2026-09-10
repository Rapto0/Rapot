"""Bounded reads of committed signals shared by the bot and the API process.

This is a create-event feed, not an outbox: subsequent tag/analysis updates are
reconciled by the client's REST refresh. Reads never hold a session across awaits.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func

from db_session import get_session
from models import Signal


@dataclass(frozen=True)
class SignalFeedBatch:
    max_id: int
    signals: list[dict[str, Any]]


def _utc_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def get_signal_feed_max_id() -> int:
    with get_session() as session:
        return int(session.query(func.max(Signal.id)).scalar() or 0)


def read_signal_feed_batch(*, after_id: int, limit: int) -> SignalFeedBatch:
    if after_id < 0 or not 1 <= limit <= 1000:
        raise ValueError("Invalid signal feed cursor or batch size")
    with get_session() as session:
        max_id = int(session.query(func.max(Signal.id)).scalar() or 0)
        # Keep the batch bounded by the observed high watermark even if another
        # connection commits between these SELECTs. Newer rows belong to the next poll.
        rows = (
            session.query(Signal)
            .filter(Signal.id > after_id, Signal.id <= max_id)
            .order_by(Signal.id.asc())
            .limit(limit)
            .all()
        )
        return SignalFeedBatch(
            max_id=max_id,
            signals=[
                {
                    "id": row.id,
                    "symbol": row.symbol,
                    "marketType": row.market_type,
                    "strategy": row.strategy,
                    "signalType": row.signal_type,
                    "timeframe": row.timeframe,
                    "score": row.score or "",
                    "price": float(row.price or 0),
                    "createdAt": _utc_timestamp(row.created_at),
                    "specialTag": row.special_tag,
                }
                for row in rows
            ],
        )
