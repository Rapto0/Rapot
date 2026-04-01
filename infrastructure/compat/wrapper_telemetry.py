from __future__ import annotations

import time
from copy import deepcopy
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from logger import get_logger

logger = get_logger(__name__)

_WARNING_RATE_LIMIT_SECONDS = 15 * 60.0
_WARNING_SAMPLE_COUNTS = {1, 5, 10, 25, 50, 100}
_usage_lock = Lock()
_last_warning_at: dict[str, float] = {}
_wrapper_usage: dict[str, dict[str, Any]] = {}


def register_wrapper_usage(
    *,
    wrapper_module: str,
    canonical_module: str,
    planned_removal: str,
) -> None:
    """
    Record runtime usage of a compatibility wrapper module.
    """
    now_epoch = time.time()
    now_iso = datetime.now(UTC).isoformat()

    with _usage_lock:
        entry = _wrapper_usage.get(wrapper_module)
        if entry is None:
            entry = {
                "wrapper_module": wrapper_module,
                "canonical_module": canonical_module,
                "planned_removal": planned_removal,
                "usage_count": 0,
                "first_seen_at": now_iso,
                "last_seen_at": now_iso,
            }
            _wrapper_usage[wrapper_module] = entry

        entry["usage_count"] = int(entry["usage_count"]) + 1
        entry["last_seen_at"] = now_iso
        usage_count = int(entry["usage_count"])

        last_warning_at = float(_last_warning_at.get(wrapper_module, 0.0))
        should_warn = usage_count in _WARNING_SAMPLE_COUNTS
        if not should_warn and now_epoch - last_warning_at >= _WARNING_RATE_LIMIT_SECONDS:
            should_warn = True
        if should_warn:
            _last_warning_at[wrapper_module] = now_epoch

    if should_warn:
        logger.warning(
            (
                "Deprecated compatibility wrapper used: %s -> %s "
                "(planned_removal=%s, usage_count=%s)"
            ),
            wrapper_module,
            canonical_module,
            planned_removal,
            usage_count,
        )


def get_wrapper_usage_snapshot() -> dict[str, dict[str, Any]]:
    """
    Return a deep-copied, deterministic snapshot for diagnostics/tests.
    """
    with _usage_lock:
        items = sorted(_wrapper_usage.items(), key=lambda x: x[0])
        return {key: deepcopy(value) for key, value in items}


def build_wrapper_usage_summary(
    *,
    include_details: bool = False,
    detail_limit: int = 20,
) -> dict[str, Any]:
    """
    Build a read-model friendly summary from in-memory wrapper telemetry.
    """
    snapshot = get_wrapper_usage_snapshot()
    rows = list(snapshot.values())

    total_wrappers = len(rows)
    active_wrappers = sum(1 for row in rows if int(row.get("usage_count") or 0) > 0)
    total_import_events = sum(int(row.get("usage_count") or 0) for row in rows)

    planned_removal_buckets: dict[str, int] = {}
    for row in rows:
        planned_removal = str(row.get("planned_removal") or "unknown")
        planned_removal_buckets[planned_removal] = (
            int(planned_removal_buckets.get(planned_removal, 0)) + 1
        )

    summary: dict[str, Any] = {
        "total_wrappers": int(total_wrappers),
        "active_wrappers": int(active_wrappers),
        "total_import_events": int(total_import_events),
        "planned_removal_buckets": dict(sorted(planned_removal_buckets.items())),
    }

    if include_details:
        sorted_rows = sorted(
            rows,
            key=lambda row: (
                -int(row.get("usage_count") or 0),
                str(row.get("wrapper_module") or ""),
            ),
        )
        trimmed_rows = sorted_rows[: max(1, int(detail_limit))]
        summary["wrappers"] = [
            {
                "wrapper_module": str(row.get("wrapper_module") or ""),
                "canonical_module": str(row.get("canonical_module") or ""),
                "usage_count": int(row.get("usage_count") or 0),
                "planned_removal": str(row.get("planned_removal") or ""),
                "first_seen_at": row.get("first_seen_at"),
                "last_seen_at": row.get("last_seen_at"),
            }
            for row in trimmed_rows
        ]

    return summary


def reset_wrapper_usage_snapshot() -> None:
    """
    Reset in-memory telemetry (test-only helper).
    """
    with _usage_lock:
        _wrapper_usage.clear()
        _last_warning_at.clear()
