from __future__ import annotations

from middleware.domain.enums import ExecutionMode
from middleware.domain.events import BrokerOrderRequestPayload
from middleware.infra.settings import settings
from middleware.tests.conftest import FakeBinanceSpotBroker


class RecordingBroker:
    name = "BINANCE_SPOT"

    def __init__(self) -> None:
        self.inner = FakeBinanceSpotBroker()
        self.submissions: list[BrokerOrderRequestPayload] = []

    def get_symbol_rules(self, symbol):
        return self.inner.get_symbol_rules(symbol)

    def get_asset_balance(self, asset):
        return self.inner.get_asset_balance(asset)

    def get_asset_balances(self, asset):
        return self.inner.get_asset_balances(asset)

    def submit_limit_order(self, payload):
        self.submissions.append(payload)
        return self.inner.submit_limit_order(payload)


def _sell_payload(sample_buy_payload: dict, *, bar_index: int = 2) -> dict:
    payload = dict(sample_buy_payload)
    payload.update(
        {
            "signalCode": "H_PAH",
            "signalText": "Hunter Pahali",
            "side": "SELL",
            "barIndex": bar_index,
            "barTime": sample_buy_payload["barTime"] + (bar_index * 60_000),
            "price": 51000,
        }
    )
    return payload


def _set_live_scope(*, base_url: str, account_id: str) -> None:
    settings.execution_mode = ExecutionMode.LIVE
    settings.inventory_account_id = account_id
    settings.binance_base_url = base_url
    settings.trading_enabled = True
    settings.binance_live_enabled = True


def test_dry_run_inventory_cannot_be_selected_or_listed_in_live_mode(
    client, sample_buy_payload, monkeypatch
):
    broker = RecordingBroker()
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", lambda cfg: broker)

    dry_scope = settings.inventory_scope
    dry_buy = client.post("/webhooks/tradingview", json=sample_buy_payload)
    assert dry_buy.status_code == 200
    assert dry_buy.json()["status"] == "filled"
    assert len(broker.submissions) == 1

    _set_live_scope(base_url="https://api.binance.com", account_id="primary")
    live_scope = settings.inventory_scope
    live_sell = client.post("/webhooks/tradingview", json=_sell_payload(sample_buy_payload))

    assert live_scope != dry_scope
    assert live_sell.status_code == 200
    assert live_sell.json()["status"] == "rejected"
    assert len(broker.submissions) == 1
    assert client.get("/positions/BTCUSDT").status_code == 404
    live_orders = client.get("/orders").json()
    assert len(live_orders) == 1
    assert live_orders[0]["mode"] == "LIVE"
    assert live_orders[0]["inventory_scope"] == live_scope

    settings.execution_mode = ExecutionMode.DRY_RUN
    settings.inventory_account_id = "pytest"
    assert settings.inventory_scope == dry_scope
    dry_position = client.get("/positions/BTCUSDT").json()
    assert dry_position["position"]["inventory_scope"] == dry_scope
    assert len(dry_position["tranches"]) == 1
    assert len(client.get("/orders").json()) == 1


def test_signal_idempotency_and_risk_totals_are_isolated_per_scope(
    client, sample_buy_payload, monkeypatch
):
    broker = RecordingBroker()
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", lambda cfg: broker)
    settings.max_open_tranches_per_symbol = 1
    settings.max_orders_per_day = 2
    settings.max_symbol_exposure_usdt = 15

    first = client.post("/webhooks/tradingview", json=sample_buy_payload)
    duplicate = client.post("/webhooks/tradingview", json=sample_buy_payload)
    assert first.json()["status"] == "filled"
    assert duplicate.json()["duplicate"] is True

    _set_live_scope(base_url="https://testnet.binance.vision", account_id="uat-one")
    live = client.post("/webhooks/tradingview", json=sample_buy_payload)
    assert live.status_code == 200
    assert live.json()["duplicate"] is False
    assert live.json()["status"] == "filled"
    assert len(broker.submissions) == 2

    second_live_payload = dict(sample_buy_payload)
    second_live_payload["barIndex"] += 1
    second_live_payload["barTime"] += 60_000
    limited = client.post("/webhooks/tradingview", json=second_live_payload)
    assert limited.json()["status"] == "rejected"
    assert "max_orders_per_day" in limited.json()["risk_reason"]


def test_testnet_production_and_accounts_have_separate_fifo_and_reconciliation(
    client, sample_buy_payload, monkeypatch
):
    broker = RecordingBroker()
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", lambda cfg: broker)

    _set_live_scope(base_url="https://testnet.binance.vision", account_id="primary")
    testnet_scope = settings.inventory_scope
    assert (
        client.post("/webhooks/tradingview", json=sample_buy_payload).json()["status"] == "filled"
    )

    _set_live_scope(base_url="https://api.binance.com", account_id="primary")
    production_scope = settings.inventory_scope
    assert production_scope != testnet_scope
    production_sell = client.post(
        "/webhooks/tradingview", json=_sell_payload(sample_buy_payload, bar_index=3)
    )
    assert production_sell.json()["status"] == "rejected"
    reconciliation = client.get("/admin/reconcile/BTCUSDT").json()
    assert reconciliation["inventory_scope"] == production_scope
    assert reconciliation["middleware_open_tranche_count"] == 0
    assert reconciliation["status"] == "OK"

    settings.inventory_account_id = "secondary"
    assert settings.inventory_scope != production_scope
    assert client.get("/positions/BTCUSDT").status_code == 404
    assert len(broker.submissions) == 1
