"""Regressions for provider work ownership and alarm-first demand capacity."""

import asyncio
import threading

import pytest

from application.services import advanced_alarm_market_data as market
from tests import test_advanced_alarm_market_data as fixtures
from tests.test_advanced_alarm_market_data import rule


@pytest.fixture
def hub(tmp_path):
    return fixtures.hub.__wrapped__(tmp_path)


def test_replaced_work_between_take_and_fetch_cannot_steal_new_worker_ownership(hub):
    hub.configure([rule("rsi")])
    old_job = hub._take_work()
    hub.configure([])
    hub.configure([rule("rsi")])
    replacement_job = hub._take_work()
    replacement = hub._requests[old_job[0]]
    assert replacement.busy
    hub.fetch_history(*old_job)
    assert not hub._provider.calls
    assert not hub._series and not hub._cache.data
    assert replacement.busy
    hub.fetch_history(*replacement_job)
    assert len(hub._provider.calls) == 1
    assert not replacement.busy
    assert old_job[0] in hub._series


def test_chart_cannot_displace_alarm_at_full_native_history_capacity(hub, monkeypatch):
    monkeypatch.setattr(market, "MAX_REQUESTS", 2)
    selected = {
        **rule("rsi"),
        "symbols": [
            {"symbol": "THYAO", "market_type": "BIST"},
            {"symbol": "ZOREN", "market_type": "BIST"},
        ],
    }
    hub.configure([selected])
    expected = set(hub._requests)
    assert len(expected) == 2
    hub.history("AKBNK")  # Sorts ahead of both active symbols.
    assert set(hub._requests) == expected
    assert hub.status()["history_requested"] == 3
    assert hub.status()["history_scheduled"] == 2
    # Spare capacity becomes available when the condition is removed.
    hub.configure([])
    assert set(hub._requests) == {("BIST", "AKBNK", "1m")}


@pytest.mark.parametrize("cancel", [False, True])
def test_provider_sessions_close_only_after_fixed_workers_have_exited(hub, cancel):
    closed = []

    def close_provider():
        assert not any(thread.is_alive() for thread in hub._threads)
        closed.append(True)

    hub._provider.close = close_provider

    async def exercise():
        hub.configure([rule("close")])
        hub._provider.block = threading.Event()
        await hub.start()
        assert await asyncio.to_thread(hub._provider.entered.wait, 2)
        stopping = asyncio.create_task(hub.stop())
        try:
            await asyncio.sleep(0.02)
            if cancel:
                stopping.cancel()
                await asyncio.sleep(0.02)
            assert not stopping.done() and not closed
        finally:
            hub._provider.block.set()
        if cancel:
            with pytest.raises(asyncio.CancelledError):
                await stopping
        else:
            await asyncio.wait_for(stopping, 3)
        assert closed == [True]
        assert not hub._threads

    asyncio.run(exercise())
