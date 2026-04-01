"""
Backward-compatible ops repository import surface.

Canonical module: `infrastructure.persistence.ops_repository`.
"""

from infrastructure.compat import register_wrapper_usage
from infrastructure.persistence.ops_repository import *  # noqa: F403

register_wrapper_usage(
    wrapper_module="ops_repository",
    canonical_module="infrastructure.persistence.ops_repository",
    planned_removal="2026-10-31",
)
