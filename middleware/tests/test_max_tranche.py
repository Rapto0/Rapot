from __future__ import annotations


def test_max_four_open_tranches_rule(client, sample_buy_payload):
    responses = []
    for idx in range(1, 6):
        payload = dict(sample_buy_payload)
        payload["barIndex"] = idx
        payload["barTime"] = 1713772800000 + (idx * 60_000)
        payload["price"] = 100.0 + idx
        responses.append(client.post("/webhooks/tradingview", json=payload))

    assert all(r.status_code == 200 for r in responses)
    assert responses[-1].json()["status"] == "rejected"
    assert "max open tranches exceeded" in (responses[-1].json()["risk_reason"] or "")

    position = client.get("/positions/THYAO").json()["position"]
    assert position["open_tranche_count"] == 4
