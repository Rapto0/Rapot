from __future__ import annotations

from decimal import Decimal

from middleware.risk.binance_filters import BinanceSymbolRules


def _raw_symbol():
    return {
        "symbol": "BTCUSDT",
        "status": "TRADING",
        "baseAsset": "BTC",
        "quoteAsset": "USDT",
        "filters": [
            {
                "filterType": "PRICE_FILTER",
                "minPrice": "0.01000000",
                "maxPrice": "1000000.00000000",
                "tickSize": "0.01000000",
            },
            {
                "filterType": "LOT_SIZE",
                "minQty": "0.00001000",
                "maxQty": "9000.00000000",
                "stepSize": "0.00001000",
            },
            {
                "filterType": "MIN_NOTIONAL",
                "minNotional": "5.00000000",
            },
        ],
    }


def test_binance_symbol_rules_parse_and_round_decimal_filters():
    rules = BinanceSymbolRules.from_exchange_info_symbol(_raw_symbol())

    assert rules.base_asset == "BTC"
    assert rules.quote_asset == "USDT"
    assert rules.round_buy_price(Decimal("64123.451")) == Decimal("64123.46")
    assert rules.round_sell_price(Decimal("64123.459")) == Decimal("64123.45")
    assert rules.floor_quantity(Decimal("0.00123456")) == Decimal("0.00123000")


def test_binance_symbol_rules_validate_min_notional_and_step_size():
    rules = BinanceSymbolRules.from_exchange_info_symbol(_raw_symbol())

    assert (
        rules.validate_limit_order(
            price=Decimal("64123.45"),
            quantity=Decimal("0.00001000"),
        )
        == "Binance notional below minimum (5.00000000)"
    )

    assert (
        rules.validate_limit_order(
            price=Decimal("64123.45"),
            quantity=Decimal("0.00123000"),
        )
        is None
    )
