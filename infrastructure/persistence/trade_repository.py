"""
Trade persistence helpers backed by SQLAlchemy models/session.

This module is the primary data-access path for trade lifecycle operations.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func

from db_session import get_session
from models import Trade


def create_trade(
    *,
    symbol: str,
    market_type: str,
    direction: str,
    price: float,
    quantity: float,
    signal_id: int | None = None,
    status: str = "OPEN",
) -> int:
    with get_session() as session:
        trade = Trade(
            symbol=symbol,
            market_type=market_type,
            direction=direction,
            price=float(price),
            quantity=float(quantity),
            signal_id=signal_id,
            status=status,
        )
        session.add(trade)
        session.flush()
        return int(trade.id or 0)


def get_trade(trade_id: int) -> dict[str, Any] | None:
    with get_session() as session:
        trade = session.query(Trade).filter(Trade.id == trade_id).first()
        return trade.to_dict() if trade else None


def close_trade(trade_id: int, close_price: float) -> dict[str, Any] | None:
    with get_session() as session:
        trade = session.query(Trade).filter(Trade.id == trade_id).first()
        if trade is None or trade.status != "OPEN":
            return None

        trade.close(close_price)
        session.add(trade)
        session.flush()
        return trade.to_dict()


def list_open_trades(symbol: str | None = None) -> list[dict[str, Any]]:
    with get_session() as session:
        query = session.query(Trade).filter(Trade.status == "OPEN")
        if symbol:
            query = query.filter(Trade.symbol == symbol)
        trades = query.order_by(Trade.created_at.desc()).all()
        return [trade.to_dict() for trade in trades]


def list_trades(symbol: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    with get_session() as session:
        query = session.query(Trade)
        if symbol:
            query = query.filter(Trade.symbol == symbol)
        trades = query.order_by(Trade.created_at.desc()).limit(max(1, int(limit))).all()
        return [trade.to_dict() for trade in trades]


def get_trade_stats() -> dict[str, Any]:
    with get_session() as session:
        total_trades = int(session.query(Trade).count())
        open_trades = int(session.query(Trade).filter(Trade.status == "OPEN").count())
        closed_trades = int(session.query(Trade).filter(Trade.status == "CLOSED").count())
        winning_trades = int(
            session.query(Trade).filter(Trade.status == "CLOSED", Trade.pnl > 0).count()
        )
        total_pnl = (
            session.query(func.sum(Trade.pnl)).filter(Trade.status == "CLOSED").scalar() or 0.0
        )
        win_rate = (winning_trades / closed_trades * 100.0) if closed_trades else 0.0

    return {
        "total_trades": total_trades,
        "open_trades": open_trades,
        "closed_trades": closed_trades,
        "winning_trades": winning_trades,
        "win_rate": round(float(win_rate), 2),
        "total_pnl": float(total_pnl),
    }


def get_best_trade() -> dict[str, Any] | None:
    with get_session() as session:
        trade = (
            session.query(Trade).filter(Trade.status == "CLOSED").order_by(Trade.pnl.desc()).first()
        )
        if trade is None:
            return None
        return {"symbol": trade.symbol, "pnl": float(trade.pnl)}


def get_worst_trade() -> dict[str, Any] | None:
    with get_session() as session:
        trade = (
            session.query(Trade).filter(Trade.status == "CLOSED").order_by(Trade.pnl.asc()).first()
        )
        if trade is None:
            return None
        return {"symbol": trade.symbol, "pnl": float(trade.pnl)}


def get_average_closed_trade_pnl() -> float:
    with get_session() as session:
        avg_pnl = session.query(func.avg(Trade.pnl)).filter(Trade.status == "CLOSED").scalar()
        return float(avg_pnl or 0.0)
