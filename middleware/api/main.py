from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from middleware.api.routes.admin import router as admin_router
from middleware.api.routes.health import router as health_router
from middleware.api.routes.orders import router as orders_router
from middleware.api.routes.positions import router as positions_router
from middleware.api.routes.signals import router as signals_router
from middleware.api.routes.webhooks import router as webhooks_router
from middleware.infra.db import init_db
from middleware.infra.logging import configure_logging, get_logger
from middleware.infra.settings import settings

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_runtime_configuration()
    init_db()
    logger.info(
        "middleware started",
        extra={
            "extra_fields": {
                "app": settings.app_name,
                "mode": settings.execution_mode.value,
                "broker": settings.broker_name.value,
                "trading_enabled": settings.trading_enabled,
            }
        },
    )
    yield


app = FastAPI(
    title="Rapot Trading Middleware",
    version="0.1.0",
    description="TradingView -> middleware -> broker execution service for BIST spot equities.",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(webhooks_router)
app.include_router(positions_router)
app.include_router(orders_router)
app.include_router(signals_router)
app.include_router(admin_router)
