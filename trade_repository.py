"""
Backward-compatible trade repository import surface.

Canonical module: `infrastructure.persistence.trade_repository`.
"""

from infrastructure.compat import register_wrapper_usage
from infrastructure.persistence.trade_repository import *  # noqa: F403

register_wrapper_usage(
    wrapper_module="trade_repository",
    canonical_module="infrastructure.persistence.trade_repository",
    planned_removal="2026-10-31",
)
