from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from middleware.api.dependencies import get_service, verify_webhook_auth
from middleware.domain.events import ProcessSignalResponse, TradingViewWebhookPayload
from middleware.services.trading_service import TradingService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/tradingview", response_model=ProcessSignalResponse)
def ingest_tradingview_webhook(
    payload: TradingViewWebhookPayload,
    _: Annotated[None, Depends(verify_webhook_auth)],
    service: Annotated[TradingService, Depends(get_service)],
) -> ProcessSignalResponse:
    try:
        return service.process_webhook(payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"failed to process signal: {exc}",
        ) from exc
