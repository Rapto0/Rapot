from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from middleware.broker_adapters.factory import build_broker_client
from middleware.infra.db import get_db_session
from middleware.infra.settings import settings
from middleware.services.osmanli_proxy_service import OsmanliProxyService
from middleware.services.trading_service import TradingService


def get_settings():
    return settings


def get_service(session: Annotated[Session, Depends(get_db_session)]) -> TradingService:
    return TradingService(
        session=session,
        cfg=settings,
        broker_client=build_broker_client(settings),
    )


def get_osmanli_proxy_service(
    service: Annotated[TradingService, Depends(get_service)],
) -> OsmanliProxyService:
    return OsmanliProxyService(cfg=settings, trading_service=service)


def require_admin_enabled() -> None:
    if not settings.allow_admin_endpoints:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="admin endpoints disabled"
        )


def verify_webhook_auth(
    x_webhook_token: Annotated[str | None, Header(alias="X-Webhook-Token")] = None,
    token: Annotated[str | None, Query(alias="token")] = None,
) -> None:
    if not settings.require_webhook_auth:
        return

    # TradingView cannot set arbitrary custom headers.
    # Allow query token fallback: /webhooks/tradingview?token=...
    provided = x_webhook_token or token
    expected = settings.webhook_auth_token
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="server misconfigured: MW_WEBHOOK_AUTH_TOKEN is not set",
        )
    if provided is None or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid webhook token"
        )
