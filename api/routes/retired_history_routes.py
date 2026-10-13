"""Authenticated tombstones for the removed automatic signal/scan archive."""

from fastapi import APIRouter, Depends, HTTPException

from api.auth import get_current_admin_user

router = APIRouter(dependencies=[Depends(get_current_admin_user)], include_in_schema=False)
RETIRED_PATHS = (
    "/signals",
    "/signals/{signal_id}",
    "/signals/{signal_id}/analysis",
    "/scans",
    "/ops/special-tag-health",
    "/ops/read-model/overview",
    "/ops/read-model/scanner-feed",
)


async def retired_history():
    """Do not read, count or expose the retired archive, including before cleanup."""
    raise HTTPException(
        status_code=410,
        detail="Eski otomatik sinyal ve tarama geçmişi kaldırıldı. Sunucu alarmlarını kullanın.",
    )


for path in RETIRED_PATHS:
    router.add_api_route(path, retired_history, methods=["GET"])
