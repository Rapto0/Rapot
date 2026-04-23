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
