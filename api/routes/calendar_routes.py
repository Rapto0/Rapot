"""Private borsapy calendar; both URL aliases require administrator access."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api.auth import User, get_current_admin_user
from api.calendar_service import calendar_service
from api.rate_limit import limiter
from api.routes.borsapy_connection_routes import PrivateRoute
from application.services.borsapy_gateway import BorsapyGatewayError

router = APIRouter(tags=["Calendar"], route_class=PrivateRoute)


@router.get("/calendar")
@router.get("/api/calendar")
@limiter.limit("30/minute")
def get_calendar(
    request: Request,
    from_date: str | None = Query(None, max_length=10),
    to_date: str | None = Query(None, max_length=10),
    country: str = Query("TR,US", max_length=8),
    importance: str = Query("all", max_length=4),
    user: User = Depends(get_current_admin_user),
) -> dict:
    try:
        return calendar_service.get_economic_calendar(from_date, to_date, country, importance)
    except BorsapyGatewayError as exc:
        raise HTTPException(exc.status_code, str(exc)) from None
