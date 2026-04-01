import importlib
import sys

from infrastructure.compat import (
    build_wrapper_usage_summary,
    get_wrapper_usage_snapshot,
    register_wrapper_usage,
    reset_wrapper_usage_snapshot,
)


def _reload_module(module_name: str) -> None:
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
        return
    importlib.import_module(module_name)


def test_register_wrapper_usage_tracks_metadata_and_count():
    reset_wrapper_usage_snapshot()

    register_wrapper_usage(
        wrapper_module="legacy.module",
        canonical_module="canonical.module",
        planned_removal="2026-09-30",
    )
    register_wrapper_usage(
        wrapper_module="legacy.module",
        canonical_module="canonical.module",
        planned_removal="2026-09-30",
    )

    snapshot = get_wrapper_usage_snapshot()
    entry = snapshot["legacy.module"]

    assert entry["wrapper_module"] == "legacy.module"
    assert entry["canonical_module"] == "canonical.module"
    assert entry["planned_removal"] == "2026-09-30"
    assert entry["usage_count"] == 2
    assert isinstance(entry["first_seen_at"], str)
    assert isinstance(entry["last_seen_at"], str)


def test_compatibility_wrappers_register_usage_on_import():
    reset_wrapper_usage_snapshot()

    _reload_module("api.services.analysis_service")
    _reload_module("api.repositories.system_repository")
    _reload_module("signal_repository")

    snapshot = get_wrapper_usage_snapshot()

    assert snapshot["api.services.analysis_service"]["canonical_module"] == (
        "application.services.analysis_service"
    )
    assert snapshot["api.repositories.system_repository"]["canonical_module"] == (
        "infrastructure.repositories.system_repository"
    )
    assert snapshot["signal_repository"]["canonical_module"] == (
        "infrastructure.persistence.signal_repository"
    )

    assert snapshot["api.services.analysis_service"]["usage_count"] >= 1
    assert snapshot["api.repositories.system_repository"]["usage_count"] >= 1
    assert snapshot["signal_repository"]["usage_count"] >= 1


def test_build_wrapper_usage_summary_returns_aggregates_and_sorted_details():
    reset_wrapper_usage_snapshot()

    register_wrapper_usage(
        wrapper_module="w.low",
        canonical_module="c.low",
        planned_removal="2026-10-31",
    )
    register_wrapper_usage(
        wrapper_module="w.high",
        canonical_module="c.high",
        planned_removal="2026-09-30",
    )
    register_wrapper_usage(
        wrapper_module="w.high",
        canonical_module="c.high",
        planned_removal="2026-09-30",
    )

    summary = build_wrapper_usage_summary(include_details=True, detail_limit=2)

    assert summary["total_wrappers"] == 2
    assert summary["active_wrappers"] == 2
    assert summary["total_import_events"] == 3
    assert summary["planned_removal_buckets"] == {"2026-09-30": 1, "2026-10-31": 1}

    details = summary["wrappers"]
    assert isinstance(details, list)
    assert len(details) == 2
    assert details[0]["wrapper_module"] == "w.high"
    assert details[0]["usage_count"] == 2
