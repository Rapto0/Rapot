from __future__ import annotations

from decimal import Decimal


def test_dry_run_binance_spot_flow(client, sample_buy_payload):
    response = client.post("/webhooks/tradingview", json=sample_buy_payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "filled"
    assert body["broker_order_id"] is not None

    orders = client.get("/orders").json()
    assert len(orders) == 1
    assert orders[0]["broker_name"] == "BINANCE_SPOT"
    assert orders[0]["status"] == "filled"
    assert Decimal(orders[0]["requested_quantity"]) > 0
    assert Decimal(orders[0]["quote_budget"]) == Decimal("10.000000000000")

    position = client.get("/positions/BTCUSDT").json()["position"]
    assert position["open_tranche_count"] == 1
    assert Decimal(position["total_remaining_quantity"]) > 0
