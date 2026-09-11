"""Exercise application auth and JSON boundaries across HTTP dependency upgrades.

These ASGI requests do not prove that a public HTTP server accepts malformed Host
headers. They verify that headers reaching the apps cannot bypass their real auth
dependencies. No lifespan, provider, broker, or middleware database is started.
"""

import json
import sys
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

import api.main as api_main

MALFORMED_HOSTS = ("testserver/public?resource=", "testserver#public")


@pytest.fixture
def api_boundary(monkeypatch):
    manual = Mock(side_effect=AssertionError("manual analysis must not start"))
    ai = Mock(side_effect=AssertionError("AI must not start"))
    inspect = Mock(side_effect=AssertionError("market data must not be fetched"))
    monkeypatch.setitem(sys.modules, "command_handler", SimpleNamespace(analyze_manual=manual))
    monkeypatch.setitem(sys.modules, "ai_analyst", SimpleNamespace(analyze_with_gemini=ai))
    monkeypatch.setattr(api_main, "inspect_strategy", inspect)
    client = TestClient(api_main.app)
    try:
        yield client
    finally:
        client.close()
        manual.assert_not_called()
        ai.assert_not_called()
        inspect.assert_not_called()


@pytest.mark.parametrize("host", MALFORMED_HOSTS)
@pytest.mark.parametrize("credential", [None, "not-a-token"])
@pytest.mark.parametrize(
    "method,path", [("POST", "/analyze/THYAO"), ("GET", "/market/analysis?symbol=THYAO")]
)
def test_malformed_host_does_not_bypass_api_auth(
    api_boundary, api_auth_users, host, credential, method, path
):
    headers = {"Host": host}
    if credential is not None:
        headers["Authorization"] = f"Bearer {credential}"
    response = api_boundary.request(method, path, headers=headers)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("host", MALFORMED_HOSTS)
def test_malformed_host_preserves_authenticated_user_and_admin_boundary(
    api_boundary, api_auth_users, host
):
    token = api_auth_users.create_access_token({"sub": "user"})
    headers = {"Host": host, "Authorization": f"Bearer {token}"}
    me = api_boundary.get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["username"] == "user"
    assert me.json()["is_admin"] is False
    assert api_boundary.post("/analyze/THYAO", headers=headers).status_code == 403


@pytest.mark.parametrize(
    "content_type,body",
    [
        ("application/x-www-form-urlencoded", "username=admin&password=test-password"),
        ("text/plain", '{"username":"admin","password":"test-password"}'),
        ("application/json", '["admin", "test-password"]'),
        ("application/json", '{"username":'),
    ],
)
def test_login_requires_json_object_before_authenticating(
    api_boundary, api_auth_users, monkeypatch, content_type, body
):
    authenticate = Mock(wraps=api_auth_users.authenticate_user)
    monkeypatch.setattr(api_auth_users, "authenticate_user", authenticate)
    rejected = api_boundary.post(
        "/auth/token", content=body, headers={"Content-Type": content_type}
    )
    assert rejected.status_code == 422
    assert "access_token" not in rejected.json()
    authenticate.assert_not_called()

    accepted = api_boundary.post(
        "/auth/token", json={"username": "admin", "password": "test-password"}
    )
    assert accepted.status_code == 200
    assert accepted.json()["token_type"] == "bearer"
    assert accepted.json()["access_token"]
    authenticate.assert_called_once_with("admin", "test-password")


def test_invalid_signal_limit_reports_documented_context_before_repository_work(
    api_boundary, monkeypatch
):
    from application.services import signal_trade_service

    list_signals = Mock(side_effect=AssertionError("invalid pagination must not query records"))
    monkeypatch.setattr(signal_trade_service, "list_signals", list_signals)
    response = api_boundary.get("/signals?limit=0")
    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["loc"] == ["query", "limit"]
    assert error["type"] == "greater_than_equal"
    assert error["input"] == "0"
    assert error["ctx"] == {"ge": 1}
    definition = api_main.app.openapi()["components"]["schemas"]["ValidationError"]
    assert set(error) <= set(definition["properties"])
    assert set(definition["required"]) == {"loc", "msg", "type"}
    list_signals.assert_not_called()


@pytest.fixture
def webhook_payload():
    return {
        "source": "Combo+Hunter",
        "symbol": "BTCUSDT",
        "ticker": "BTCUSDT",
        "signalCode": "H_BLS",
        "signalText": "Hunter Beles",
        "side": "BUY",
        "price": 50000,
        "timeframe": "1H",
        "barTime": 1713772800000,
        "barIndex": 12345,
        "isRealtime": True,
    }


