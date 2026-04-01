"""
Backward-compatible signal repository import surface.

Canonical module: `infrastructure.persistence.signal_repository`.
"""

from infrastructure.compat import register_wrapper_usage
from infrastructure.persistence.signal_repository import *  # noqa: F403

register_wrapper_usage(
    wrapper_module="signal_repository",
    canonical_module="infrastructure.persistence.signal_repository",
    planned_removal="2026-10-31",
)
