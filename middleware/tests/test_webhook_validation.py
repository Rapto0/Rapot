from __future__ import annotations

from datetime import datetime, timedelta

from middleware.infra.settings import settings
from middleware.infra.time import UTC


def test_webhook_rejects_unknown_signal_code(client, sample_buy_payload):
    payload = dict(sample_buy_payload)
    payload["signalCode"] = "UNKNOWN"
    response = client.post("/webhooks/tradingview", json=payload)
    assert response.status_code == 422


def test_webhook_rejects_side_mismatch(client, sample_buy_payload):
    payload = dict(sample_buy_payload)
    payload["signalCode"] = "H_PAH"
    payload["side"] = "BUY"
    response = client.post("/webhooks/tradingview", json=payload)
    assert response.status_code == 422


def test_webhook_rejects_symbol_ticker_mismatch(client, sample_buy_payload):
    payload = dict(sample_buy_payload)
    payload["ticker"] = "GARAN"
    response = client.post("/webhooks/tradingview", json=payload)
    assert response.status_code == 422


def test_webhook_rejects_extra_field(client, sample_buy_payload):
    payload = dict(sample_buy_payload)
    payload["unexpected"] = "x"
    response = client.post("/webhooks/tradingview", json=payload)
    assert response.status_code == 422


def test_webhook_rejects_unknown_source(client, sample_buy_payload):
    payload = dict(sample_buy_payload)
    payload["source"] = "OtherEngine"
    response = client.post("/webhooks/tradingview", json=payload)
    assert response.status_code == 422


def test_webhook_rejects_unsupported_schema_version(client, sample_buy_payload):
    payload = dict(sample_buy_payload)
    payload["schemaVersion"] = 2
    response = client.post("/webhooks/tradingview", json=payload)
    assert response.status_code == 422


def test_webhook_rejects_missing_auth_token(sample_buy_payload):
    from fastapi.testclient import TestClient

    from middleware.api.main import app

    with TestClient(app) as unauth_client:
        response = unauth_client.post("/webhooks/tradingview", json=sample_buy_payload)
    assert response.status_code == 401


def test_webhook_allows_query_token(sample_buy_payload):
    from fastapi.testclient import TestClient

    from middleware.api.main import app

    with TestClient(app) as query_token_client:
        response = query_token_client.post(
            "/webhooks/tradingview?token=test-token", json=sample_buy_payload
        )
    assert response.status_code == 200


def test_webhook_rejects_future_bar_time_by_temporal_guard(client, sample_buy_payload):
    settings.max_signal_future_skew_seconds = 5
    payload = dict(sample_buy_payload)
    future_time = datetime.now(UTC) + timedelta(minutes=2)
    payload["barTime"] = int(future_time.timestamp() * 1000)

    response = client.post("/webhooks/tradingview", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert "future" in (data["risk_reason"] or "").lower()