@pytest.fixture
def middleware_boundary(monkeypatch):
    from middleware.api import dependencies
    from middleware.api.main import app
    from middleware.domain.enums import ExecutionMode
    from middleware.domain.events import ProcessSignalResponse

    for name, value in {
        "require_webhook_auth": True,
        "webhook_auth_token": "boundary-webhook-token",
        "allow_admin_endpoints": True,
        "admin_auth_token": "boundary-admin-token",
        "execution_mode": ExecutionMode.DRY_RUN,
        "trading_enabled": False,
        "binance_live_enabled": False,
        "binance_api_key": None,
        "binance_secret_key": None,
    }.items():
        monkeypatch.setattr(dependencies.settings, name, value)
    response = ProcessSignalResponse(signal_event_id=17, duplicate=False, message="boundary test")
    service = SimpleNamespace(
        process_webhook=Mock(return_value=response), replay_signal=Mock(return_value=response)
    )
    resolve_service = Mock(return_value=service)
    broker = Mock(side_effect=AssertionError("broker must not be constructed"))
    database = Mock(side_effect=AssertionError("middleware database must not be opened"))

    def get_service():
        return resolve_service()

    def no_database():
        return database()

    monkeypatch.setattr(dependencies, "build_broker_client", broker)
    monkeypatch.setitem(app.dependency_overrides, dependencies.get_service, get_service)
    monkeypatch.setitem(app.dependency_overrides, dependencies.get_db_session, no_database)
    # Deliberately no context manager: startup would initialize a database.
    client = TestClient(app)
    try:
        yield SimpleNamespace(client=client, service=service, resolve_service=resolve_service)
    finally:
        client.close()
        broker.assert_not_called()
        database.assert_not_called()


@pytest.mark.parametrize("host", MALFORMED_HOSTS)
@pytest.mark.parametrize("token", [None, "wrong-token"])
def test_malformed_host_cannot_bypass_webhook_token(
    middleware_boundary, webhook_payload, host, token
):
    headers = {"Host": host}
    if token is not None:
        headers["X-Webhook-Token"] = token
    response = middleware_boundary.client.post(
        "/webhooks/tradingview", json=webhook_payload, headers=headers
    )
    assert response.status_code == 401
    middleware_boundary.resolve_service.assert_not_called()
    middleware_boundary.service.process_webhook.assert_not_called()


@pytest.mark.parametrize("host", MALFORMED_HOSTS)
def test_webhook_secret_is_not_admin_identity_even_with_malformed_host(
    middleware_boundary, webhook_payload, host
):
    response = middleware_boundary.client.post(
        "/admin/replay-signal",
        json={"payload": webhook_payload},
        headers={"Host": host, "X-Admin-Token": "boundary-webhook-token"},
    )
    assert response.status_code == 401
    middleware_boundary.resolve_service.assert_not_called()
    middleware_boundary.service.replay_signal.assert_not_called()


@pytest.mark.parametrize("credential_location", ["header", "query"])
@pytest.mark.parametrize("body_kind", ["form", "json-list", "broken-json"])
def test_webhook_json_contract_and_token_fallback(
    middleware_boundary, webhook_payload, credential_location, body_kind
):
    from middleware.domain.events import TradingViewWebhookPayload

    headers = {}
    path = "/webhooks/tradingview"
    if credential_location == "header":
        headers["X-Webhook-Token"] = "boundary-webhook-token"
    else:
        path += "?token=boundary-webhook-token"
    content_type, body = {
        "form": ("application/x-www-form-urlencoded", urlencode(webhook_payload)),
        "json-list": ("application/json", json.dumps([webhook_payload])),
        "broken-json": ("application/json", '{"source":'),
    }[body_kind]
    rejected = middleware_boundary.client.post(
        path, content=body, headers={**headers, "Content-Type": content_type}
    )
    assert rejected.status_code == 422
    middleware_boundary.service.process_webhook.assert_not_called()

    accepted = middleware_boundary.client.post(path, json=webhook_payload, headers=headers)
    assert accepted.status_code == 200
    assert accepted.json()["signal_event_id"] == 17
    middleware_boundary.service.process_webhook.assert_called_once_with(
        TradingViewWebhookPayload.model_validate(webhook_payload)
    )


def test_unregistered_http_method_cannot_dispatch_webhook_work(
    middleware_boundary, webhook_payload
):
    response = middleware_boundary.client.request(
        "CUSTOM",
        "/webhooks/tradingview",
        json=webhook_payload,
        headers={"X-Webhook-Token": "boundary-webhook-token"},
    )
    assert response.status_code == 405
    middleware_boundary.resolve_service.assert_not_called()
    middleware_boundary.service.process_webhook.assert_not_called()
