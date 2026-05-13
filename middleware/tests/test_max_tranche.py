from __future__ import annotations

from middleware.infra.settings import settings


def _post_distinct_buys(client, sample_buy_payload, count: int):
    responses = []
    for idx in range(1, count + 1):
        payload = dict(sample_buy_payload)
        payload["barIndex"] = idx
        payload["barTime"] = 1713772800000 + (idx * 60_000)
        payload["price"] = 50000 + idx
        responses.append(client.post("/webhooks/tradingview", json=payload))
    return responses


def test_repeated_buy_signals_open_new_tranches_by_default(client, sample_buy_payload):
    responses = _post_distinct_buys(client, sample_buy_payload, 6)

    assert all(r.status_code == 200 for r in responses)
    assert all(r.json()["status"] == "filled" for r in responses)

    position = client.get("/positions/BTCUSDT").json()["position"]
    assert position["open_tranche_count"] == 6


def test_optional_max_open_tranches_rule(client, sample_buy_payload):
    settings.max_open_tranches_per_symbol = 4
    responses = _post_distinct_buys(client, sample_buy_payload, 5)

    assert all(r.status_code == 200 for r in responses)
    assert responses[-1].json()["status"] == "rejected"
    assert "max open tranches exceeded" in (responses[-1].json()["risk_reason"] or "")

    position = client.get("/positions/BTCUSDT").json()["position"]
    assert position["open_tranche_count"] == 4
