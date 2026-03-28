from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel

from api.calendar_service import calendar_service

router = APIRouter(tags=["Calendar"])


class CalendarEventResponse(BaseModel):
    country: str | None = None
    event: str | None = None
    impact: str | None = None
    time: str | None = None
    actual: float | int | str | None = None
    estimate: float | int | str | None = None
    previous: float | int | str | None = None
    unit: str | None = None
    currency: str | None = None
    timestamp: str | None = None


def _normalize_events(raw_events: list[dict]) -> list[CalendarEventResponse]:
    normalized: list[CalendarEventResponse] = []
    for item in raw_events:
        value = dict(item)
        if not value.get("timestamp"):
            value["timestamp"] = datetime.now().isoformat()
        normalized.append(CalendarEventResponse(**value))
    return normalized


@router.get("/calendar", response_model=list[CalendarEventResponse])
@router.get("/api/calendar", response_model=list[CalendarEventResponse])
def get_calendar(from_date: str = Query(None), to_date: str = Query(None)):
    raw_events = calendar_service.get_economic_calendar(from_date, to_date)
    return _normalize_events(raw_events)
