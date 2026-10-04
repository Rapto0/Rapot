"""Personal data authorization is checked before work and throughout streaming."""

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from api import private_data_access as access
from api import realtime


@pytest.fixture
def personal_app(api_auth_users, monkeypatch):
    app = FastAPI()
    app.add_middleware(access.PrivateDataAccessMiddleware)
    app.include_router(realtime.router)
    monkeypatch.setattr(realtime, "manager", realtime.ConnectionManager())
    work = []

    @app.get("/private-data")
    def data():
        work.append("data")
        return {"price": 123}

    @app.get("/private-error")
    def error():
        raise RuntimeError("provider-cookie-should-not-escape")

    @app.get("/health")
    def health():
        return {"status": "healthy"}

    @app.post("/auth/token")
    def token():
        return {"public_login": True}

    return app, work


@pytest.mark.parametrize("username,status", [(None, 401), ("user", 403), ("disabled", 403)])
def test_private_http_rejects_before_work(personal_app, api_auth_users, username, status):
    app, work = personal_app
    headers = (
        {"Authorization": "Bearer " + api_auth_users.create_access_token({"sub": username})}
        if username
        else {}
    )
    response = TestClient(app).get("/private-data", headers=headers)
    assert response.status_code == status
    assert response.headers["cache-control"] == "private, no-store"
    assert work == []


def test_private_http_success_errors_and_public_login(personal_app, api_auth_users):
    app, work = personal_app
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.post("/auth/token").status_code == 200
    assert client.post("/auth/token").headers["cache-control"] == "private, no-store"
    client.headers["Authorization"] = "Bearer " + api_auth_users.create_access_token(
        {"sub": "admin"}
    )
    response = client.get("/private-data")
    assert response.json() == {"price": 123}
    assert response.headers["cache-control"] == "private, no-store"
    assert "Authorization" in response.headers["vary"]
    assert work == ["data"]
    failed = client.get("/private-error")
    assert failed.status_code == 500
    assert failed.headers["cache-control"] == "private, no-store"
    assert "provider-cookie" not in failed.text
    missing = client.get("/future-personal-route")
    assert missing.status_code == 404
    assert missing.headers["cache-control"] == "private, no-store"


@pytest.mark.parametrize(
    "path",
    [
        "/realtime/ws/signals",
        "/realtime/ws/ticker",
        "/realtime/ws/kline/BTCUSDT",
        "/realtime/ws/trades/BTCUSDT",
    ],
)
@pytest.mark.parametrize("credential", ["missing", "invalid", "expired", "regular"])
def test_every_websocket_rejects_before_subscriptions(
    personal_app, api_auth_users, path, credential
):
    app, _ = personal_app
    payload = {"action": "subscribe", "symbol": "BTCUSDT"}
    if credential != "missing":
        token = "bad-token"
        if credential == "expired":
            token = api_auth_users.create_access_token({"sub": "admin"}, timedelta(seconds=-10))
        elif credential == "regular":
            token = api_auth_users.create_access_token({"sub": "user"})
        payload = {"type": "auth", "token": token}
    with TestClient(app).websocket_connect(path) as socket:
        socket.send_json(payload)
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
        assert closed.value.code == (4403 if credential == "regular" else 4401)
    assert realtime.manager.total_connections == 0
    assert realtime.manager._grants == {}


def test_admin_stream_sends_only_after_auth_and_revocation_stops_delivery(
    personal_app, api_auth_users
):
    app, _ = personal_app
    token = api_auth_users.create_access_token({"sub": "admin"})
    with TestClient(app) as client, client.websocket_connect("/realtime/ws/signals") as socket:
        socket.send_json({"type": "auth", "token": token})
        assert socket.receive_json() == {"type": "authenticated"}
        client.portal.call(realtime.broadcast_signal, {"id": 1})
        assert socket.receive_json()["data"] == {"id": 1}
        # Revocation must block the next broadcast, not just the next client message.
        access.auth.USERS_DB["admin"]["disabled"] = True
        client.portal.call(realtime.broadcast_signal, {"id": 2})
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
        assert closed.value.code == 4403
    assert realtime.manager.total_connections == 0


def test_url_token_never_authenticates_a_websocket(personal_app, api_auth_users):
    app, _ = personal_app
    token = api_auth_users.create_access_token({"sub": "admin"})
    with TestClient(app).websocket_connect("/realtime/ws/signals?token=" + token) as socket:
        socket.send_json({"type": "subscribe"})
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
        assert closed.value.code == 4401


@pytest.mark.asyncio
async def test_first_auth_deadline_never_registers_socket(monkeypatch):
    import asyncio

    async def block():
        await asyncio.Event().wait()

    socket = AsyncMock()
    socket.receive_text.side_effect = block
    monkeypatch.setattr(access, "WS_AUTH_TIMEOUT", 0.01)
    assert await access.authenticate_websocket(socket) is None
    socket.close.assert_awaited_once_with(code=4401)


@pytest.mark.asyncio
async def test_sse_stops_without_delivering_data_after_access_expires(monkeypatch, api_auth_users):
    manager = realtime.ConnectionManager()
    monkeypatch.setattr(realtime, "manager", manager)
    token = api_auth_users.create_access_token({"sub": "admin"})
    grant = access.admin_grant(token)
    queue = manager.create_sse_queue("signals")
    queue.put_nowait({"private": "data"})
    monkeypatch.setattr(access.time, "time", lambda: grant.expires_at + 1)
    generator = realtime.event_generator(queue, "signals", grant)
    with pytest.raises(StopAsyncIteration):
        await anext(generator)
    assert manager._sse_queues["signals"] == []


@pytest.mark.parametrize("suffix", ["ticker", "signals"])
def test_sse_requires_bearer_before_creating_queue(personal_app, suffix):
    app, _ = personal_app
    response = TestClient(app).get("/realtime/sse/" + suffix)
    assert response.status_code == 401
    assert response.headers["cache-control"] == "private, no-store"
    assert not realtime.manager._sse_queues[suffix]


def test_invalid_expiry_claim_and_duplicate_header_are_rejected(api_auth_users):
    from starlette.datastructures import Headers

    token = access.auth.jwt.encode(
        {"sub": "admin", "exp": "NaN"}, access.auth.SECRET_KEY, algorithm=access.auth.ALGORITHM
    )
    with pytest.raises(HTTPException) as error:
        access.admin_grant(token)
    assert error.value.status_code == 401
    token = api_auth_users.create_access_token({"sub": "admin"})
    headers = Headers(raw=[(b"authorization", ("Bearer " + token).encode())] * 2)
    with pytest.raises(HTTPException):
        access.bearer_grant(headers)
