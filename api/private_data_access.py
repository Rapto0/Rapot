"""One admin boundary for personal HTTP data and authenticated realtime sessions.

Browser WebSockets authenticate in their first message, never in a URL. Credentials
are checked before registering a stream and again before each data delivery.
"""

from __future__ import annotations

import asyncio
import json
import math
import time
from contextlib import suppress
from dataclasses import dataclass

import jwt
from fastapi import HTTPException, Request, WebSocket, WebSocketDisconnect
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from api import auth

PUBLIC_PATHS = frozenset(
    {"/", "/health", "/auth/token", "/auth/me", "/docs", "/redoc", "/openapi.json"}
)
PRIVATE_CACHE = "private, no-store"
MAX_TOKEN_BYTES = 8192
WS_AUTH_TIMEOUT = 5.0


@dataclass(frozen=True, repr=False)
class AccessGrant:
    """A short-lived process-local credential, never serialized or logged."""

    token: str
    expires_at: float

    def check(self) -> None:
        admin_grant(self.token)

    def remaining(self) -> float:
        return max(0.0, self.expires_at - time.time())


def admin_grant(token: str | None) -> AccessGrant:
    if not isinstance(token, str) or not token or len(token) > MAX_TOKEN_BYTES:
        raise HTTPException(
            401, "Yönetici oturumu gerekli.", headers={"WWW-Authenticate": "Bearer"}
        )
    try:
        payload = jwt.decode(
            token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM], options={"require": ["exp"]}
        )
        username = payload.get("sub")
        expiry = payload["exp"]
        if (
            not isinstance(username, str)
            or not username
            or isinstance(expiry, bool)
            or not isinstance(expiry, (int, float))
            or not math.isfinite(expiry)
            or expiry <= time.time()
        ):
            raise ValueError
    except (jwt.InvalidTokenError, ValueError, TypeError, OverflowError):
        raise HTTPException(
            401,
            "Yönetici oturumu geçersiz veya süresi dolmuş.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    user = auth.get_user(username)
    if user is None:
        raise HTTPException(
            401, "Yönetici oturumu geçersiz.", headers={"WWW-Authenticate": "Bearer"}
        )
    if user.get("disabled") or not user.get("is_admin"):
        raise HTTPException(403, "Bu kişisel verilere erişmek için yönetici yetkisi gerekli.")
    return AccessGrant(token=token, expires_at=float(expiry))


def bearer_grant(headers: Headers) -> AccessGrant:
    values = headers.getlist("authorization")
    if len(values) != 1:
        return admin_grant(None)
    scheme, separator, token = values[0].partition(" ")
    return admin_grant(token if separator and scheme.lower() == "bearer" else None)


def require_admin_request(request: Request) -> AccessGrant:
    return bearer_grant(request.headers)


class PrivateDataAccessMiddleware:
    """Default-deny personal data, including unknown future HTTP endpoints."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        public = scope.get("path", "") in PUBLIC_PATHS
        preflight = (
            scope.get("method") == "OPTIONS"
            and "origin" in headers
            and "access-control-request-method" in headers
        )
        if not public and not preflight:
            try:
                grant = bearer_grant(headers)
                scope.setdefault("state", {})["private_data_grant"] = grant
            except HTTPException as error:
                response = JSONResponse(
                    {"detail": error.detail},
                    status_code=error.status_code,
                    headers={**(error.headers or {}), "Cache-Control": PRIVATE_CACHE},
                )
                await response(scope, receive, send)
                return

        started = False

        async def private_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            if message["type"] == "http.response.start" and (
                not public or scope.get("path", "").startswith("/auth/")
            ):
                output_headers = MutableHeaders(scope=message)
                output_headers["Cache-Control"] = PRIVATE_CACHE
                output_headers.add_vary_header("Authorization")
            await send(message)

        try:
            await self.app(scope, receive, private_send)
        except Exception:
            if started or public:
                raise
            # An unhandled provider error must not escape with account details or
            # a cacheable response. Error text is deliberately never serialized.
            response = JSONResponse(
                {"detail": "Veri isteği tamamlanamadı."},
                status_code=500,
                headers={"Cache-Control": PRIVATE_CACHE},
            )
            await response(scope, receive, send)


async def authenticate_websocket(websocket: WebSocket) -> AccessGrant | None:
    """Accept transport only; no subscription/data is created until auth succeeds."""
    await websocket.accept()
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), WS_AUTH_TIMEOUT)
        if len(raw) > MAX_TOKEN_BYTES + 100:
            raise ValueError
        value = json.loads(raw)
        if (
            not isinstance(value, dict)
            or set(value) != {"type", "token"}
            or value["type"] != "auth"
        ):
            raise ValueError
        grant = admin_grant(value["token"])
    except HTTPException as error:
        await websocket.close(code=4403 if error.status_code == 403 else 4401)
        return None
    except (TimeoutError, ValueError, TypeError, KeyError, WebSocketDisconnect):
        with suppress(RuntimeError):
            await websocket.close(code=4401)
        return None
    await websocket.send_text(json.dumps({"type": "authenticated"}))
    return grant


async def receive_private(websocket: WebSocket, grant: AccessGrant, timeout: float = 30) -> str:
    try:
        grant.check()
        result = await asyncio.wait_for(websocket.receive_text(), min(timeout, grant.remaining()))
        grant.check()
        return result
    except TimeoutError:
        # A regular heartbeat timeout may be retried; expiration cannot.
        try:
            grant.check()
        except HTTPException as error:
            await websocket.close(code=4403 if error.status_code == 403 else 4401)
            raise WebSocketDisconnect(code=4401) from None
        raise
    except HTTPException as error:
        await websocket.close(code=4403 if error.status_code == 403 else 4401)
        raise WebSocketDisconnect(code=4401) from None
