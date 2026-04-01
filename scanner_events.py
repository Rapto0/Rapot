"""
Backward-compatible import surface for scanner domain events.

Prefer importing from `domain.events`.
"""

from domain.events.signal_domain_event import SignalDomainEvent
from infrastructure.compat import register_wrapper_usage

__all__ = ["SignalDomainEvent"]

register_wrapper_usage(
    wrapper_module="scanner_events",
    canonical_module="domain.events.signal_domain_event",
    planned_removal="2026-10-31",
)
