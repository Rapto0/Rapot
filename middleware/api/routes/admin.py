from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from middleware.api.dependencies import get_service, require_admin_enabled
from middleware.domain.enums import OrderStatus, Side
from middleware.domain.events import (
    OrderItem,
    ProcessSignalResponse,
    ReplaySignalRequest,
    SimulateFillRequest,
)
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


@router.post("/simulate-fill", response_model=OrderItem)
def simulate_fill(
    request: SimulateFillRequest,
    _: Annotated[None, Depends(require_admin_enabled)],
    service: Annotated[TradingService, Depends(get_service)],
) -> OrderItem:
    try:
        row = service.simulate_fill(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"simulate-fill failed: {exc}",
        ) from exc

    return OrderItem(
        id=row.id,
        signal_event_id=row.signal_event_id,
        idempotency_key=row.idempotency_key,
        symbol=row.symbol,
        side=Side(row.side),
        signal_code=row.signal_code,
        requested_lots=row.requested_lots,
        filled_lots=row.filled_lots,
        requested_quantity=row.requested_quantity,
        filled_quantity=row.filled_quantity,
        limit_price=row.limit_price,
        budget_tl=row.budget_tl,
        quote_budget=row.quote_budget,
        status=OrderStatus(row.status),
        rejection_reason=row.rejection_reason,
        broker_name=row.broker_name,
        broker_order_id=row.broker_order_id,
        base_asset=row.base_asset,
        quote_asset=row.quote_asset,
        target_tranche_id=row.target_tranche_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        realized_pnl=row.realized_pnl,
    )
