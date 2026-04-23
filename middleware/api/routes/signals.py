from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from middleware.api.dependencies import get_service
from middleware.domain.enums import Side
from middleware.domain.events import SignalItem
from middleware.services.trading_service import TradingService

router = APIRouter(tags=["signals"])


@router.get("/signals", response_model=list[SignalItem])
def list_signals(
    service: Annotated[TradingService, Depends(get_service)],
    symbol: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[SignalItem]:
    rows = service.list_signals(limit=limit, symbol=symbol)
    return [
        SignalItem(
            id=row.id,
            event_hash=row.event_hash,
            source=row.source,
            symbol=row.symbol,
            ticker=row.ticker,
            signal_code=row.signal_code,
            signal_text=row.signal_text,
            side=Side(row.side),
            price=row.price,
            timeframe=row.timeframe,
            bar_time=row.bar_time,
            bar_index=row.bar_index,
            is_realtime=row.is_realtime,
            received_at=row.received_at,
        )
        for row in rows
    ]
