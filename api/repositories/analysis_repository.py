"""Compatibility wrapper for infrastructure analysis repository."""

from infrastructure.compat import register_wrapper_usage
from infrastructure.repositories.analysis_repository import (
    get_ai_analysis_by_id,
    get_ai_analysis_by_signal_id,
    list_ai_analyses,
)

__all__ = [
    "get_ai_analysis_by_id",
    "get_ai_analysis_by_signal_id",
    "list_ai_analyses",
]

register_wrapper_usage(
    wrapper_module="api.repositories.analysis_repository",
    canonical_module="infrastructure.repositories.analysis_repository",
    planned_removal="2026-09-30",
)
