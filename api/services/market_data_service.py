"""Compatibility wrapper for application market data services."""

from application.services.market_data_service import (
    build_candles_payload,
    build_market_indices_payload,
    build_market_metrics_payload,
    build_market_overview_payload,
    build_market_ticker_payload,
)
from infrastructure.compat import register_wrapper_usage

__all__ = [
    "build_candles_payload",
    "build_market_indices_payload",
    "build_market_metrics_payload",
    "build_market_overview_payload",
    "build_market_ticker_payload",
]

register_wrapper_usage(
    wrapper_module="api.services.market_data_service",
    canonical_module="application.services.market_data_service",
    planned_removal="2026-09-30",
)
