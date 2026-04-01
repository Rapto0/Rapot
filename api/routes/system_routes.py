import os

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from api.rate_limit import limiter
from logger import get_logger

router = APIRouter(tags=["System"])
logger = get_logger(__name__)


class CompatibilityWrapperUsageItemResponse(BaseModel):
    wrapper_module: str
    canonical_module: str
    usage_count: int
    planned_removal: str
    first_seen_at: str | None
    last_seen_at: str | None


class CompatibilityWrapperTelemetryResponse(BaseModel):
    total_wrappers: int
    active_wrappers: int
    total_import_events: int
    planned_removal_buckets: dict[str, int]
    details_requested: bool
    details_included: bool
    details_hidden_reason: str | None = None
    wrappers: list[CompatibilityWrapperUsageItemResponse] | None = None


class OpsOverviewReadModelResponse(BaseModel):
    total_signals: int
    total_trades: int
    open_trades: int
    total_scans: int
    total_pnl: float
    last_signal_at: str | None
    last_trade_at: str | None
    last_scan_at: str | None
    compatibility_wrappers: CompatibilityWrapperTelemetryResponse | None = None


class ScannerActivityItemResponse(BaseModel):
    item_type: str
    item_id: str
    symbol: str | None
    market_type: str | None
    strategy: str | None
    action: str | None
    timeframe: str | None
    status: str | None
    numeric_value: float | None
    created_at: str | None


@router.get("/scans")
@limiter.limit("30/minute")
async def get_scan_history(request: Request, limit: int = 10):
    from application.services.system_service import list_recent_scans

    return list_recent_scans(limit)


@router.get("/ops/read-model/overview", response_model=OpsOverviewReadModelResponse)
@limiter.limit("60/minute")
async def get_ops_overview_read_model(
    request: Request,
    include_compat_telemetry: bool = Query(
        False,
        description="Include compatibility wrapper telemetry summary in response.",
    ),
    include_wrapper_details: bool = Query(
        False,
        description="Include per-wrapper details (disabled in production env).",
    ),
):
    from application.services.system_service import get_ops_overview

    return OpsOverviewReadModelResponse(
        **get_ops_overview(
            include_compat_telemetry=include_compat_telemetry,
            include_wrapper_details=include_wrapper_details,
        )
    )


@router.get("/ops/read-model/scanner-feed", response_model=list[ScannerActivityItemResponse])
@limiter.limit("60/minute")
async def get_scanner_activity_read_model(request: Request, limit: int = 100):
    from application.services.system_service import list_scanner_activity

    rows = list_scanner_activity(limit=limit)
    return [ScannerActivityItemResponse(**row) for row in rows]


@router.get("/logs")
@limiter.limit("30/minute")
async def get_system_logs(request: Request, limit: int = 50):
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
