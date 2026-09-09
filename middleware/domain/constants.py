from __future__ import annotations

from middleware.domain.enums import Side

TRADINGVIEW_SCHEMA_VERSION = 1

# JSON milliseconds within Python/SQL datetime's supported UTC calendar range.
MAX_EVENT_TIMESTAMP_MS = 253402300799999  # 9999-12-31T23:59:59.999Z
MAX_BAR_INDEX = (1 << 63) - 1  # mw_signal_events.bar_index is a signed BIGINT.

SUPPORTED_SIGNAL_SOURCES = {"Combo+Hunter"}

BUY_SIGNAL_CODES = {"H_BLS", "H_UCZ", "C_BLS", "C_UCZ"}
SELL_SIGNAL_CODES = {"H_PAH", "C_PAH"}
SUPPORTED_SIGNAL_CODES = BUY_SIGNAL_CODES | SELL_SIGNAL_CODES

DEFAULT_SIGNAL_MULTIPLIERS = {
    "H_BLS": 1.00,
    "H_UCZ": 1.00,
    "C_BLS": 1.00,
    "C_UCZ": 1.00,
}

SIGNAL_SIDE_MAP = {
    "H_BLS": Side.BUY,
    "H_UCZ": Side.BUY,
    "C_BLS": Side.BUY,
    "C_UCZ": Side.BUY,
    "H_PAH": Side.SELL,
    "C_PAH": Side.SELL,
}
