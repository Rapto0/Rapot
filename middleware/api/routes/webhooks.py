from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

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
    OsmanliForwardError,
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
async def ingest_osmanli_proxy_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    _: Annotated[None, Depends(verify_webhook_auth)],
    proxy_service: Annotated[OsmanliProxyService, Depends(get_osmanli_proxy_service)],
) -> OsmanliProxyResponse:
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="invalid JSON payload") from exc

    try:
        return proxy_service.process_shadow(
            payload,
            raw_body=raw_body,
            background_tasks=background_tasks,
        )
    except OsmanliProxyPayloadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OsmanliForwardError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Osmanli forward failed: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"failed to process Osmanli proxy payload: {exc}",
        ) from exc
