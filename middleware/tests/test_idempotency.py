from __future__ import annotations


def test_webhook_idempotency_prevents_duplicate_orders(client, sample_buy_payload):
    first = client.post("/webhooks/tradingview", json=sample_buy_payload)
    second = client.post("/webhooks/tradingview", json=sample_buy_payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True

    orders = client.get("/orders").json()
    assert len(orders) == 1
    signals = client.get("/signals").json()
    assert len(signals) == 1
