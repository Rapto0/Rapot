from __future__ import annotations

from decimal import Decimal

from middleware.infra.settings import settings


def test_buy_sizing_uses_budget_multiplier_formula(client, sample_buy_payload):
    settings.base_budget_tl = Decimal("10000")
    settings.buy_bps = 0
    settings.multiplier_h_ucz = Decimal("0.50")
    settings.__dict__.pop("signal_multipliers", None)

    payload = dict(sample_buy_payload)
    payload["signalCode"] = "H_UCZ"
    payload["price"] = 200.0
    response = client.post("/webhooks/tradingview", json=payload)
    assert response.status_code == 200

    orders = client.get("/orders").json()
    assert len(orders) == 1
    order = orders[0]
    assert Decimal(order["budget_tl"]) == Decimal("5000")
    assert Decimal(order["limit_price"]) == Decimal("200")
    assert order["requested_lots"] == 25
