import threading

import pytest

import health_api
import scheduler
from infrastructure.persistence import ops_repository
from state_keys import (
    ASYNC_SCAN_COUNT_KEY,
    ASYNC_SIGNAL_COUNT_KEY,
    RUNTIME_IS_RUNNING_KEY,
    SCHEDULED_SCAN_LOCK_NAME,
    SYNC_SCAN_COUNT_KEY,
    SYNC_SIGNAL_COUNT_KEY,
)


@pytest.fixture(autouse=True)
def reset_runtime_observation(monkeypatch):
    monkeypatch.setattr(health_api, "_runtime_lifecycle", {"phase": "unknown", "owner": None})
    monkeypatch.setattr(health_api, "_bot_status", {"is_running": True, "is_scanning": True})


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ("", None),
        ("invalid", None),
        ("2", None),
        (" TRUE ", True),
        ("on", True),
        ("1", True),
        ("false", False),
        ("0", False),
        ("OFF", False),
    ],
)
def test_missing_or_malformed_flags_are_not_coerced_to_running_or_stopped(raw, expected):
    assert health_api._parse_stat_bool(raw) is expected


@pytest.mark.parametrize("reported", [None, "false", "true", "malformed"])
def test_standalone_observer_cannot_turn_a_persisted_flag_into_current_liveness(reported):
    if reported is not None:
        ops_repository.set_bot_stat(RUNTIME_IS_RUNNING_KEY, reported)
    with health_api.app.test_client() as client:
        response = client.get("/status")
        health_response = client.get("/health")
    bot = response.get_json()["bot"]
    assert response.status_code == 200
    assert bot["is_running"] is None
    assert bot["state"] == "unknown"
    assert bot["state_source"] == "unverified_repository"
    assert bot["observed_at"] is None
    assert bot["last_reported_is_running"] is health_api._parse_stat_bool(reported)
    assert bot["is_scanning"] is None
    # Infrastructure health is separate from proving a scheduler is currently running.
    assert health_response.status_code == 200
    assert health_response.get_json()["status"] == "healthy"
    assert health_response.get_json()["realtime"] == "unknown"


def test_current_lifecycle_distinguishes_starting_running_and_explicit_stop():
    health_api.begin_bot_runtime()
    assert health_api._load_runtime_state_from_repo()["is_running"] is None
    health_api.mark_bot_runtime_running()
    with health_api.app.test_client() as client:
        running = client.get("/status").get_json()["bot"]
        assert running["is_running"] is True
        assert running["state"] == "running"
        assert running["state_source"] == "local_lifecycle"
        assert running["observed_at"].endswith("+00:00")
        health_api.end_bot_runtime()
        stopped = client.get("/status").get_json()["bot"]
    assert stopped["is_running"] is False
    assert stopped["state"] == "stopped"


def test_dead_owner_thread_cannot_keep_a_running_flag_true(monkeypatch):
    owner = threading.Thread(target=lambda: None)
    owner.start()
    owner.join(timeout=1)
    monkeypatch.setattr(health_api, "_runtime_lifecycle", {"phase": "running", "owner": owner})
    assert health_api._load_runtime_state_from_repo()["is_running"] is None


def test_unrelated_thread_cannot_change_the_scheduler_lifecycle():
    health_api.begin_bot_runtime()
    worker = threading.Thread(target=health_api.mark_bot_runtime_running)
    worker.start()
    worker.join(timeout=1)
    assert health_api._observe_bot_runtime()["is_running"] is None


def test_repository_failure_does_not_fall_back_to_true_in_memory(monkeypatch):
    health_api.begin_bot_runtime()
    health_api.mark_bot_runtime_running()

    def fail(_name):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(ops_repository, "get_bot_stat", fail)
    with health_api.app.test_client() as client:
        bot = client.get("/status").get_json()["bot"]
    assert bot["is_running"] is None
    assert bot["state"] == "unknown"
    assert bot["state_source"] == "unavailable"
    assert bot["observed_at"] is None


def test_db_probe_failure_hides_old_running_state_but_preserves_503_health(monkeypatch):
    health_api.begin_bot_runtime()
    health_api.mark_bot_runtime_running()
    monkeypatch.setattr(health_api, "_probe_database", lambda: False)
    with health_api.app.test_client() as client:
        bot = client.get("/status").get_json()["bot"]
        health_response = client.get("/health")
    assert bot["is_running"] is None
    assert bot["is_scanning"] is None
    assert bot["state"] == "unknown"
    assert bot["database"] == "disconnected"
    assert health_response.status_code == 503
    assert health_response.get_json()["status"] == "unhealthy"


def test_old_scan_lease_is_not_current_scan_evidence():
    assert health_api._load_runtime_state_from_repo()["is_scanning"] is None
    assert ops_repository.acquire_distributed_lock(SCHEDULED_SCAN_LOCK_NAME, owner="test")
    assert health_api._load_runtime_state_from_repo()["is_scanning"] is None
    health_api.begin_bot_runtime()
    health_api.mark_bot_runtime_running()
    assert health_api._load_runtime_state_from_repo()["is_scanning"] is False


