"""Compatibility wrapper for application analysis services."""

from application.services.analysis_service import (
    get_ai_analysis_by_id,
    get_ai_analysis_by_signal_id,
    list_ai_analyses,
)
from infrastructure.compat import register_wrapper_usage

__all__ = [
    "get_ai_analysis_by_id",
    "get_ai_analysis_by_signal_id",
    "list_ai_analyses",
]

register_wrapper_usage(
    wrapper_module="api.services.analysis_service",
    canonical_module="application.services.analysis_service",
    planned_removal="2026-09-30",
)
