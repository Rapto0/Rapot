from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from middleware.api.dependencies import get_service, require_admin_enabled, verify_admin_auth
from middleware.domain.events import (
    ProcessSignalResponse,
    ReconciliationReport,
    ReplaySignalRequest,
)
from middleware.infra.logging import get_logger
from middleware.services.trading_service import TradingService

logger = get_logger(__name__)
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_enabled), Depends(verify_admin_auth)],
)


@router.post("/replay-signal", response_model=ProcessSignalResponse)
def replay_signal(
    request: ReplaySignalRequest,
    service: Annotated[TradingService, Depends(get_service)],
) -> ProcessSignalResponse:
    try:
        return service.replay_signal(
            request.payload,
            bypass_idempotency=request.bypass_idempotency,
        )
    except Exception as exc:
        logger.error("Admin replay failed (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="replay failed",
        ) from exc


@router.get("/reconcile/{symbol}", response_model=ReconciliationReport)
def reconcile_symbol(
    symbol: str,
    service: Annotated[TradingService, Depends(get_service)],
) -> ReconciliationReport:
    try:
        return ReconciliationReport(**service.reconcile_symbol(symbol))
    except Exception as exc:
        logger.error("Admin reconciliation failed (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="reconciliation failed",
        ) from exc
