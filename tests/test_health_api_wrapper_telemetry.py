import health_api


def _mock_scanner_counters():
    return {
        "sync_scans": 1,
        "sync_signals": 2,
        "async_scans": 3,
        "async_signals": 4,
        "total_scans": 4,
        "total_signals": 6,
        "last_updated": "2026-03-30T10:00:00",
    }


def _mock_runtime_state():
    return {
        "is_running": True,
        "is_scanning": False,
        "last_scan_time": "2026-03-30T10:00:00",
        "error_count": 0,
        "last_error": None,
    }


def test_health_status_excludes_wrapper_telemetry_by_default(monkeypatch):
    monkeypatch.setattr(health_api, "_probe_database", lambda: True)
    monkeypatch.setattr(health_api, "_load_scanner_counters", _mock_scanner_counters)
    monkeypatch.setattr(health_api, "_load_runtime_state_from_repo", _mock_runtime_state)

    with health_api.app.test_client() as client:
        response = client.get("/status")

    assert response.status_code == 200
    payload = response.get_json()
    assert "compatibility_wrappers" not in payload


def test_health_status_can_include_wrapper_telemetry(monkeypatch):
    monkeypatch.setattr(health_api, "_probe_database", lambda: True)
    monkeypatch.setattr(health_api, "_load_scanner_counters", _mock_scanner_counters)
    monkeypatch.setattr(health_api, "_load_runtime_state_from_repo", _mock_runtime_state)
    monkeypatch.setattr("settings.settings.app_env", "production")
    monkeypatch.setattr(
        "infrastructure.compat.build_wrapper_usage_summary",
        lambda **_kwargs: {
            "total_wrappers": 2,
            "active_wrappers": 1,
            "total_import_events": 5,
            "planned_removal_buckets": {"2026-09-30": 2},
            "wrappers": [{"wrapper_module": "legacy.path", "usage_count": 5}],
        },
    )

    with health_api.app.test_client() as client:
        response = client.get("/status?include_compat_telemetry=true&include_wrapper_details=true")

    assert response.status_code == 200
    payload = response.get_json()
    telemetry = payload["compatibility_wrappers"]
    assert telemetry["total_wrappers"] == 2
    assert telemetry["details_requested"] is True
    assert telemetry["details_included"] is False
    assert telemetry["details_hidden_reason"] == "details_disabled_in_production"
