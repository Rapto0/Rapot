from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from middleware.broker_adapters.base import BrokerAssetBalance, BrokerOrderResult
from middleware.domain.enums import OrderStatus
from middleware.domain.events import BrokerOrderRequestPayload
from middleware.risk.binance_filters import BinanceSymbolRules


@dataclass(slots=True)
class ReconciliationBroker:
    name: str = "BINANCE_SPOT"
    free: Decimal = Decimal("0")
    locked: Decimal = Decimal("0")
    rules: BinanceSymbolRules = field(init=False)

    def __post_init__(self) -> None:
        self.rules = BinanceSymbolRules(
            symbol="BTCUSDT",
            status="TRADING",
            base_asset="BTC",
            quote_asset="USDT",
            tick_size=Decimal("0.01"),
            min_price=Decimal("0.01"),
            max_price=Decimal("1000000"),
            step_size=Decimal("0.000001"),
            min_qty=Decimal("0.000001"),
            max_qty=Decimal("1000"),
            min_notional=Decimal("5"),
        )

    def get_symbol_rules(self, symbol: str) -> BinanceSymbolRules:
        assert symbol == "BTCUSDT"
        return self.rules

    def get_asset_balance(self, asset: str) -> Decimal:
        assert asset == "BTC"
        return self.free

    def get_asset_balances(self, asset: str) -> BrokerAssetBalance:
        assert asset == "BTC"
        return BrokerAssetBalance(asset=asset, free=self.free, locked=self.locked)

    def submit_limit_order(self, payload: BrokerOrderRequestPayload) -> BrokerOrderResult:
        quantity = payload.quantity or Decimal("0")
        return BrokerOrderResult(
            accepted=True,
            status=OrderStatus.FILLED,
            broker_order_id=f"BN-{payload.idempotency_key[:8]}",
            filled_lots=0,
            filled_quantity=quantity,
            avg_fill_price=payload.limit_price,
            message="fake Binance fill",
            raw_payload={},
        )


def _open_one_tranche(client, sample_buy_payload) -> Decimal:
    response = client.post("/webhooks/tradingview", json=sample_buy_payload)
    assert response.status_code == 200
    assert response.json()["status"] == "filled"
    position = client.get("/positions/BTCUSDT").json()["position"]
    return Decimal(position["total_remaining_quantity"])


def test_reconciliation_ok_when_binance_balance_matches_middleware(
    client, sample_buy_payload, monkeypatch
):
    broker = ReconciliationBroker()
    monkeypatch.setattr(
        "middleware.api.dependencies.build_broker_client",
        lambda cfg: broker,
    )
    remaining_quantity = _open_one_tranche(client, sample_buy_payload)
    broker.free = remaining_quantity

    response = client.get("/admin/reconcile/BTCUSDT")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "OK"
    assert body["sell_ready"] is True
    assert Decimal(body["middleware_remaining_quantity"]) == remaining_quantity
    assert Decimal(body["total_delta_quantity"]) == Decimal("0")


def test_reconciliation_detects_missing_binance_balance(client, sample_buy_payload, monkeypatch):
    broker = ReconciliationBroker()
    monkeypatch.setattr(
        "middleware.api.dependencies.build_broker_client",
        lambda cfg: broker,
    )
    remaining_quantity = _open_one_tranche(client, sample_buy_payload)
    broker.free = Decimal("0")

    response = client.get("/admin/reconcile/BTCUSDT")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "MISMATCH"
    assert body["sell_ready"] is False
    assert Decimal(body["middleware_remaining_quantity"]) == remaining_quantity
    assert Decimal(body["total_delta_quantity"]) < 0


def test_reconciliation_flags_locked_balance(client, sample_buy_payload, monkeypatch):
    broker = ReconciliationBroker()
    monkeypatch.setattr(
        "middleware.api.dependencies.build_broker_client",
        lambda cfg: broker,
    )
    remaining_quantity = _open_one_tranche(client, sample_buy_payload)
    broker.free = Decimal("0")
    broker.locked = remaining_quantity

    response = client.get("/admin/reconcile/BTCUSDT")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "LOCKED_BALANCE"
    assert body["sell_ready"] is False
    assert Decimal(body["total_delta_quantity"]) == Decimal("0")
