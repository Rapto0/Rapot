"""API-owned alarms/AI remain available without the retired scheduled bot."""

import builtins
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import api.main as api_main
import db_session
from application.services import borsapy_gateway, borsapy_market_data, server_alarm_service
from infrastructure.persistence import ops_repository
from scripts import runtime
from settings import Settings
from tests.test_advanced_alarm_backend import payload

RETIRED = {
    "scheduler",
    "market_scanner",
    "async_scanner",
    "health_api",
    "command_handler",
    "telegram_notify",
}


def refuse_retired_imports(monkeypatch):
    original = builtins.__import__
    calls = []

    def guarded(name, *args, **kwargs):
        if name.split(".", 1)[0] in RETIRED:
            calls.append(name)
            raise AssertionError("retired runtime import")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    return calls


def test_container_entrypoint_rejects_bot_before_starting_anything(monkeypatch):
    run = Mock(side_effect=AssertionError("server must not start"))
    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(run=run))
    monkeypatch.setattr(sys, "argv", ["runtime", "bot"])
    with pytest.raises(SystemExit) as exit_info:
        runtime.main()
    assert exit_info.value.code == 2
    run.assert_not_called()


def test_default_container_runs_single_api_even_with_stale_embedded_environment(monkeypatch):
    dockerfile = Path(__file__).resolve().parents[1] / "Dockerfile"
    command = next(line for line in dockerfile.read_text().splitlines() if line.startswith("CMD "))
    argv = json.loads(command.removeprefix("CMD "))
    assert argv == ["python", "-m", "scripts.runtime", "api"]
    monkeypatch.setenv("RUN_EMBEDDED_BOT", "true")
    monkeypatch.setattr(sys, "argv", ["runtime", argv[-1]])
    run = Mock()
    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(run=run))
    calls = refuse_retired_imports(monkeypatch)
    runtime.main()
    run.assert_called_once_with("api.main:app", host="0.0.0.0", port=8000, workers=1)
    assert calls == []


def test_startup_initializes_database_without_restoring_removed_scanners(monkeypatch):
    init = Mock()
    reconcile = Mock(return_value={})
    monkeypatch.setattr(db_session, "init_db", init)
    monkeypatch.setattr(ops_repository, "reconcile_active_orders_on_startup", reconcile)
    monkeypatch.setattr(api_main, "_RUNTIME_STATE", {})
    calls = refuse_retired_imports(monkeypatch)
    api_main._run_startup_sequence()
    init.assert_called_once_with()
    reconcile.assert_called_once_with()
    assert api_main._RUNTIME_STATE["db_ready"] is True
    assert calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("fail_advanced_start", [False, True])
async def test_lifespan_owns_website_alarm_startup_and_shutdown(monkeypatch, fail_advanced_start):
    seen = []
    monkeypatch.setattr(api_main, "_run_startup_sequence", lambda: seen.append("database"))
    for name in (
        "_start_realtime_services",
        "_stop_realtime_services",
        "start_server_alarms",
        "stop_server_alarms",
        "start_advanced_alarms",
        "stop_advanced_alarms",
    ):

        async def operation(name=name):
            seen.append(name)
            if fail_advanced_start and name == "start_advanced_alarms":
                raise RuntimeError("synthetic startup failure")

        monkeypatch.setattr(api_main, name, operation)
    monkeypatch.setattr(
        borsapy_gateway,
        "get_borsapy_gateway",
        lambda: SimpleNamespace(close=lambda: seen.append("gateway_close")),
    )
    monkeypatch.setattr(
        borsapy_market_data,
        "get_borsapy_market_data",
        lambda: SimpleNamespace(close=lambda: seen.append("market_close")),
    )
    calls = refuse_retired_imports(monkeypatch)
    if fail_advanced_start:
        with pytest.raises(RuntimeError, match="synthetic startup"):
            async with api_main.lifespan(api_main.app):
                pytest.fail("Failed startup must not yield")
    else:
        async with api_main.lifespan(api_main.app):
            seen.append("serving")
    expected = [
        "database",
        "_start_realtime_services",
        "start_server_alarms",
        "start_advanced_alarms",
    ]
    if not fail_advanced_start:
        expected.append("serving")
    expected += ["stop_advanced_alarms", "stop_server_alarms", "_stop_realtime_services"]
    if not fail_advanced_start:
        expected += ["market_close", "gateway_close"]
    assert seen == expected
    assert calls == []


def test_telegram_is_optional_and_only_explicit_alarm_delivery_requires_it(
    monkeypatch, authenticated_api_client
):
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    configured = Settings(_env_file=None)
    assert configured.telegram_token == configured.telegram_chat_id == ""
    monkeypatch.setattr(server_alarm_service.settings, "telegram_token", "")
    monkeypatch.setattr(server_alarm_service.settings, "telegram_chat_id", "")
    body = payload()
    body.pop("notify_telegram")
    accepted = authenticated_api_client.post("/advanced-alarms", json=body)
    assert accepted.status_code == 201
    assert accepted.json()["enabled"] is True and accepted.json()["notify_telegram"] is False
    requested = authenticated_api_client.post(
        "/advanced-alarms", json={**body, "notify_telegram": True}
    )
    assert requested.status_code == 422


def test_retired_analysis_returns_410_without_import_or_delivery(
    monkeypatch, authenticated_api_client
):
    calls = refuse_retired_imports(monkeypatch)
    result = authenticated_api_client.post("/analyze/THYAO?market_type=BIST")
    assert result.status_code == 410
    assert result.headers["cache-control"] == "private, no-store"
    assert calls == []
