from __future__ import annotations


def test_dry_run_mock_broker_flow(client, sample_buy_payload):
    response = client.post("/webhooks/tradingview", json=sample_buy_payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "filled"
    assert body["broker_order_id"] is not None

    orders = client.get("/orders").json()
    assert len(orders) == 1
    assert orders[0]["broker_name"] == "MOCK"
    assert orders[0]["status"] == "filled"

    position = client.get("/positions/THYAO").json()["position"]
    assert position["open_tranche_count"] == 1
    assert position["total_remaining_lots"] > 0
