from __future__ import annotations

from typing import Any

from sqlalchemy import text


def list_scan_history(limit: int) -> list[dict[str, Any]]:
    from db_session import get_session
    from models import ScanHistory

    with get_session() as session:
        scans = (
            session.query(ScanHistory).order_by(ScanHistory.created_at.desc()).limit(limit).all()
        )
        return [scan.to_dict() for scan in scans]


def get_ops_overview_read_model() -> dict[str, Any]:
    """
    Return dashboard-focused aggregate metrics using a single SQL round-trip.
    """
    from db_session import get_session

    query = text(
        """
        SELECT
            (SELECT COUNT(*) FROM signals) AS total_signals,
            (SELECT COUNT(*) FROM trades) AS total_trades,
            (SELECT COUNT(*) FROM trades WHERE status = 'OPEN') AS open_trades,
            (SELECT COUNT(*) FROM scan_history) AS total_scans,
            (SELECT COALESCE(SUM(pnl), 0) FROM trades WHERE status = 'CLOSED') AS total_pnl,
            (SELECT MAX(created_at) FROM signals) AS last_signal_at,
            (SELECT MAX(created_at) FROM trades) AS last_trade_at,
            (SELECT MAX(created_at) FROM scan_history) AS last_scan_at
        """
    )

    with get_session() as session:
        row = session.execute(query).mappings().first() or {}

    return {
        "total_signals": int(row.get("total_signals") or 0),
        "total_trades": int(row.get("total_trades") or 0),
        "open_trades": int(row.get("open_trades") or 0),
        "total_scans": int(row.get("total_scans") or 0),
        "total_pnl": float(row.get("total_pnl") or 0.0),
        "last_signal_at": _iso_or_none(row.get("last_signal_at")),
        "last_trade_at": _iso_or_none(row.get("last_trade_at")),
        "last_scan_at": _iso_or_none(row.get("last_scan_at")),
    }


def list_scanner_activity_projection(limit: int) -> list[dict[str, Any]]:
    """
    Return a unified timeline for signals, trades and scans.
    """
    from db_session import get_session

    query = text(
        """
        SELECT *
        FROM (
            SELECT
                'signal' AS item_type,
                CAST(id AS TEXT) AS item_id,
                symbol,
                market_type,
                strategy,
                signal_type AS action,
                timeframe,
                NULL AS status,
                price AS numeric_value,
                created_at
            FROM signals

            UNION ALL

            SELECT
                'trade' AS item_type,
                CAST(id AS TEXT) AS item_id,
                symbol,
                market_type,
                NULL AS strategy,
                direction AS action,
                NULL AS timeframe,
                status,
                pnl AS numeric_value,
                created_at
            FROM trades

            UNION ALL

            SELECT
                'scan' AS item_type,
                CAST(id AS TEXT) AS item_id,
                NULL AS symbol,
                NULL AS market_type,
                mode AS strategy,
                scan_type AS action,
                NULL AS timeframe,
                NULL AS status,
                duration_seconds AS numeric_value,
                created_at
            FROM scan_history
        ) merged
        ORDER BY created_at DESC
        LIMIT :limit
        """
    )

    with get_session() as session:
        rows = session.execute(query, {"limit": max(1, int(limit))}).mappings().all()

    return [
        {
            "item_type": str(row.get("item_type") or ""),
            "item_id": str(row.get("item_id") or ""),
            "symbol": row.get("symbol"),
            "market_type": row.get("market_type"),
            "strategy": row.get("strategy"),
            "action": row.get("action"),
            "timeframe": row.get("timeframe"),
            "status": row.get("status"),
            "numeric_value": float(row.get("numeric_value"))
            if row.get("numeric_value") is not None
            else None,
            "created_at": _iso_or_none(row.get("created_at")),
        }
        for row in rows
    ]


def _iso_or_none(value: Any) -> str | None:
    if value is None:
        return None
    iso_func = getattr(value, "isoformat", None)
    if callable(iso_func):
        return str(iso_func())
    return str(value)
