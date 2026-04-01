import pytest
from starlette.requests import Request

import api.main as api_main
from api.routes import system_routes
from application.services import system_service


def _request_stub(path: str) -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
        "app": api_main.app,
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_ops_overview_read_model_endpoint_shape(monkeypatch):
    monkeypatch.setattr(
        "application.services.system_service.get_ops_overview",
        lambda **_kwargs: {
            "total_signals": 12,
            "total_trades": 8,
            "open_trades": 3,
            "total_scans": 44,
            "total_pnl": 1250.5,
            "last_signal_at": "2026-03-29T19:00:00",
            "last_trade_at": "2026-03-29T18:59:00",
            "last_scan_at": "2026-03-29T18:58:00",
        },
    )

    payload = await system_routes.get_ops_overview_read_model(
        _request_stub("/ops/read-model/overview")
    )

    assert payload.total_signals == 12
    assert payload.total_trades == 8
    assert payload.open_trades == 3
    assert payload.total_scans == 44
    assert payload.total_pnl == 1250.5


@pytest.mark.asyncio
async def test_ops_overview_read_model_can_include_wrapper_telemetry(monkeypatch):
    monkeypatch.setattr(
        "application.services.system_service.get_ops_overview",
        lambda **kwargs: {
            "total_signals": 4,
            "total_trades": 2,
            "open_trades": 1,
            "total_scans": 20,
            "total_pnl": 15.2,
            "last_signal_at": "2026-03-29T19:00:00",
            "last_trade_at": "2026-03-29T18:59:00",
            "last_scan_at": "2026-03-29T18:58:00",
            "compatibility_wrappers": {
                "total_wrappers": 7,
                "active_wrappers": 3,
                "total_import_events": 9,
                "planned_removal_buckets": {"2026-09-30": 4, "2026-10-31": 3},
                "details_requested": bool(kwargs.get("include_wrapper_details")),
                "details_included": False,
                "details_hidden_reason": "details_disabled_in_production",
                "wrappers": None,
            },
        },
    )

    payload = await system_routes.get_ops_overview_read_model(
        _request_stub("/ops/read-model/overview"),
        include_compat_telemetry=True,
        include_wrapper_details=True,
    )

    assert payload.compatibility_wrappers is not None
    assert payload.compatibility_wrappers.total_wrappers == 7
    assert payload.compatibility_wrappers.details_requested is True
    assert payload.compatibility_wrappers.details_included is False


@pytest.mark.asyncio
async def test_scanner_activity_read_model_endpoint_shape(monkeypatch):
    monkeypatch.setattr(
        "application.services.system_service.list_scanner_activity",
        lambda limit: [
            {
                "item_type": "signal",
                "item_id": "101",
                "symbol": "THYAO",
                "market_type": "BIST",
                "strategy": "HUNTER",
                "action": "AL",
                "timeframe": "1D",
                "status": None,
                "numeric_value": 302.15,
                "created_at": "2026-03-29T19:10:00",
            },
            {
                "item_type": "scan",
                "item_id": "77",
                "symbol": None,
                "market_type": None,
                "strategy": "sync",
                "action": "BIST",
                "timeframe": None,
                "status": None,
                "numeric_value": 14.2,
                "created_at": "2026-03-29T19:09:00",
            },
        ],
    )

    payload = await system_routes.get_scanner_activity_read_model(
        _request_stub("/ops/read-model/scanner-feed"),
        limit=20,
    )

    assert len(payload) == 2
    assert payload[0].item_type == "signal"
    assert payload[0].symbol == "THYAO"
    assert payload[1].item_type == "scan"
    assert payload[1].strategy == "sync"


def test_ops_overview_service_hides_wrapper_details_in_production(monkeypatch):
    monkeypatch.setattr(
        system_service,
        "repo_get_ops_overview_read_model",
        lambda: {
            "total_signals": 1,
            "total_trades": 1,
            "open_trades": 0,
            "total_scans": 5,
            "total_pnl": 0.0,
            "last_signal_at": None,
            "last_trade_at": None,
            "last_scan_at": None,
        },
    )
    monkeypatch.setattr(
        system_service,
        "build_wrapper_usage_summary",
        lambda **_kwargs: {
            "total_wrappers": 3,
            "active_wrappers": 2,
            "total_import_events": 7,
            "planned_removal_buckets": {"2026-09-30": 3},
            "wrappers": [{"wrapper_module": "x", "usage_count": 7}],
        },
    )
    monkeypatch.setattr(system_service.settings, "app_env", "production")

    payload = system_service.get_ops_overview(
        include_compat_telemetry=True,
        include_wrapper_details=True,
    )

    telemetry = payload["compatibility_wrappers"]
    assert telemetry["details_requested"] is True
    assert telemetry["details_included"] is False
    assert telemetry["details_hidden_reason"] == "details_disabled_in_production"


def test_ops_overview_service_includes_wrapper_details_outside_production(monkeypatch):
    monkeypatch.setattr(
        system_service,
        "repo_get_ops_overview_read_model",
        lambda: {
            "total_signals": 1,
            "total_trades": 1,
            "open_trades": 0,
            "total_scans": 5,
            "total_pnl": 0.0,
            "last_signal_at": None,
            "last_trade_at": None,
            "last_scan_at": None,
        },
    )
    monkeypatch.setattr(
        system_service,
        "build_wrapper_usage_summary",
        lambda **_kwargs: {
            "total_wrappers": 3,
            "active_wrappers": 2,
            "total_import_events": 7,
            "planned_removal_buckets": {"2026-09-30": 3},
            "wrappers": [{"wrapper_module": "x", "usage_count": 7}],
        },
    )
    monkeypatch.setattr(system_service.settings, "app_env", "development")

    payload = system_service.get_ops_overview(
        include_compat_telemetry=True,
        include_wrapper_details=True,
    )

    telemetry = payload["compatibility_wrappers"]
    assert telemetry["details_requested"] is True
    assert telemetry["details_included"] is True
    assert "details_hidden_reason" not in telemetry
