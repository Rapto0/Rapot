from __future__ import annotations


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
