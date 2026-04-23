from __future__ import annotations

from middleware.domain.enums import Side

TRADINGVIEW_SCHEMA_VERSION = 1

SUPPORTED_SIGNAL_SOURCES = {"Combo+Hunter"}

BUY_SIGNAL_CODES = {"H_BLS", "H_UCZ", "C_BLS", "C_UCZ"}
SELL_SIGNAL_CODES = {"H_PAH", "C_PAH"}
SUPPORTED_SIGNAL_CODES = BUY_SIGNAL_CODES | SELL_SIGNAL_CODES

DEFAULT_SIGNAL_MULTIPLIERS = {
    "H_BLS": 1.00,
    "H_UCZ": 0.50,
    "C_BLS": 1.00,
    "C_UCZ": 0.50,
}

SIGNAL_SIDE_MAP = {
    "H_BLS": Side.BUY,
    "H_UCZ": Side.BUY,
    "C_BLS": Side.BUY,
    "C_UCZ": Side.BUY,
    "H_PAH": Side.SELL,
    "C_PAH": Side.SELL,
}
