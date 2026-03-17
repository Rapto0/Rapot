import os

from fastapi import APIRouter, Request

from api.rate_limit import limiter

router = APIRouter(tags=["System"])


@router.get("/scans")
@limiter.limit("30/minute")
async def get_scan_history(request: Request, limit: int = 10):
    from db_session import get_session
    from models import ScanHistory

    with get_session() as session:
        scans = session.query(ScanHistory).order_by(ScanHistory.created_at.desc()).limit(limit).all()
        return [scan.to_dict() for scan in scans]


@router.get("/logs")
@limiter.limit("30/minute")
async def get_system_logs(request: Request, limit: int = 50):
    try:
        log_path = "logs/trading_bot.log"
        if not os.path.exists(log_path):
            return []

        with open(log_path, encoding="utf-8") as f:
            lines = f.readlines()
            last_lines = lines[-limit:]

        logs = []
        for line in last_lines:
            parts = line.split(" | ")
            if len(parts) >= 3:
                logs.append(
                    {
                        "timestamp": parts[0],
                        "level": parts[1].strip(),
                        "message": " | ".join(parts[2:]).strip(),
                    }
                )
            else:
                logs.append({"timestamp": "", "level": "INFO", "message": line.strip()})

        return list(reversed(logs))
    except Exception as e:
        print(f"Log error: {e}")
        return []