def test_actual_nested_scan_calls_are_observed_and_cleaned_up_after_failure():
    health_api.begin_bot_runtime()
    health_api.mark_bot_runtime_running()
    with pytest.raises(RuntimeError, match="scan failed"), health_api.track_bot_scan():
        assert health_api._load_runtime_state_from_repo()["is_scanning"] is True
        with health_api.track_bot_scan():
            assert health_api._observe_bot_runtime()["is_scanning"] is True
        assert health_api._observe_bot_runtime()["is_scanning"] is True
        raise RuntimeError("scan failed")
    assert health_api._observe_bot_runtime()["is_scanning"] is False


@pytest.mark.parametrize("fail_scan", [False, True])
def test_manual_async_command_tracks_the_actual_scan_without_network(monkeypatch, fail_scan):
    import async_scanner
    import command_handler

    health_api.begin_bot_runtime()
    health_api.mark_bot_runtime_running()
    seen = []

    def scan():
        seen.append(health_api._observe_bot_runtime()["is_scanning"])
        if fail_scan:
            raise RuntimeError("scan failed")

    monkeypatch.setattr(command_handler, "get_last_messages", lambda: ["/asynctara"])
    monkeypatch.setattr(command_handler, "send_message", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(async_scanner, "run_async_scan", scan)
    if fail_scan:
        with pytest.raises(RuntimeError, match="scan failed"):
            command_handler.check_commands()
    else:
        command_handler.check_commands()
    assert seen == [True]
    assert health_api._observe_bot_runtime()["is_scanning"] is False


@pytest.mark.parametrize("raw", [None, "invalid", "-1"])
def test_missing_or_invalid_counters_are_not_reported_as_zero(raw):
    if raw is not None:
        ops_repository.set_bot_stat(SYNC_SCAN_COUNT_KEY, raw)
    with health_api.app.test_client() as client:
        payload = client.get("/status").get_json()
    assert payload["scanning"]["data_available"] is False
    assert payload["scanning"]["scan_count"] is None
    assert payload["scanning"]["signal_count"] is None
    assert payload["errors"]["error_count"] is None


def test_counter_query_failure_after_successful_probe_is_unavailable(monkeypatch):
    monkeypatch.setattr(health_api, "_probe_database", lambda: True)

    def fail(_name):
        raise RuntimeError("counter read failed")

    monkeypatch.setattr(ops_repository, "get_bot_stat", fail)
    with health_api.app.test_client() as client:
        payload = client.get("/status").get_json()
    assert payload["bot"]["database"] == "connected"
    assert payload["scanning"]["data_available"] is False
    assert payload["scanning"]["scan_count"] is None


def test_counter_update_is_not_last_scan_time_and_explicit_zero_remains_zero():
    for key in (
        SYNC_SCAN_COUNT_KEY,
        SYNC_SIGNAL_COUNT_KEY,
        ASYNC_SCAN_COUNT_KEY,
        ASYNC_SIGNAL_COUNT_KEY,
    ):
        ops_repository.set_bot_stat(key, "0")
    with health_api.app.test_client() as client:
        scanning = client.get("/status").get_json()["scanning"]
    assert scanning["data_available"] is True
    assert scanning["scan_count"] == 0
    assert scanning["counters_updated_at"] is not None
    assert scanning["last_scan_available"] is True
    assert scanning["last_scan_time"] is None


def test_last_scan_time_comes_from_recorded_scan_history():
    ops_repository.save_scan_history(
        scan_type="BIST",
        mode="sync",
        symbols_scanned=0,
        signals_found=0,
        errors_count=1,
        duration_seconds=1,
        status="failed",
    )
    with health_api.app.test_client() as client:
        scanning = client.get("/status").get_json()["scanning"]
    assert scanning["last_scan_time"].endswith("+00:00")
    assert scanning["last_scan_available"] is True
    # A completed scan record does not invent missing lifetime counters.
    assert scanning["data_available"] is False
    assert scanning["scan_count"] is None


@pytest.mark.parametrize("use_async", [False, True])
@pytest.mark.parametrize("fail_boot", [False, True])
def test_all_bot_modes_record_startup_and_terminal_lifecycle(monkeypatch, use_async, fail_boot):
    seen = []

    def boot(*, use_async):
        seen.append(use_async)
        assert health_api._observe_bot_runtime()["is_running"] is None
        if fail_boot:
            raise RuntimeError("boot failed")
        scheduler.run_bot_loop(lambda: None, lambda: None)

    def stop():
        assert health_api._observe_bot_runtime()["is_running"] is True
        raise KeyboardInterrupt

    monkeypatch.setattr(scheduler, "_run_bot", boot)
    monkeypatch.setattr(scheduler.schedule, "run_pending", stop)
    monkeypatch.setattr(scheduler, "send_message", lambda *_args, **_kwargs: None)
    if fail_boot:
        with pytest.raises(RuntimeError, match="boot failed"):
            scheduler.start_bot(use_async=use_async)
    else:
        scheduler.start_bot(use_async=use_async)
    assert seen == [use_async]
    assert health_api._observe_bot_runtime()["is_running"] is False
