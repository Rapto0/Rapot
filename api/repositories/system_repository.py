"""Compatibility wrapper for infrastructure system repository."""

from infrastructure.compat import register_wrapper_usage
from infrastructure.repositories.system_repository import (
    get_ops_overview_read_model,
    list_scan_history,
    list_scanner_activity_projection,
)

__all__ = [
    "get_ops_overview_read_model",
    "list_scan_history",
    "list_scanner_activity_projection",
]

register_wrapper_usage(
    wrapper_module="api.repositories.system_repository",
    canonical_module="infrastructure.repositories.system_repository",
    planned_removal="2026-09-30",
)
