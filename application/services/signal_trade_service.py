from __future__ import annotations

from typing import Any

from infrastructure.repositories.signal_trade_repository import (
    get_signal_by_id as repo_get_signal_by_id,
)
from infrastructure.repositories.signal_trade_repository import (
    get_trade_stats_aggregate as repo_get_trade_stats_aggregate,
)
from infrastructure.repositories.signal_trade_repository import list_signals as repo_list_signals
from infrastructure.repositories.signal_trade_repository import list_trades as repo_list_trades


def list_signals(
    *,
    symbol: str | None,
    strategy: str | None,
    signal_type: str | None,
    market_type: str | None,
    special_tag: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    signals = repo_list_signals(
        symbol=symbol,
        strategy=strategy,
        signal_type=signal_type,
        market_type=market_type,
        special_tag=special_tag,
        limit=limit,
    )

    return [
        {
            "id": s.id,
            "symbol": s.symbol,
            "market_type": s.market_type,
            "strategy": s.strategy,
            "signal_type": s.signal_type,
            "timeframe": s.timeframe,
            "score": s.score,
            "price": s.price,
            "created_at": s.created_at.isoformat() + "Z" if s.created_at else None,
            "special_tag": s.special_tag,
            "details": s.details,
        }
        for s in signals
    ]


def get_signal_by_id(signal_id: int) -> dict[str, Any] | None:
    signal = repo_get_signal_by_id(signal_id)
    if not signal:
        return None

    return {
        "id": signal.id,
        "symbol": signal.symbol,
        "market_type": signal.market_type,
        "strategy": signal.strategy,
        "signal_type": signal.signal_type,
        "timeframe": signal.timeframe,
        "score": signal.score,
        "price": signal.price,
        "created_at": signal.created_at.isoformat() if signal.created_at else None,
        "special_tag": signal.special_tag,
        "details": signal.details,
    }


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

    try:
        from market_scanner import get_scan_count

        scan_count = get_scan_count()
    except Exception:
        scan_count = 0

    return {
        "total_signals": int(stats["total_signals"]),
        "total_trades": int(stats["total_trades"]),
        "open_trades": int(stats["open_trades"]),
        "total_pnl": float(stats["total_pnl"]),
        "win_rate": round(float(win_rate), 2),
        "scan_count": int(scan_count),
    }
