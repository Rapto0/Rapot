"""Synthetic lifecycle checks: shutdown, singleton ownership and failed-cycle recovery."""

import asyncio

import pytest

from api.runtime import server_alarms as runtime
from infrastructure.runtime_lock import bot_instance_lock


@pytest.fixture
def worker(monkeypatch, tmp_path):
    from application.services import server_alarm_service as service

    monkeypatch.setattr(runtime.settings, "server_alarms_enabled", True)
    monkeypatch.setattr(runtime, "alarm_lock_path", lambda: tmp_path / "alarms.lock")
    monkeypatch.setattr(runtime, "_task", None)
    monkeypatch.setattr(runtime, "_stop", None)
    states = []
    monkeypatch.setattr(service, "set_runtime_running", states.append)
    return service, states


def test_start_is_idempotent_and_stop_waits_for_current_request(worker, monkeypatch):
    service, states = worker

    async def scenario():
        entered = asyncio.Event()
        release = asyncio.Event()
        calls = []

        async def cycle(*, should_stop):
            calls.append(1)
            entered.set()
            await release.wait()
            assert should_stop()

        monkeypatch.setattr(service, "run_alarm_cycle", cycle)
        await runtime.start_server_alarms()
        await entered.wait()
        original_task = runtime._task
        await runtime.start_server_alarms()
        assert runtime._task is original_task
        stopping = asyncio.create_task(runtime.stop_server_alarms())
        await asyncio.sleep(0)
        assert not stopping.done()
        assert states == [True]
        release.set()
        await stopping
        assert states == [True, False]
        assert calls == [1]
        assert runtime._task is None

    asyncio.run(scenario())


def test_another_owner_prevents_evaluation(worker, monkeypatch):
    service, states = worker

    async def forbidden(**kwargs):
        pytest.fail("Second lock owner must never evaluate or deliver alarms")

    monkeypatch.setattr(service, "run_alarm_cycle", forbidden)

    async def scenario():
        with bot_instance_lock(runtime.alarm_lock_path()):
            await runtime.start_server_alarms()
            assert states == [False]
            await runtime.stop_server_alarms()

    asyncio.run(scenario())


def test_failed_cycle_recovers_without_logging_provider_secret(worker, monkeypatch, caplog):
    service, states = worker
    calls = []

    async def cycle(*, should_stop):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("private-token-must-not-be-logged")
        runtime._stop.set()

    async def immediate_wait(stop):
        await asyncio.sleep(0)

    monkeypatch.setattr(service, "run_alarm_cycle", cycle)
    monkeypatch.setattr(runtime, "_wait", immediate_wait)

    async def scenario():
        await runtime.start_server_alarms()
        await runtime._task
        await runtime.stop_server_alarms()

    asyncio.run(scenario())
    assert calls == [1, 1]
    assert states == [True, False]
    assert "private-token-must-not-be-logged" not in caplog.text


def test_disabled_worker_does_not_open_lock(worker, monkeypatch):
    monkeypatch.setattr(runtime.settings, "server_alarms_enabled", False)
    monkeypatch.setattr(runtime, "alarm_lock_path", lambda: pytest.fail("Must not open lock"))
    asyncio.run(runtime.start_server_alarms())
    assert runtime._task is None
