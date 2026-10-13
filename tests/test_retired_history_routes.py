"""Retired scanner history has no data path or background delivery surface."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from starlette.websockets import WebSocketDisconnect

from api import main as api_main
from api import realtime
from api.routes.retired_history_routes import RETIRED_PATHS
from db_session import get_engine


@pytest.mark.parametrize("path", RETIRED_PATHS)
def test_history_tombstone_is_private_absent_from_openapi_and_never_queries_database(
    authenticated_api_client, path
):
    calls = []

    def query(*args):
        calls.append(args[2])

    engine = get_engine()
    event.listen(engine, "before_cursor_execute", query)
    try:
        response = authenticated_api_client.get(path.replace("{signal_id}", "42"))
    finally:
        event.remove(engine, "before_cursor_execute", query)
    assert response.status_code == 410
    assert response.headers["cache-control"] == "private, no-store"
    assert calls == []
    assert path not in authenticated_api_client.get("/openapi.json").json()["paths"]


@pytest.mark.parametrize("path", RETIRED_PATHS)
@pytest.mark.parametrize("username,status", [(None, 401), ("user", 403)])
def test_history_tombstones_keep_auth_boundary(api_auth_users, path, username, status):
    headers = (
        {"Authorization": "Bearer " + api_auth_users.create_access_token({"sub": username})}
        if username
        else {}
    )
    client = TestClient(api_main.app)
    try:
        response = client.get(path.replace("{signal_id}", "42"), headers=headers)
    finally:
        client.close()
    assert response.status_code == status
    assert response.headers["cache-control"] == "private, no-store"


def test_signal_websocket_authenticates_then_retires_without_subscription(
    authenticated_api_client, api_auth_users, monkeypatch
):
    manager = realtime.ConnectionManager()
    monkeypatch.setattr(realtime, "manager", manager)
    token = api_auth_users.create_access_token({"sub": "admin"})
    with authenticated_api_client.websocket_connect("/realtime/ws/signals") as socket:
        socket.send_json({"type": "auth", "token": token})
        assert socket.receive_json() == {"type": "authenticated"}
        with pytest.raises(WebSocketDisconnect) as error:
            socket.receive_json()
        assert error.value.code == 4410
    assert manager.total_connections == 0
    assert not manager._grants


def test_signal_sse_retires_without_queue(authenticated_api_client, monkeypatch):
    manager = realtime.ConnectionManager()
    monkeypatch.setattr(realtime, "manager", manager)
    response = authenticated_api_client.get("/realtime/sse/signals")
    assert response.status_code == 410
    assert response.headers["cache-control"] == "private, no-store"
    assert not manager._sse_queues
