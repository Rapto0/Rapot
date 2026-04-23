from __future__ import annotations


def test_sell_signal_uses_fifo_oldest_tranche(client, sample_buy_payload):
    first_buy = dict(sample_buy_payload)
    first_buy["barIndex"] = 1
    first_buy["barTime"] = 1713772800000
    first_buy["price"] = 100.0
    resp1 = client.post("/webhooks/tradingview", json=first_buy)
    assert resp1.status_code == 200

    second_buy = dict(sample_buy_payload)
    second_buy["barIndex"] = 2
    second_buy["barTime"] = 1713859200000
    second_buy["price"] = 90.0
    resp2 = client.post("/webhooks/tradingview", json=second_buy)
    assert resp2.status_code == 200

    before_sell = client.get("/positions/THYAO").json()
    tranches_before = before_sell["tranches"]
    assert len(tranches_before) == 2
    oldest_id = tranches_before[0]["id"]

    sell_payload = dict(sample_buy_payload)
    sell_payload["signalCode"] = "H_PAH"
    sell_payload["signalText"] = "Hunter Pahali"
    sell_payload["side"] = "SELL"
    sell_payload["barIndex"] = 3
    sell_payload["barTime"] = 1713945600000
    sell_payload["price"] = 120.0
    sell_resp = client.post("/webhooks/tradingview", json=sell_payload)
    assert sell_resp.status_code == 200

    orders = client.get("/orders").json()
    sell_order = orders[0]
    assert sell_order["signal_code"] == "H_PAH"
    assert sell_order["target_tranche_id"] == oldest_id

    after_sell = client.get("/positions/THYAO").json()
    tranches_after = after_sell["tranches"]
    assert len(tranches_after) == 1
    assert tranches_after[0]["id"] != oldest_id
