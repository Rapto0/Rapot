from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from middleware.api.main import app
from middleware.infra.db import get_session_local
from middleware.infra.models import Order, SignalEvent
from middleware.infra.settings import settings


def _assert_no_orders_or_signals() -> None:
    with get_session_local()() as session:
        assert session.scalar(select(func.count()).select_from(Order)) == 0
        assert session.scalar(select(func.count()).select_from(SignalEvent)) == 0


@pytest.mark.parametrize(
    "headers,query",
    [
        ({}, ""),
        ({"X-Admin-Token": "wrong"}, ""),
        ({"X-Webhook-Token": "test-token"}, ""),
        ({"X-Admin-Token": "test-token"}, ""),
        ({}, "?token=test-admin-token"),
    ],
)
def test_replay_rejects_before_broker_or_database_work(
    headers, query, sample_buy_payload, monkeypatch
):
    broker_factory = Mock(side_effect=AssertionError("unauthorized broker creation"))
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", broker_factory)
    with TestClient(app) as client:
        response = client.post(
            f"/admin/replay-signal{query}",
            headers=headers,
            json={"payload": sample_buy_payload, "bypass_idempotency": True},
        )
    assert response.status_code == 401
    broker_factory.assert_not_called()
    _assert_no_orders_or_signals()


@pytest.mark.parametrize("configured", [None, "test-token"])
def test_admin_auth_fails_closed_when_unconfigured_or_reusing_webhook_key(
    configured, client, sample_buy_payload, monkeypatch
):
    settings.admin_auth_token = configured
    broker_factory = Mock()
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", broker_factory)
    response = client.post("/admin/replay-signal", json={"payload": sample_buy_payload})
    assert response.status_code == 503
    broker_factory.assert_not_called()
    _assert_no_orders_or_signals()


def test_disabled_admin_rejects_valid_key(client, sample_buy_payload, monkeypatch):
    settings.allow_admin_endpoints = False
    broker_factory = Mock()
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", broker_factory)
    assert (
        client.post("/admin/replay-signal", json={"payload": sample_buy_payload}).status_code == 403
    )
    assert client.get("/admin/reconcile/BTCUSDT").status_code == 403
    broker_factory.assert_not_called()
    _assert_no_orders_or_signals()


def test_disabling_webhook_auth_does_not_disable_admin_auth(sample_buy_payload):
    settings.require_webhook_auth = False
    with TestClient(app) as client:
        response = client.post("/admin/replay-signal", json={"payload": sample_buy_payload})
    assert response.status_code == 401
    _assert_no_orders_or_signals()


@pytest.mark.parametrize(
    "path", ["/orders", "/positions", "/positions/BTCUSDT", "/signals", "/admin/reconcile/BTCUSDT"]
)
def test_account_read_routes_require_management_key(path, monkeypatch):
    broker_factory = Mock()
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", broker_factory)
    with TestClient(app) as client:
        assert client.get(path, headers={"X-Webhook-Token": "test-token"}).status_code == 401
    broker_factory.assert_not_called()


def test_authorized_replay_requires_explicit_idempotency_bypass(client, sample_buy_payload):
    first = client.post("/webhooks/tradingview", json=sample_buy_payload)
    duplicate = client.post("/admin/replay-signal", json={"payload": sample_buy_payload})
    replay = client.post(
        "/admin/replay-signal", json={"payload": sample_buy_payload, "bypass_idempotency": True}
    )
    assert first.status_code == duplicate.status_code == replay.status_code == 200
    assert duplicate.json()["duplicate"] is True
    assert replay.json()["duplicate"] is False
    assert len(client.get("/orders").json()) == 2


@pytest.mark.parametrize(
    "path", ["/admin/replay-signal", "/admin/reconcile/BTCUSDT", "/webhooks/tradingview"]
)
def test_operation_failure_does_not_leak_exception(
    path, client, sample_buy_payload, monkeypatch, caplog
):
    secret = "private-broker-token-in-error"
    service = Mock()
    service.replay_signal.side_effect = RuntimeError(secret)
    service.reconcile_symbol.side_effect = RuntimeError(secret)
    service.process_webhook.side_effect = RuntimeError(secret)
    monkeypatch.setattr("middleware.api.dependencies.TradingService", Mock(return_value=service))
    if "reconcile" in path:
        response = client.get(path)
    else:
        payload = {"payload": sample_buy_payload} if "replay" in path else sample_buy_payload
        response = client.post(path, json=payload)
    assert response.status_code == 500
    assert secret not in response.text
    assert secret not in caplog.text
