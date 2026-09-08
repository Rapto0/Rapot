from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import Any

import pytest

from middleware.broker_adapters.base import BrokerOrderResult
from middleware.domain.enums import OrderStatus
from middleware.domain.events import BrokerOrderRequestPayload
from middleware.infra.settings import settings
from middleware.risk.binance_filters import BinanceSymbolRules
from middleware.tests.test_order_accounting import AccountingBroker, _payload


@dataclass(slots=True)
class SnapshotBroker(AccountingBroker):
    result_overrides: dict[str, Any] = field(default_factory=dict)
    recovery_result: BrokerOrderResult | None = None
    quantity_step_size: Decimal = Decimal("0.000000000001")

    def get_symbol_rules(self, symbol: str) -> BinanceSymbolRules:
        return replace(
            AccountingBroker.get_symbol_rules(self, symbol),
            step_size=self.quantity_step_size,
            min_qty=self.quantity_step_size,
        )

    def submit_limit_order(self, payload: BrokerOrderRequestPayload) -> BrokerOrderResult:
        result = AccountingBroker.submit_limit_order(self, payload)
        for attribute, value in self.result_overrides.items():
            setattr(result, attribute, value)
        return result

    def get_order_by_client_id(self, symbol: str, client_order_id: str) -> BrokerOrderResult:
        assert self.recovery_result is not None
        return self.recovery_result


@pytest.mark.parametrize(
    "field_name,value",
    [
        ("filled_lots", Decimal("NaN")),
        ("filled_quantity", Decimal("NaN")),
        ("filled_quantity", Decimal("Infinity")),
        ("avg_fill_price", Decimal("NaN")),
        ("avg_fill_price", Decimal("Infinity")),
        ("avg_fill_price", Decimal("0")),
        ("avg_fill_price", Decimal("-1")),
        ("commission_by_asset", {"USDT": Decimal("NaN")}),
        ("commission_by_asset", {"USDT": Decimal("Infinity")}),
    ],
)
def test_invalid_accounting_values_remain_unknown_without_inventory(
    client, monkeypatch, field_name, value
):
    broker = SnapshotBroker(result_overrides={field_name: value})
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", lambda cfg: broker)

    response = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_BLS", side="BUY", bar_index=100),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "unknown"
    assert client.get("/positions/BTCUSDT").status_code == 404
    order = client.get("/orders").json()[0]
    assert Decimal(order["filled_quantity"]) == Decimal("0")
    assert order["commission_by_asset"] == {}


def test_missing_previously_accounted_fee_asset_quarantines_cumulative_snapshot(
    client, monkeypatch
):
    broker = SnapshotBroker(
        result_overrides={
            "status": OrderStatus.PARTIALLY_FILLED,
            "filled_quantity": Decimal("0.001"),
            "avg_fill_price": Decimal("50000"),
            "commission_by_asset": {"USDT": Decimal("0.01")},
        },
        recovery_result=BrokerOrderResult(
            accepted=True,
            status=OrderStatus.FILLED,
            filled_quantity=Decimal("0.002"),
            avg_fill_price=Decimal("50000"),
            commission_by_asset={"BNB": Decimal("0.0001")},
        ),
    )
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", lambda cfg: broker)
    settings.binance_buy_quote_amount_usdt = Decimal("100")
    settings.buy_bps = 0
    initial = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_BLS", side="BUY", bar_index=101),
    ).json()
    previous_position = client.get("/positions/BTCUSDT").json()

    recovered = client.post(f"/admin/recover-order/{initial['order_id']}")

    assert recovered.status_code == 200
    assert recovered.json()["status"] == "unknown"
    assert client.get("/positions/BTCUSDT").json() == previous_position
    order = client.get("/orders").json()[0]
    assert Decimal(order["filled_quantity"]) == Decimal("0.001")
    assert {asset: Decimal(fee) for asset, fee in order["commission_by_asset"].items()} == {
        "USDT": Decimal("0.01")
    }


def test_sell_fee_is_checked_against_new_fill_proceeds_before_accounting(client, monkeypatch):
    broker = SnapshotBroker()
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", lambda cfg: broker)
    settings.binance_buy_quote_amount_usdt = Decimal("100")
    settings.buy_bps = 0
    settings.sell_bps = 0
    client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_BLS", side="BUY", bar_index=102),
    )
    broker.result_overrides = {
        "status": OrderStatus.PARTIALLY_FILLED,
        "filled_quantity": Decimal("0.001"),
        "avg_fill_price": Decimal("50000"),
        "commission_by_asset": {"USDT": Decimal("0.01")},
    }
    initial_sell = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_PAH", side="SELL", bar_index=103),
    ).json()
    previous_position = client.get("/positions/BTCUSDT").json()
    broker.recovery_result = BrokerOrderResult(
        accepted=True,
        status=OrderStatus.FILLED,
        filled_quantity=Decimal("0.002"),
        avg_fill_price=Decimal("25000.5"),
        commission_by_asset={"USDT": Decimal("0.012")},
    )

    recovered = client.post(f"/admin/recover-order/{initial_sell['order_id']}")

    assert recovered.status_code == 200
    assert recovered.json()["status"] == "unknown"
    assert "commission exceeds the sell proceeds" in recovered.json()["risk_reason"]
    assert client.get("/positions/BTCUSDT").json() == previous_position
    order = client.get("/orders").json()[0]
    assert Decimal(order["filled_quantity"]) == Decimal("0.001")
    assert Decimal(order["realized_pnl"]) == Decimal("-0.01")


