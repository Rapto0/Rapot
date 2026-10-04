"""The bot proxy cannot expose personal data around the main API admin boundary."""

from datetime import timedelta

import pytest

import health_api


def _headers(auth, username="admin"):
    return {"Authorization": "Bearer " + auth.create_access_token({"sub": username})}


def _private_read_forbidden(*args, **kwargs):
    pytest.fail("Denied/public health requests must not read personal data")


@pytest.mark.parametrize("path", ["/signals", "/stats", "/metrics", "/future-private-path"])
@pytest.mark.parametrize("identity,expected", [(None, 401), ("user", 403), ("disabled", 403)])
def test_personal_routes_deny_before_repository_access(
    monkeypatch, api_auth_users, path, identity, expected
):
    from infrastructure.persistence import ops_repository, trade_repository

    monkeypatch.setattr(ops_repository, "get_recent_signals", _private_read_forbidden)
    monkeypatch.setattr(ops_repository, "get_trade_stats", _private_read_forbidden)
    monkeypatch.setattr(trade_repository, "list_open_trades", _private_read_forbidden)
    monkeypatch.setattr(health_api, "_load_scanner_counters", _private_read_forbidden)
    with health_api.app.test_client() as client:
        response = client.get(path, headers=_headers(api_auth_users, identity) if identity else {})
    assert response.status_code == expected
    assert response.headers["Cache-Control"] == "private, no-store"
    assert "Authorization" in response.headers["Vary"]


def test_public_status_is_only_local_lifecycle_and_does_not_load_private_details(monkeypatch):
    monkeypatch.setattr(health_api, "_probe_database", lambda: True)
    monkeypatch.setattr(health_api, "_load_scanner_counters", _private_read_forbidden)
    monkeypatch.setattr(health_api, "_load_runtime_state_from_repo", _private_read_forbidden)
    monkeypatch.setattr(
        "infrastructure.compat.build_wrapper_usage_summary", _private_read_forbidden
    )
    monkeypatch.setattr(health_api, "_runtime_lifecycle", {"phase": "unknown", "owner": None})
    health_api.begin_bot_runtime()
    health_api.mark_bot_runtime_running()
    with health_api.app.test_client() as client:
        response = client.get("/status?include_compat_telemetry=true&include_wrapper_details=true")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload.keys() == {"bot", "timestamp"}
    assert payload["bot"]["state"] == "running"
    assert payload["bot"]["state_source"] == "local_lifecycle"
    assert not {"is_scanning", "last_reported_is_running", "last_error"} & payload["bot"].keys()
    assert response.headers["Cache-Control"] == "private, no-store"
    assert "Authorization" in response.headers["Vary"]


@pytest.mark.parametrize("authorization", ["", "Bearer invalid-token", "Basic invalid", "Bearer"])
def test_supplied_invalid_status_auth_cannot_downgrade_to_public(monkeypatch, authorization):
    monkeypatch.setattr(health_api, "_probe_database", _private_read_forbidden)
    with health_api.app.test_client() as client:
        response = client.get("/status", headers={"Authorization": authorization})
    assert response.status_code == 401
    assert response.headers["Cache-Control"] == "private, no-store"
    assert "Authorization" in response.headers["Vary"]


def test_expired_token_is_rejected_before_private_or_status_work(monkeypatch, api_auth_users):
    token = api_auth_users.create_access_token(
        {"sub": "admin"}, expires_delta=timedelta(seconds=-1)
    )
    monkeypatch.setattr(health_api, "_probe_database", _private_read_forbidden)
    with health_api.app.test_client() as client:
        for path in ("/status", "/signals", "/stats", "/metrics"):
            response = client.get(path, headers={"Authorization": "Bearer " + token})
            assert response.status_code == 401
            assert token not in response.get_data(as_text=True)


def test_admin_signals_stats_and_metrics_remain_usable_and_uncacheable(monkeypatch, api_auth_users):
    from infrastructure.persistence import ops_repository, trade_repository
    from price_cache import price_cache

    monkeypatch.setattr(ops_repository, "get_recent_signals", lambda limit: [{"symbol": "FIXTURE"}])
    monkeypatch.setattr(ops_repository, "get_trade_stats", lambda: {"total_trades": 17})
    monkeypatch.setattr(trade_repository, "list_open_trades", lambda: [])
    monkeypatch.setattr(
        price_cache, "get_stats", lambda: {"cache_entries": 0, "hit_rate": 0, "api_calls_saved": 0}
    )
    monkeypatch.setattr(
        health_api,
        "_load_scanner_counters",
        lambda: dict.fromkeys(["total_scans", "total_signals", "sync_scans", "async_scans"], 0),
    )
    with health_api.app.test_client() as client:
        responses = {
            path: client.get(path, headers=_headers(api_auth_users))
            for path in ("/signals", "/stats", "/metrics")
        }
    assert responses["/signals"].get_json()["signals"] == [{"symbol": "FIXTURE"}]
    assert responses["/stats"].get_json()["trading"] == {"total_trades": 17}
    metrics_enabled = any(rule.rule == "/metrics" for rule in health_api.app.url_map.iter_rules())
    for path, response in responses.items():
        assert response.status_code == (404 if path == "/metrics" and not metrics_enabled else 200)
        assert response.headers["Cache-Control"] == "private, no-store"
        assert "Authorization" in response.headers["Vary"]


def test_private_failure_and_unknown_route_do_not_become_cacheable(monkeypatch, api_auth_users):
    from infrastructure.persistence import ops_repository

    def fail(**kwargs):
        raise RuntimeError("synthetic-private-error-detail")

    monkeypatch.setattr(ops_repository, "get_recent_signals", fail)
    with health_api.app.test_client() as client:
        for path, expected in (("/signals", 500), ("/future-private-path", 404)):
            response = client.get(path, headers=_headers(api_auth_users))
            assert response.status_code == expected
            assert response.headers["Cache-Control"] == "private, no-store"
            assert "synthetic-private-error-detail" not in response.get_data(as_text=True)


def test_public_health_probe_keeps_service_unhealthy_status(monkeypatch):
    monkeypatch.setattr(health_api, "_probe_database", lambda: False)
    with health_api.app.test_client() as client:
        response = client.get("/health")
        status = client.get("/status").get_json()
    assert response.status_code == 503 and response.get_json()["status"] == "unhealthy"
    assert status["bot"]["state"] == "unknown"
    assert status["bot"]["state_source"] == "unavailable"
