"""
Signal persistence helpers backed by SQLAlchemy models/session.

This module is used by scanners to avoid writing through legacy `database.py`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.exc import IntegrityError

from db_session import get_session
from models import Signal


def save_signal(
    symbol: str,
    market_type: str,
    strategy: str,
    signal_type: str,
    timeframe: str,
    score: str = "",
    price: float = 0.0,
    special_tag: str | None = None,
    details: str = "",
) -> int:
    """
    Persist a signal row and return its id.

    Returns 0 when the insert is ignored due to a uniqueness conflict.
    """
    try:
        with get_session() as session:
            signal = Signal(
                symbol=symbol,
                market_type=market_type,
                strategy=strategy,
                signal_type=signal_type,
                timeframe=timeframe,
                score=score,
                price=float(price),
                special_tag=special_tag,
                details=details,
            )
            session.add(signal)
            session.flush()
            return int(signal.id or 0)
    except IntegrityError:
        return 0


def set_signal_special_tag(
    symbol: str,
    market_type: str,
    strategy: str,
    signal_type: str,
    timeframe: str,
    special_tag: str,
    within_seconds: int = 900,
) -> bool:
    """
    Write special_tag to the latest matching signal row.
    """
    with get_session() as session:
        signal = (
            session.query(Signal)
            .filter(
                Signal.symbol == symbol,
                Signal.market_type == market_type,
                Signal.strategy == strategy,
                Signal.signal_type == signal_type,
                Signal.timeframe == timeframe,
            )
            .order_by(Signal.id.desc())
            .first()
        )

        if signal is None:
            return False

        if signal.created_at is not None and within_seconds > 0:
            age_seconds = abs((datetime.utcnow() - signal.created_at).total_seconds())
            if age_seconds > within_seconds:
                return False

        signal.special_tag = special_tag
        session.add(signal)
        session.flush()
        return True