@pytest.mark.parametrize("cumulative_price", ["24999", "25000"])
def test_new_fill_requires_an_increase_in_cumulative_notional(
    client, monkeypatch, cumulative_price
):
    broker = SnapshotBroker(
        result_overrides={
            "status": OrderStatus.PARTIALLY_FILLED,
            "filled_quantity": Decimal("0.001"),
            "avg_fill_price": Decimal("50000"),
        },
        recovery_result=BrokerOrderResult(
            accepted=True,
            status=OrderStatus.FILLED,
            filled_quantity=Decimal("0.002"),
            avg_fill_price=Decimal(cumulative_price),
        ),
    )
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", lambda cfg: broker)
    settings.binance_buy_quote_amount_usdt = Decimal("100")
    settings.buy_bps = 0
    initial = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_BLS", side="BUY", bar_index=104),
    ).json()
    previous_position = client.get("/positions/BTCUSDT").json()

    recovered = client.post(f"/admin/recover-order/{initial['order_id']}")

    assert recovered.status_code == 200
    assert recovered.json()["status"] == "unknown"
    assert "cumulative fill value" in recovered.json()["risk_reason"]
    assert client.get("/positions/BTCUSDT").json() == previous_position


def test_fifo_preserves_fee_dust_and_sells_next_tranche_above_exchange_minimum(client, monkeypatch):
    broker = SnapshotBroker(
        commissions={"BUY": {"BTC": Decimal("0.00000003")}},
        quantity_step_size=Decimal("0.000001"),
    )
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", lambda cfg: broker)
    settings.binance_buy_quote_amount_usdt = Decimal("100")
    settings.buy_bps = 0
    settings.sell_bps = 0
    first_buy = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_BLS", side="BUY", bar_index=105),
    ).json()
    first_sell = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_PAH", side="SELL", bar_index=106),
    ).json()
    assert first_buy["status"] == first_sell["status"] == "filled"
    dust_position = client.get("/positions/BTCUSDT").json()
    dust_id = dust_position["tranches"][0]["id"]
    dust_quantity = Decimal(dust_position["position"]["total_remaining_quantity"])
    assert dust_quantity > 0

    broker.commissions = {}
    second_buy = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_BLS", side="BUY", bar_index=107),
    ).json()
    second_sell = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_PAH", side="SELL", bar_index=108),
    ).json()

    assert second_buy["status"] == second_sell["status"] == "filled"
    remaining = client.get("/positions/BTCUSDT").json()
    assert len(remaining["tranches"]) == 1
    assert remaining["tranches"][0]["id"] == dust_id
    assert Decimal(remaining["position"]["total_remaining_quantity"]) == dust_quantity
    assert broker.submissions == 4


def test_fifo_retains_partial_fill_below_minimum_notional_and_sells_next_tranche(
    client, monkeypatch
):
    broker = SnapshotBroker(
        result_overrides={
            "status": OrderStatus.CANCELLED,
            "filled_quantity": Decimal("0.00001"),
            "commission_by_asset": {"BTC": Decimal("0.00000001")},
        },
        quantity_step_size=Decimal("0.000001"),
    )
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", lambda cfg: broker)
    settings.binance_buy_quote_amount_usdt = Decimal("100")
    settings.buy_bps = 0
    settings.sell_bps = 0
    initial = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_BLS", side="BUY", bar_index=109),
    )
    assert initial.json()["status"] == "cancelled"
    dust_position = client.get("/positions/BTCUSDT").json()
    dust_id = dust_position["tranches"][0]["id"]
    dust_quantity = Decimal(dust_position["position"]["total_remaining_quantity"])
    assert dust_quantity > broker.quantity_step_size

    broker.result_overrides = {}
    second_buy = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_BLS", side="BUY", bar_index=110),
    )
    sell = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_PAH", side="SELL", bar_index=111),
    )

    assert second_buy.json()["status"] == sell.json()["status"] == "filled"
    remaining = client.get("/positions/BTCUSDT").json()
    assert len(remaining["tranches"]) == 1
    assert remaining["tranches"][0]["id"] == dust_id
    assert Decimal(remaining["position"]["total_remaining_quantity"]) == dust_quantity
    assert broker.submissions == 3
