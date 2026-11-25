"""HttpOnly cookie session, CSRF double-submit protection, and short-lived WS ticket tests."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import api.main as api_main
from api import private_data_access as access
from api import realtime
from api.auth import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME


def _set_cookie_headers(response) -> list[str]:
    return [value for key, value in response.headers.multi_items() if key.lower() == "set-cookie"]


def test_cookie_session_login_sets_httponly_and_csrf_without_exposing_jwt(api_auth_users):
    client = TestClient(api_main.app)
    res = client.post(
        "/auth/session",
        json={"username": "admin", "password": "test-password"},
        headers={"X-Forwarded-Proto": "https"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["authenticated"] is True
    assert body["user"]["username"] == "admin"
    assert body["user"]["is_admin"] is True
    assert body["expires_in"] > 0
    assert "access_token" not in body
    assert "token" not in body
    assert res.headers["cache-control"] == "private, no-store"

    cookies = _set_cookie_headers(res)
    session_cookie = next(c for c in cookies if c.startswith(f"{SESSION_COOKIE_NAME}="))
    csrf_cookie = next(c for c in cookies if c.startswith(f"{CSRF_COOKIE_NAME}="))
    assert "HttpOnly" in session_cookie
    assert "SameSite=lax" in session_cookie or "SameSite=Lax" in session_cookie
    assert "Secure" in session_cookie
    assert "HttpOnly" not in csrf_cookie
    assert "SameSite=lax" in csrf_cookie or "SameSite=Lax" in csrf_cookie
    assert "Secure" in csrf_cookie


def test_cookie_session_persists_across_refresh_and_enforces_csrf_on_mutations(api_auth_users):
    client = TestClient(api_main.app)

    guest = client.get("/auth/session")
    assert guest.status_code == 200
    assert guest.json()["authenticated"] is False

    login = client.post("/auth/session", json={"username": "admin", "password": "test-password"})
    assert login.status_code == 200
    csrf_token = client.cookies.get(CSRF_COOKIE_NAME)
    assert csrf_token

    # Refresh / new tab hydration via GET /auth/session works with HttpOnly cookie alone.
    hydrated = client.get("/auth/session")
    assert hydrated.status_code == 200
    assert hydrated.json()["authenticated"] is True
    assert hydrated.json()["user"]["username"] == "admin"

    # GET on private endpoints works via HttpOnly cookie without Authorization header.
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["is_admin"] is True
    trades = client.get("/trades")
    assert trades.status_code == 200
    assert "Cookie" in trades.headers["vary"]
    assert "Authorization" in trades.headers["vary"]

    # Mutating private requests via cookie MUST fail with 403 without matching X-CSRF-Token.
    no_csrf = client.post("/analyze/THYAO")
    assert no_csrf.status_code == 403
    wrong_csrf = client.post("/analyze/THYAO", headers={"X-CSRF-Token": "wrong-token"})
    assert wrong_csrf.status_code == 403

    # Mutating private requests with matching X-CSRF-Token pass middleware (retired endpoint returns 410).
    ok_csrf = client.post("/analyze/THYAO", headers={"X-CSRF-Token": csrf_token})
    assert ok_csrf.status_code == 410


def test_logout_enforces_csrf_for_cookie_sessions_and_clears_cookies(api_auth_users):
    client = TestClient(api_main.app)
    # Anonymous logout is safe and idempotent.
    assert client.post("/auth/logout").status_code == 200

    login = client.post("/auth/session", json={"username": "admin", "password": "test-password"})
    assert login.status_code == 200
    csrf_token = client.cookies.get(CSRF_COOKIE_NAME)

    # Cross-site logout without CSRF token is blocked.
    blocked = client.post("/auth/logout")
    assert blocked.status_code == 403
    assert client.get("/auth/session").json()["authenticated"] is True

    # Logout with valid CSRF token clears session cookies.
    out = client.post("/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert out.status_code == 200
    assert out.json() == {"logged_out": True}
    assert client.get("/auth/session").json()["authenticated"] is False
    assert client.get("/trades").status_code == 401


def test_regular_user_cookie_cannot_access_admin_endpoints_or_ws_ticket(api_auth_users):
    client = TestClient(api_main.app)
    login = client.post("/auth/session", json={"username": "user", "password": "test-password"})
    assert login.status_code == 200
    assert login.json()["user"]["is_admin"] is False
    csrf_token = client.cookies.get(CSRF_COOKIE_NAME)

    assert client.get("/trades").status_code == 403
    assert client.post("/auth/ws-ticket", headers={"X-CSRF-Token": csrf_token}).status_code == 403


def test_ws_ticket_rejected_on_http_and_accepted_on_websocket_past_ticket_ttl(
    api_auth_users, monkeypatch
):
    import websocket_manager

    monkeypatch.setattr(realtime, "manager", realtime.ConnectionManager())
    monkeypatch.setattr(websocket_manager.ws_manager, "subscribe_kline", AsyncMock())
    monkeypatch.setattr(websocket_manager.ws_manager, "unsubscribe_kline", AsyncMock())

    client = TestClient(api_main.app)
    assert client.post("/auth/ws-ticket").status_code == 401

    login = client.post("/auth/session", json={"username": "admin", "password": "test-password"})
    assert login.status_code == 200
    csrf_token = client.cookies.get(CSRF_COOKIE_NAME)

    # Requires CSRF for cookie auth.
    assert client.post("/auth/ws-ticket").status_code == 403

    ticket_res = client.post("/auth/ws-ticket", headers={"X-CSRF-Token": csrf_token})
    assert ticket_res.status_code == 200
    ticket_body = ticket_res.json()
    ticket = ticket_body["ticket"]
    assert 1 <= ticket_body["expires_in"] <= 30

    # A WS ticket must NEVER be accepted as an HTTP Bearer token or session cookie.
    anon = TestClient(api_main.app)
    assert anon.get("/trades", headers={"Authorization": f"Bearer {ticket}"}).status_code == 401
    assert anon.get("/auth/me", headers={"Authorization": f"Bearer {ticket}"}).status_code == 401
    assert (
        anon.get("/auth/session", headers={"Authorization": f"Bearer {ticket}"}).json()[
            "authenticated"
        ]
        is False
    )

    # WebSocket handshake accepts the ticket and stays valid after the 30s ticket TTL (until session_exp).
    ws_app = FastAPI()
    ws_app.add_middleware(access.PrivateDataAccessMiddleware)
    ws_app.include_router(realtime.router)
    now = access.time.time()
    with (
        TestClient(ws_app) as ws_client,
        ws_client.websocket_connect("/realtime/ws/kline/BTCUSDT") as socket,
    ):
        socket.send_json({"type": "auth", "token": ticket})
        assert socket.receive_json() == {"type": "authenticated"}

        # Advance time by 45s (past 30s ticket TTL, well within 1h WS session cap).
        monkeypatch.setattr(access.time, "time", lambda: now + 45)
        ws_client.portal.call(realtime.broadcast_kline, "BTCUSDT", "1m", {"id": 10})
        assert socket.receive_json()["data"]["id"] == 10

        # Disabling admin still revokes the open WS stream immediately.
        access.auth.USERS_DB["admin"]["disabled"] = True
        ws_client.portal.call(realtime.broadcast_kline, "BTCUSDT", "1m", {"id": 11})
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
        assert closed.value.code == 4403


def test_expired_ws_ticket_is_rejected_at_handshake(api_auth_users, monkeypatch):
    client = TestClient(api_main.app)
    token = api_auth_users.create_access_token({"sub": "admin"}, timedelta(minutes=30))
    ticket_res = client.post("/auth/ws-ticket", headers={"Authorization": f"Bearer {token}"})
    assert ticket_res.status_code == 200
    ticket = ticket_res.json()["ticket"]

    # Simulate handshake arriving 35 seconds later (ticket expired).
    future = access.time.time() + 35
    monkeypatch.setattr(access.time, "time", lambda: future)
    with client.websocket_connect("/realtime/ws/ticker") as socket:
        socket.send_json({"type": "auth", "token": ticket})
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
        assert closed.value.code == 4401
