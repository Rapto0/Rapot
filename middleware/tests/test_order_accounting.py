from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from unittest.mock import Mock

import pytest
from sqlalchemy.dialects import postgresql

from middleware.broker_adapters.base import BrokerAssetBalance, BrokerOrderResult
from middleware.broker_adapters.binance_spot import BinanceSpotBrokerClient
from middleware.domain.enums import OrderStatus
from middleware.domain.events import BrokerOrderRequestPayload
from middleware.infra.models import Order, SignalEvent, Tranche
from middleware.infra.settings import settings
from middleware.repositories.order_repository import OrderRepository
from middleware.risk.binance_filters import BinanceSymbolRules


def _payload(*, signal_code: str, side: str, bar_index: int, price: str = "50000") -> dict:
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


@dataclass(slots=True)
class AccountingBroker:
    name: str = "BINANCE_SPOT"
    commissions: dict[str, dict[str, Decimal]] = field(default_factory=dict)
    fail_first: bool = False
    commission_complete: bool = True
    tick_size: Decimal = Decimal("0.01")
    submissions: int = 0

    def get_symbol_rules(self, symbol: str) -> BinanceSymbolRules:
        return BinanceSymbolRules(
            symbol=symbol.upper(),
            status="TRADING",
            base_asset="BTC",
            quote_asset="USDT",
            tick_size=self.tick_size,
            min_price=self.tick_size,
            max_price=Decimal("1000000"),
            step_size=Decimal("0.000000000001"),
            min_qty=Decimal("0.000000000001"),
            max_qty=Decimal("1000"),
            min_notional=Decimal("5"),
        )

    def get_asset_balance(self, asset: str) -> Decimal:
        return Decimal("1000")

    def get_asset_balances(self, asset: str) -> BrokerAssetBalance:
        return BrokerAssetBalance(asset=asset, free=Decimal("1000"), locked=Decimal("0"))

    def submit_limit_order(self, payload: BrokerOrderRequestPayload) -> BrokerOrderResult:
        self.submissions += 1
        if self.fail_first and self.submissions == 1:
            return BrokerOrderResult(
                accepted=False,
                status=OrderStatus.FAILED,
                client_order_id=payload.client_order_id,
                message="explicit broker rejection",
            )
        return BrokerOrderResult(
            accepted=True,
            status=OrderStatus.FILLED,
            broker_order_id=f"ACCOUNTING-{self.submissions}",
            client_order_id=payload.client_order_id,
            filled_quantity=payload.quantity,
            avg_fill_price=payload.limit_price,
            commission_by_asset=self.commissions.get(payload.side.value, {}),
            commission_complete=self.commission_complete,
            message="accounting fill",
        )


@pytest.mark.parametrize(
    "commissions,expected_quantity,expected_entry",
    [
        ({"BTC": Decimal("0.000002")}, Decimal("0.001998"), Decimal("50050.05005005005")),
        ({"USDT": Decimal("0.1")}, Decimal("0.002"), Decimal("50050")),
        ({"BNB": Decimal("0.00001")}, Decimal("0.002"), Decimal("50000")),
    ],
)
def test_buy_commission_tracks_base_quote_and_third_asset(
    client,
    monkeypatch,
    commissions,
    expected_quantity,
    expected_entry,
):
    broker = AccountingBroker(commissions={"BUY": commissions})
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", lambda cfg: broker)
    settings.binance_buy_quote_amount_usdt = Decimal("100")
    settings.buy_bps = 0

    response = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_BLS", side="BUY", bar_index=1),
    )

    assert response.json()["status"] == "filled"
    position = client.get("/positions/BTCUSDT").json()
    assert Decimal(position["position"]["total_remaining_quantity"]) == expected_quantity
    assert Decimal(position["tranches"][0]["entry_price"]) == pytest.approx(expected_entry)
    order = client.get("/orders").json()[0]
    assert {asset: Decimal(amount) for asset, amount in order["commission_by_asset"].items()} == (
        commissions
    )
    assert order["commission_complete"] is True
    assert Decimal(order["filled_quantity"]) == Decimal("0.002")


def test_sell_quote_commission_reduces_realized_pnl(client, monkeypatch):
    broker = AccountingBroker(commissions={"SELL": {"USDT": Decimal("0.1")}})
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", lambda cfg: broker)
    settings.binance_buy_quote_amount_usdt = Decimal("100")
    settings.buy_bps = 0
    settings.sell_bps = 0

    client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_BLS", side="BUY", bar_index=2),
    )
    sell = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_PAH", side="SELL", bar_index=3),
    )

    assert sell.json()["status"] == "filled"
    assert client.get("/positions/BTCUSDT").status_code == 404
    sell_order = client.get("/orders").json()[0]
    assert Decimal(sell_order["realized_pnl"]) == Decimal("-0.1")
    assert Decimal(sell_order["commission_by_asset"]["USDT"]) == Decimal("0.1")


