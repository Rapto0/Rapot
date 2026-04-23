from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from middleware.domain.events import HealthResponse
from middleware.infra.settings import settings
from middleware.infra.time import UTC

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        now=datetime.now(UTC),
        trading_enabled=settings.trading_enabled,
        execution_mode=settings.execution_mode.value,
        broker=settings.broker_name.value,
    )
