from __future__ import annotations

from typing import Any


def list_scan_history(limit: int) -> list[dict[str, Any]]:
    from db_session import get_session
    from models import ScanHistory

    with get_session() as session:
        scans = (
            session.query(ScanHistory).order_by(ScanHistory.created_at.desc()).limit(limit).all()
        )
        return [scan.to_dict() for scan in scans]
