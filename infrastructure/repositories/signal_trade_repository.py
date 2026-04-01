from __future__ import annotations

from typing import Any

from sqlalchemy import func


def list_signals(
    *,
    symbol: str | None,
    strategy: str | None,
    signal_type: str | None,
    market_type: str | None,
    special_tag: str | None,
    limit: int,
) -> list[Any]:
    from db_session import get_session
    from models import Signal

    with get_session() as session:
        query = session.query(Signal)

        if symbol:
            query = query.filter(Signal.symbol == symbol.upper())
        if strategy:
            query = query.filter(Signal.strategy == strategy.upper())
        if signal_type:
            query = query.filter(Signal.signal_type == signal_type.upper())
        if market_type:
            query = query.filter(Signal.market_type == market_type)
        if special_tag:
            query = query.filter(Signal.special_tag == special_tag)

        return query.order_by(Signal.created_at.desc()).limit(limit).all()


def get_signal_by_id(signal_id: int) -> Any | None:
    from db_session import get_session
    from models import Signal

    with get_session() as session:
        return session.query(Signal).filter(Signal.id == signal_id).first()


def list_trades(*, symbol: str | None, status: str | None, limit: int) -> list[Any]:
    from db_session import get_session
    from models import Trade

    with get_session() as session:
        query = session.query(Trade)

        if symbol:
            query = query.filter(Trade.symbol == symbol.upper())
        if status:
            query = query.filter(Trade.status == status.upper())

        return query.order_by(Trade.created_at.desc()).limit(limit).all()


def get_trade_stats_aggregate() -> dict[str, int | float]:
    from db_session import get_session
    from models import Signal, Trade

    with get_session() as session:
        total_signals = int(session.query(Signal).count())
        total_trades = int(session.query(Trade).count())
        open_trades = int(session.query(Trade).filter(Trade.status == "OPEN").count())

        total_pnl = (
            session.query(func.sum(Trade.pnl)).filter(Trade.status == "CLOSED").scalar() or 0.0
        )

        closed_trades = int(session.query(Trade).filter(Trade.status == "CLOSED").count())
        winning_trades = int(
            session.query(Trade).filter(Trade.status == "CLOSED", Trade.pnl > 0).count()
        )

    return {
        "total_signals": total_signals,
        "total_trades": total_trades,
        "open_trades": open_trades,
        "total_pnl": float(total_pnl),
        "closed_trades": closed_trades,
        "winning_trades": winning_trades,
    }
