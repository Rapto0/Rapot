"""
Shared health payload contract for FastAPI and Flask health endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def format_uptime(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def build_health_payload(
    *,
    status: str,
    uptime_seconds: float,
    database: str,
    realtime: str,
    version: str,
) -> dict[str, Any]:
    return {
        "status": status,
        "uptime_seconds": round(float(uptime_seconds), 2),
        "uptime_human": format_uptime(float(uptime_seconds)),
        "database": database,
        "realtime": realtime,
        "version": version,
        "timestamp": datetime.now().isoformat(),
    }
