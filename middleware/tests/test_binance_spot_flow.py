from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from middleware.broker_adapters.base import BrokerOrderResult
from middleware.domain.enums import BrokerName, OrderStatus
from middleware.domain.events import BrokerOrderRequestPayload
from middleware.infra.settings import settings
from middleware.risk.binance_filters import BinanceSymbolRules


@dataclass(slots=True)
class FakeBinanceSpotBroker:
    name: str = "BINANCE_SPOT"
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
        assert asset == "USDT"
        return Decimal("1000")

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
            raw_payload={
                "symbol": payload.symbol,
                "side": payload.side.value,
                "quantity": str(quantity),
                "price": str(payload.limit_price),
            },
        )


def _binance_payload(*, signal_code: str, side: str, price: str, bar_index: int) -> dict:
    return {
        "source": "Combo+Hunter",
        "symbol": "BTCUSDT",
        "ticker": "BTCUSDT",
        "signalCode": signal_code,
        "signalText": signal_code,
        "side": side,
        "price": price,
        "timeframe": "1H",
        "barTime": 1713772800000 + (bar_index * 60000),
        "barIndex": bar_index,
        "isRealtime": True,
    }


def test_binance_spot_fixed_usdt_buy_uses_decimal_quantity(client, monkeypatch):
    fake_broker = FakeBinanceSpotBroker()
    monkeypatch.setattr(
        "middleware.api.dependencies.build_broker_client",
        lambda cfg: fake_broker,
    )
    settings.broker_name = BrokerName.BINANCE_SPOT
    settings.binance_buy_quote_amount_usdt = Decimal("50")
    settings.buy_bps = 0

    response = client.post(
        "/webhooks/tradingview",
        json=_binance_payload(
            signal_code="H_BLS",
            side="BUY",
            price="50000",
            bar_index=1,
        ),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "filled"

    order = client.get("/orders").json()[0]
    assert order["broker_name"] == "BINANCE_SPOT"
    assert Decimal(order["quote_budget"]) == Decimal("50.000000000000")
    assert Decimal(order["requested_quantity"]) == Decimal("0.001000000000")
    assert Decimal(order["filled_quantity"]) == Decimal("0.001000000000")
    assert order["base_asset"] == "BTC"
    assert order["quote_asset"] == "USDT"

    position = client.get("/positions/BTCUSDT").json()["position"]
    assert Decimal(position["total_remaining_quantity"]) == Decimal("0.001000000000")


def test_binance_spot_sell_uses_fifo_remaining_quantity(client, monkeypatch):
    fake_broker = FakeBinanceSpotBroker()
    monkeypatch.setattr(
        "middleware.api.dependencies.build_broker_client",
        lambda cfg: fake_broker,
    )
    settings.broker_name = BrokerName.BINANCE_SPOT
    settings.binance_buy_quote_amount_usdt = Decimal("50")
    settings.buy_bps = 0
    settings.sell_bps = 0

    first_buy = client.post(
        "/webhooks/tradingview",
        json=_binance_payload(
            signal_code="H_BLS",
            side="BUY",
            price="50000",
            bar_index=1,
        ),
    )
    assert first_buy.status_code == 200

    second_buy = client.post(
        "/webhooks/tradingview",
        json=_binance_payload(
            signal_code="H_BLS",
            side="BUY",
            price="25000",
            bar_index=2,
        ),
    )
    assert second_buy.status_code == 200

    before_sell = client.get("/positions/BTCUSDT").json()
    oldest_id = before_sell["tranches"][0]["id"]

    sell = client.post(
        "/webhooks/tradingview",
        json=_binance_payload(
            signal_code="H_PAH",
            side="SELL",
            price="51000",
            bar_index=3,
        ),
    )
    assert sell.status_code == 200

    sell_order = client.get("/orders").json()[0]
    assert sell_order["signal_code"] == "H_PAH"
    assert sell_order["target_tranche_id"] == oldest_id
    assert Decimal(sell_order["requested_quantity"]) == Decimal("0.001000000000")

    after_sell = client.get("/positions/BTCUSDT").json()
    assert len(after_sell["tranches"]) == 1
    assert after_sell["tranches"][0]["id"] != oldest_id
    assert Decimal(after_sell["position"]["total_remaining_quantity"]) == Decimal("0.002000000000")
