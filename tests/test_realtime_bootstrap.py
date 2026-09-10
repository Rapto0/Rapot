import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

import bist_service
import signal_dispatcher
import websocket_manager
from api import realtime
from api.runtime import realtime_bootstrap as bootstrap
from infrastructure.persistence import signal_feed_repository as repository


@pytest.fixture
def fake_vendors(monkeypatch):
    crypto = websocket_manager.BinanceWebSocketManager()
    bist = bist_service.BISTDataService()
    crypto.start = AsyncMock()
    crypto.stop = AsyncMock()
    bist.start = AsyncMock()
    bist.stop = AsyncMock()
    monkeypatch.setattr(websocket_manager, "ws_manager", crypto)
    monkeypatch.setattr(bist_service, "bist_service", bist)
    monkeypatch.setattr(bootstrap, "_signal_feed", None)
    monkeypatch.setattr(bootstrap, "_providers", None)
    monkeypatch.setattr(bootstrap, "_status_state", {})
    monkeypatch.setattr(realtime, "_broadcast_loop", None)
    monkeypatch.setattr(signal_dispatcher, "_publisher", None)
    return crypto, bist


@pytest.mark.asyncio
async def test_bootstrap_single_feed_no_duplicate_callbacks_and_complete_stop(fake_vendors):
    crypto, bist = fake_vendors
    state = {}
    logger = Mock()
    try:
        await bootstrap.start_realtime_services(runtime_state=state, logger=logger)
        first_feed = bootstrap._signal_feed
        await bootstrap.start_realtime_services(runtime_state=state, logger=logger)
        assert state["signal_feed_ready"] and state["realtime_ready"]
        assert first_feed is bootstrap._signal_feed
        assert signal_dispatcher._publisher is None
        status = await realtime.realtime_status()
        assert status["signal_feed"] == {
            "running": True,
            "ready": True,
            "cursor": 0,
            "error_type": None,
        }
        assert status["providers"]["started"] is True
        for event in ("ticker", "kline", "trade"):
            assert len(crypto._callbacks[event]) == 1
        assert len(bist._callbacks) == 1
        crypto.start.assert_awaited_once()
        bist.start.assert_awaited_once()
    finally:
        await bootstrap.stop_realtime_services(runtime_state=state, logger=logger)
    assert not first_feed.running
    assert not state["realtime_ready"]
    assert not state["signal_feed_ready"]
    assert realtime._broadcast_loop is None
    assert all(not callbacks for callbacks in crypto._callbacks.values())
    assert bist._callbacks == []
    assert bootstrap._signal_feed is None
    await bootstrap.start_realtime_services(runtime_state=state, logger=logger)
    await bootstrap.stop_realtime_services(runtime_state=state, logger=logger)
    assert crypto.start.await_count == 2


@pytest.mark.asyncio
async def test_status_exposes_only_error_type_not_sql_or_provider_details(monkeypatch):
    monkeypatch.setattr(bootstrap, "_signal_feed", None)
    monkeypatch.setattr(bootstrap, "_providers", None)
    monkeypatch.setattr(
        bootstrap,
        "_status_state",
        {
            "signal_feed_ready": False,
            "signal_feed_error": "OperationalError: SELECT secret FROM confidential",
            "market_realtime_error": "provider: credential details",
        },
    )
    status = await realtime.realtime_status()
    assert status["signal_feed"]["error_type"] == "OperationalError"
    assert "secret" not in str(status)
    assert "credential" not in str(status)


@pytest.mark.asyncio
async def test_vendor_start_failure_keeps_feed_live_but_health_degraded(fake_vendors):
    crypto, bist = fake_vendors
    crypto.start.side_effect = RuntimeError("vendor unavailable")
    state = {}
    try:
        await bootstrap.start_realtime_services(runtime_state=state, logger=Mock())
        assert bootstrap._signal_feed.running
        assert state["signal_feed_ready"]
        assert not state["market_realtime_ready"]
        assert not state["realtime_ready"]
        assert "vendor unavailable" in state["realtime_error"]
        bist.start.assert_awaited_once()
    finally:
        await bootstrap.stop_realtime_services(runtime_state=state, logger=Mock())


@pytest.mark.asyncio
async def test_initial_max_failure_aborts_before_provider_or_socket_start(
    monkeypatch, fake_vendors
):
    crypto, bist = fake_vendors

    def fail():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(repository, "get_signal_feed_max_id", fail)
    state = {}
    with pytest.raises(RuntimeError, match="database unavailable"):
        await bootstrap.start_realtime_services(runtime_state=state, logger=Mock())
    assert bootstrap._signal_feed is None
    assert not state["signal_feed_ready"]
    assert realtime._broadcast_loop is None
    crypto.start.assert_not_awaited()
    bist.start.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancelled_provider_start_cleans_the_already_started_feed(fake_vendors):
    crypto, _bist = fake_vendors
    entered = asyncio.Event()

    async def start():
        entered.set()
        await asyncio.Event().wait()

    crypto.start.side_effect = start
    state = {}
    task = asyncio.create_task(
        bootstrap.start_realtime_services(runtime_state=state, logger=Mock())
    )
    await asyncio.wait_for(entered.wait(), 2)
    feed = bootstrap._signal_feed
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not feed.running
    assert bootstrap._signal_feed is None
    assert all(not callbacks for callbacks in crypto._callbacks.values())
    assert realtime._broadcast_loop is None