def test_unverified_commission_keeps_fill_unknown_and_inventory_unchanged(client, monkeypatch):
    broker = AccountingBroker(commission_complete=False)
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", lambda cfg: broker)

    response = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_BLS", side="BUY", bar_index=11),
    )

    assert response.json()["status"] == "unknown"
    assert "commissions" in response.json()["risk_reason"]
    assert client.get("/positions/BTCUSDT").status_code == 404
    order = client.get("/orders").json()[0]
    assert Decimal(order["filled_quantity"]) == Decimal("0")
    assert order["commission_complete"] is False


def test_daily_order_limit_excludes_candidate_and_risk_rejections(client, monkeypatch):
    broker = AccountingBroker()
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", lambda cfg: broker)
    settings.max_orders_per_day = 1

    rejected_sell = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_PAH", side="SELL", bar_index=4),
    )
    first_buy = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_BLS", side="BUY", bar_index=5),
    )
    second_buy = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_BLS", side="BUY", bar_index=6),
    )

    assert rejected_sell.json()["status"] == "rejected"
    assert first_buy.json()["status"] == "filled"
    assert second_buy.json()["status"] == "rejected"
    assert "max_orders_per_day" in second_buy.json()["risk_reason"]
    assert broker.submissions == 1


def test_zero_daily_order_limit_rejects_first_candidate(client, monkeypatch):
    broker = AccountingBroker()
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", lambda cfg: broker)
    settings.max_orders_per_day = 0

    response = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_BLS", side="BUY", bar_index=7),
    )

    assert response.json()["status"] == "rejected"
    assert "max_orders_per_day" in response.json()["risk_reason"]
    assert broker.submissions == 0


def test_explicit_broker_failure_consumes_daily_attempt(client, monkeypatch):
    broker = AccountingBroker(fail_first=True)
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", lambda cfg: broker)
    settings.max_orders_per_day = 1

    failed = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_BLS", side="BUY", bar_index=8),
    )
    limited = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_BLS", side="BUY", bar_index=9),
    )

    assert failed.json()["status"] == "failed"
    assert limited.json()["status"] == "rejected"
    assert "max_orders_per_day" in limited.json()["risk_reason"]
    assert broker.submissions == 1


def test_supported_price_precision_round_trip(client, monkeypatch):
    broker = AccountingBroker(tick_size=Decimal("0.000000000001"))
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", lambda cfg: broker)
    settings.binance_buy_quote_amount_usdt = Decimal("100")
    settings.buy_bps = 0
    price = Decimal("12345.12345678")

    response = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_BLS", side="BUY", bar_index=10, price=str(price)),
    )

    assert response.json()["status"] == "filled"
    order = client.get("/orders").json()[0]
    assert Decimal(order["limit_price"]) == price
    assert Decimal(client.get("/signals").json()[0]["price"]) == price
    assert Decimal(client.get("/positions/BTCUSDT").json()["tranches"][0]["entry_price"]) == price
    assert Order.__table__.c.limit_price.type.scale == 12
    assert SignalEvent.__table__.c.price.type.scale == 12
    assert Tranche.__table__.c.entry_price.type.scale == 12


def test_binance_full_response_aggregates_commissions():
    result = BinanceSpotBrokerClient(settings)._map_order_response(
        {
            "orderId": 11,
            "clientOrderId": "client-11",
            "status": "FILLED",
            "executedQty": "0.003",
            "cummulativeQuoteQty": "150",
            "fills": [
                {"qty": "0.001", "price": "50000", "commission": "0.01", "commissionAsset": "USDT"},
                {"qty": "0.001", "price": "50000", "commission": "0.02", "commissionAsset": "USDT"},
                {
                    "qty": "0.001",
                    "price": "50000",
                    "commission": "0.0001",
                    "commissionAsset": "BNB",
                },
            ],
        }
    )

    assert result.commission_complete is True
    assert result.commission_by_asset == {
        "USDT": Decimal("0.03"),
        "BNB": Decimal("0.0001"),
    }


def test_daily_risk_uses_postgres_transaction_advisory_lock():
    session = Mock()
    session.get_bind.return_value.dialect.name = "postgresql"
    repository = OrderRepository(session, inventory_scope="LIVE|BINANCE_SPOT|venue|account")

    repository.lock_daily_risk_scope()

    statement = session.execute.call_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "pg_advisory_xact_lock" in sql
