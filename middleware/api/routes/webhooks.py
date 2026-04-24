from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from middleware.api.dependencies import (
    get_osmanli_proxy_service,
    get_service,
    verify_webhook_auth,
)
from middleware.domain.events import (
    OsmanliProxyResponse,
    ProcessSignalResponse,
    TradingViewWebhookPayload,
)
from middleware.services.osmanli_proxy_service import (
    OsmanliProxyPayloadError,
    OsmanliProxyService,
)
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


@router.post("/tradingview/osmanli-proxy", response_model=OsmanliProxyResponse)
def ingest_osmanli_proxy_webhook(
    payload: dict[str, Any],
    _: Annotated[None, Depends(verify_webhook_auth)],
    proxy_service: Annotated[OsmanliProxyService, Depends(get_osmanli_proxy_service)],
) -> OsmanliProxyResponse:
    try:
        return proxy_service.process_shadow(payload)
    except OsmanliProxyPayloadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"failed to process Osmanli proxy payload: {exc}",
        ) from exc
