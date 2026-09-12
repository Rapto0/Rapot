from __future__ import annotations

from typing import Any

from sqlalchemy import text


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

    with get_session() as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM signals) AS total_signals,
                        (SELECT COUNT(*) FROM trades) AS total_trades,
                        (SELECT COUNT(*) FROM trades WHERE status = 'OPEN') AS open_trades,
                        (SELECT COALESCE(SUM(pnl), 0) FROM trades WHERE status = 'CLOSED') AS total_pnl,
                        (SELECT COUNT(*) FROM trades WHERE status = 'CLOSED') AS closed_trades,
                        (SELECT COUNT(*) FROM trades WHERE status = 'CLOSED' AND pnl > 0) AS winning_trades
                    """
                )
            )
            .mappings()
            .first()
            or {}
        )

    return {
        "total_signals": int(row.get("total_signals") or 0),
        "total_trades": int(row.get("total_trades") or 0),
        "open_trades": int(row.get("open_trades") or 0),
        "total_pnl": float(row.get("total_pnl") or 0.0),
        "closed_trades": int(row.get("closed_trades") or 0),
        "winning_trades": int(row.get("winning_trades") or 0),
    }
