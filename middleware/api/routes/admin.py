from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from middleware.api.dependencies import get_service, require_admin_enabled
from middleware.domain.events import ProcessSignalResponse, ReplaySignalRequest
from middleware.services.trading_service import TradingService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/replay-signal", response_model=ProcessSignalResponse)
def replay_signal(
    request: ReplaySignalRequest,
    _: Annotated[None, Depends(require_admin_enabled)],
    service: Annotated[TradingService, Depends(get_service)],
) -> ProcessSignalResponse:
    try:
        return service.replay_signal(
            request.payload,
            bypass_idempotency=request.bypass_idempotency,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"replay failed: {exc}",
        ) from exc
