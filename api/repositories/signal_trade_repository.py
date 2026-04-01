"""Compatibility wrapper for infrastructure signal/trade repository."""

from infrastructure.compat import register_wrapper_usage
from infrastructure.repositories.signal_trade_repository import (
    get_signal_by_id,
    get_trade_stats_aggregate,
    list_signals,
    list_trades,
)

__all__ = [
    "get_signal_by_id",
    "get_trade_stats_aggregate",
    "list_signals",
    "list_trades",
]

register_wrapper_usage(
    wrapper_module="api.repositories.signal_trade_repository",
    canonical_module="infrastructure.repositories.signal_trade_repository",
    planned_removal="2026-09-30",
)
