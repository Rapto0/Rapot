from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from middleware.api.dependencies import get_service
from middleware.domain.enums import OrderStatus, Side
from middleware.domain.events import OrderItem
from middleware.services.trading_service import TradingService

router = APIRouter(tags=["orders"])


@router.get("/orders", response_model=list[OrderItem])
def list_orders(
    service: Annotated[TradingService, Depends(get_service)],
    symbol: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[OrderItem]:
    rows = service.list_orders(limit=limit, symbol=symbol)
    return [
        OrderItem(
            id=row.id,
            signal_event_id=row.signal_event_id,
            idempotency_key=row.idempotency_key,
            symbol=row.symbol,
            side=Side(row.side),
            signal_code=row.signal_code,
            requested_lots=row.requested_lots,
            filled_lots=row.filled_lots,
            limit_price=row.limit_price,
            budget_tl=row.budget_tl,
            status=OrderStatus(row.status),
            rejection_reason=row.rejection_reason,
            broker_name=row.broker_name,
            broker_order_id=row.broker_order_id,
            target_tranche_id=row.target_tranche_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            realized_pnl=row.realized_pnl,
        )
        for row in rows
    ]
