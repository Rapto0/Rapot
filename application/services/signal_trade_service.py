from __future__ import annotations

from typing import Any

from infrastructure.repositories.signal_trade_repository import (
    get_trade_stats_aggregate as repo_get_trade_stats_aggregate,
)
from infrastructure.repositories.signal_trade_repository import list_trades as repo_list_trades


def list_trades(*, symbol: str | None, status: str | None, limit: int) -> list[dict[str, Any]]:
    trades = repo_list_trades(symbol=symbol, status=status, limit=limit)

    return [
        {
            "id": t.id,
            "symbol": t.symbol,
            "market_type": t.market_type,
            "direction": t.direction,
            "price": t.price,
            "quantity": t.quantity,
            "pnl": t.pnl,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in trades
    ]


def get_trade_stats_summary() -> dict[str, int | float]:
    stats = repo_get_trade_stats_aggregate()
    closed_trades = int(stats["closed_trades"])
    winning_trades = int(stats["winning_trades"])
    win_rate = (winning_trades / closed_trades * 100) if closed_trades > 0 else 0.0

    return {
        "total_trades": int(stats["total_trades"]),
        "open_trades": int(stats["open_trades"]),
        "closed_trades": closed_trades,
        "total_pnl": float(stats["total_pnl"]),
        "win_rate": round(float(win_rate), 2),
    }
