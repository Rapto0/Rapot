"""Administrator-only, write-only account configuration and bounded chart streams."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.auth import User, get_current_admin_user
from api.rate_limit import limiter
from application.services.borsapy_gateway import BorsapyGatewayError, get_borsapy_gateway


class PrivateRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def private(request):
            try:
                response = await handler(request)
            except StarletteHTTPException as exc:
                response = JSONResponse(
                    {"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers
                )
            except RequestValidationError:
                response = JSONResponse({"detail": "Geçersiz istek."}, status_code=422)
            response.headers["Cache-Control"] = "private, no-store"
            return response

        return private


router = APIRouter(prefix="/borsapy", tags=["Borsapy connection"], route_class=PrivateRoute)


def _call(method, *args, **kwargs):
    try:
        return method(*args, **kwargs)
    except BorsapyGatewayError as exc:
        raise HTTPException(exc.status_code, str(exc)) from None


@router.get("/connection")
@limiter.limit("60/minute")
def connection_status(request: Request, user: User = Depends(get_current_admin_user)) -> dict:
    return get_borsapy_gateway().status()


@router.post("/connection")
@limiter.limit("5/minute")
async def save_connection(request: Request, user: User = Depends(get_current_admin_user)) -> dict:
    # Do not let framework validation echo a submitted credential in a 422 body.
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 24576:
            raise HTTPException(413, "Bağlantı isteği çok büyük.")
    try:
        values = json.loads(body)
        if not isinstance(values, dict):
            raise ValueError
    except (ValueError, UnicodeError):
        raise HTTPException(422, "Geçersiz bağlantı isteği.") from None
    return await run_in_threadpool(_call, get_borsapy_gateway().configure, values)


@router.post("/connection/verify")
@limiter.limit("5/minute")
def verify_connection(request: Request, user: User = Depends(get_current_admin_user)) -> dict:
    return _call(get_borsapy_gateway().verify)


@router.delete("/connection")
@limiter.limit("5/minute")
def clear_connection(request: Request, user: User = Depends(get_current_admin_user)) -> dict:
    return _call(get_borsapy_gateway().clear)


@router.get("/stream")
@limiter.limit("120/minute")
def stream_snapshot(
    request: Request,
    symbol: str = Query(min_length=1, max_length=66),
    interval: str = Query("1m", max_length=5),
    study: str | None = Query(None, max_length=128),
    study_inputs: str | None = Query(None, max_length=2048),
    subscriber_id: str = Query("shared", min_length=1, max_length=64),
    user: User = Depends(get_current_admin_user),
) -> dict:
    try:
        inputs = json.loads(study_inputs) if study_inputs else None
    except ValueError:
        raise HTTPException(422, "Gösterge girdileri geçersiz.") from None
    return _call(
        get_borsapy_gateway().stream_snapshot, symbol, interval, study, inputs, subscriber_id
    )


@router.delete("/stream")
@limiter.limit("30/minute")
def clear_streams(
    request: Request,
    symbol: str = Query(min_length=1, max_length=66),
    interval: str = Query("1m", max_length=5),
    study: str | None = Query(None, max_length=128),
    study_inputs: str | None = Query(None, max_length=2048),
    subscriber_id: str = Query("shared", min_length=1, max_length=64),
    user: User = Depends(get_current_admin_user),
) -> dict:
    try:
        inputs = json.loads(study_inputs) if study_inputs else None
    except ValueError:
        raise HTTPException(422, "Gösterge girdileri geçersiz.") from None
    return _call(get_borsapy_gateway().close_stream, symbol, interval, study, inputs, subscriber_id)
