from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from middleware.api.dependencies import get_service
from middleware.domain.enums import TrancheStatus
from middleware.domain.events import PositionItem, TrancheItem
from middleware.services.trading_service import TradingService

router = APIRouter(tags=["positions"])


@router.get("/positions", response_model=list[PositionItem])
def list_positions(
    service: Annotated[TradingService, Depends(get_service)],
) -> list[PositionItem]:
    rows = service.list_positions()
    return [PositionItem(**row) for row in rows]


@router.get("/positions/{symbol}")
def get_position(
    symbol: str,
    service: Annotated[TradingService, Depends(get_service)],
) -> dict[str, Any]:
    normalized = symbol.upper()
    positions = service.list_positions(symbol=normalized)
    if not positions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="position not found")

    tranches = service.list_tranches(symbol=normalized)
    return {
        "position": PositionItem(**positions[0]),
        "tranches": [
            TrancheItem(
                id=t.id,
                symbol=t.symbol,
                signal_code=t.signal_code,
                entry_price=t.entry_price,
                entry_time=t.entry_time,
                requested_lots=t.requested_lots,
                filled_lots=t.filled_lots,
                remaining_lots=t.remaining_lots,
                requested_quantity=t.requested_quantity,
                filled_quantity=t.filled_quantity,
                remaining_quantity=t.remaining_quantity,
                status=TrancheStatus(t.status),
                open_order_id=t.open_order_id,
                close_order_id=t.close_order_id,
            )
            for t in tranches
        ],
    }
