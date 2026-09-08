from decimal import Decimal

import pytest

from middleware.broker_adapters.binance_spot import BinanceSpotBrokerClient
from middleware.infra.settings import settings


def _trade(trade_id: int, **changes) -> dict:
    return {
        "symbol": "BTCUSDT",
        "orderId": 42,
        "id": trade_id,
        "qty": "0.001",
        "price": "50000",
        "commission": "0.000001",
        "commissionAsset": "BTC",
        **changes,
    }


def _order(quantity: str = "0.002", **changes) -> dict:
    return {
        "symbol": "BTCUSDT",
        "orderId": 42,
        "clientOrderId": "recovery-id",
        "status": "FILLED",
        "executedQty": quantity,
        "cummulativeQuoteQty": str(Decimal(quantity) * Decimal("50000")),
        **changes,
    }


@pytest.mark.parametrize(
    "trades",
    [
        [],
        [_trade(1)],  # Truncated history must not imply complete commissions.
        [_trade(1), _trade(1)],
        [_trade(1), _trade(2, orderId=43)],
        [_trade(1), _trade(2, symbol="ETHUSDT")],
        [_trade(1), _trade(2, commissionAsset="")],
        [_trade(1), _trade(2, commission="NaN")],
        [_trade(1), _trade(2, commission=None)],
    ],
)
def test_incomplete_or_invalid_trade_history_is_not_accountable(monkeypatch, trades):
    def signed_request(self, method, path, params):
        return _order() if path == "/api/v3/order" else trades

    monkeypatch.setattr(BinanceSpotBrokerClient, "_signed_request", signed_request)
    result = BinanceSpotBrokerClient(settings).get_order_by_client_id("BTCUSDT", "recovery-id")

    assert result.commission_complete is False
    assert result.execution_uncertain is True
    assert result.commission_by_asset == {}


def test_recovery_paginates_from_first_trade_and_verifies_complete_quantity(monkeypatch):
    cursors = []

    def signed_request(self, method, path, params):
        if path == "/api/v3/order":
            return _order("1.001")
        assert params["orderId"] == "42"
        assert params["limit"] == 1000
        cursors.append(params["fromId"])
        if params["fromId"] == 0:
            return [_trade(i) for i in range(1, 1001)]
        return [_trade(1001)]

    monkeypatch.setattr(BinanceSpotBrokerClient, "_signed_request", signed_request)
    result = BinanceSpotBrokerClient(settings).get_order_by_client_id("BTCUSDT", "recovery-id")

    assert cursors == [0, 1001]
    assert result.commission_complete is True
    assert result.commission_by_asset == {"BTC": Decimal("0.001001")}


@pytest.mark.parametrize("fills", [[], [_trade(1)], [{"qty": "0.002", "price": "50000"}]])
def test_full_response_needs_fees_covering_all_executed_quantity(fills):
    result = BinanceSpotBrokerClient(settings)._map_order_response(_order(fills=fills))

    assert result.commission_complete is False


def test_average_uses_cumulative_notional_instead_of_a_truncated_fill_list():
    result = BinanceSpotBrokerClient(settings)._map_order_response(
        _order(fills=[_trade(1, price="40000")])
    )

    assert result.avg_fill_price == Decimal("50000")
    assert result.commission_complete is False
