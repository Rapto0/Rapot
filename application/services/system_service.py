from __future__ import annotations

from typing import Any

from infrastructure.compat import build_wrapper_usage_summary
from infrastructure.repositories.system_repository import (
    get_ops_overview_read_model as repo_get_ops_overview_read_model,
)
from infrastructure.repositories.system_repository import (
    list_scan_history as repo_list_scan_history,
)
from infrastructure.repositories.system_repository import (
    list_scanner_activity_projection as repo_list_scanner_activity_projection,
)
from settings import settings


def list_recent_scans(limit: int) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 500))
    return repo_list_scan_history(safe_limit)


def get_ops_overview(
    *,
    include_compat_telemetry: bool = False,
    include_wrapper_details: bool = False,
) -> dict[str, Any]:
    payload = repo_get_ops_overview_read_model()
    if not include_compat_telemetry:
        return payload

    app_env = str(settings.app_env or "production").strip().lower()
    details_included = bool(include_wrapper_details and app_env != "production")

    telemetry = build_wrapper_usage_summary(
        include_details=details_included,
        detail_limit=20,
    )
    telemetry["details_requested"] = bool(include_wrapper_details)
    telemetry["details_included"] = bool(details_included)
    if include_wrapper_details and not details_included:
        telemetry["details_hidden_reason"] = "details_disabled_in_production"

    payload["compatibility_wrappers"] = telemetry
    return payload


def list_scanner_activity(limit: int) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 500))
    return repo_list_scanner_activity_projection(safe_limit)
