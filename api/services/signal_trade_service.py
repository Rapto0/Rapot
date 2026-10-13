"""Compatibility wrapper for application signal/trade services."""

from application.services.signal_trade_service import (
    get_trade_stats_summary,
    list_trades,
)
from infrastructure.compat import register_wrapper_usage

__all__ = [
    "get_trade_stats_summary",
    "list_trades",
]

register_wrapper_usage(
    wrapper_module="api.services.signal_trade_service",
    canonical_module="application.services.signal_trade_service",
    planned_removal="2026-09-30",
)
