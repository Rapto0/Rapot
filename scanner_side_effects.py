"""
Compatibility wrapper for scanner side-effect handlers.

Canonical implementation lives in `application.scanner.signal_handlers`.
"""

from application.scanner.signal_handlers import (
    persist_and_publish_signal,
    persist_and_publish_signal_event,
)
from infrastructure.compat import register_wrapper_usage

__all__ = ["persist_and_publish_signal", "persist_and_publish_signal_event"]

register_wrapper_usage(
    wrapper_module="scanner_side_effects",
    canonical_module="application.scanner.signal_handlers",
    planned_removal="2026-10-31",
)
