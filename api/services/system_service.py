"""Compatibility wrapper for application system services."""

from application.services.system_service import (
    get_ops_overview,
    list_recent_scans,
    list_scanner_activity,
)
from infrastructure.compat import register_wrapper_usage

__all__ = [
    "get_ops_overview",
    "list_recent_scans",
    "list_scanner_activity",
]

register_wrapper_usage(
    wrapper_module="api.services.system_service",
    canonical_module="application.services.system_service",
    planned_removal="2026-09-30",
)
