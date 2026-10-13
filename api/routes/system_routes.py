import os

from fastapi import APIRouter, Depends, Query, Request

from api.auth import get_current_admin_user
from api.rate_limit import limiter
from logger import get_logger

router = APIRouter(tags=["System"])
logger = get_logger(__name__)


@router.get("/logs", dependencies=[Depends(get_current_admin_user)])
@limiter.limit("30/minute")
async def get_system_logs(request: Request, limit: int = Query(50, ge=1, le=500)):
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
    except Exception:
        logger.exception("System log retrieval failed.")
        return []
