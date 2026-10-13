import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

import bist_service
import db_session
import websocket_manager
from api import realtime
from api.runtime import realtime_bootstrap as bootstrap


@pytest.fixture
def fake_vendors(monkeypatch):
    # The legacy-provider lifecycle remains available only by explicit selection.
    monkeypatch.setattr(bootstrap.settings, "borsapy_use_for_bist", False)
    crypto = websocket_manager.BinanceWebSocketManager()
    bist = bist_service.BISTDataService()
    crypto.start = AsyncMock()
    crypto.stop = AsyncMock()
    bist.start = AsyncMock()
    bist.stop = AsyncMock()
    monkeypatch.setattr(websocket_manager, "ws_manager", crypto)
    monkeypatch.setattr(bist_service, "bist_service", bist)
    monkeypatch.setattr(bootstrap, "_providers", None)
    monkeypatch.setattr(bootstrap, "_status_state", {})
    return crypto, bist


@pytest.mark.asyncio
async def test_borsapy_bootstrap_never_starts_legacy_bist_or_requires_account(
    fake_vendors, monkeypatch
):
    crypto, bist = fake_vendors
    monkeypatch.setattr(bootstrap.settings, "borsapy_use_for_bist", True)
    state = {}
    try:
        await bootstrap.start_realtime_services(runtime_state=state, logger=Mock())
        assert state["realtime_ready"]
        crypto.start.assert_awaited_once()
        bist.start.assert_not_awaited()
        assert bist._callbacks == []
        status = bootstrap.get_realtime_status()["providers"]
        assert status["bist_source"] == "borsapy_tradingview"
        assert status["bist_account_stream"] == "on_demand"
    finally:
        await bootstrap.stop_realtime_services(runtime_state=state, logger=Mock())
    bist.stop.assert_not_awaited()


@pytest.mark.asyncio
async def test_bootstrap_market_callbacks_are_idempotent_and_restartable(fake_vendors):
    crypto, bist = fake_vendors
    state = {}
    logger = Mock()
    try:
        await bootstrap.start_realtime_services(runtime_state=state, logger=logger)
        await bootstrap.start_realtime_services(runtime_state=state, logger=logger)
        assert state["realtime_ready"]
        status = await realtime.realtime_status()
        assert "signal_feed" not in status
        assert status["providers"]["started"] is True
        for event in ("ticker", "kline", "trade"):
            assert len(crypto._callbacks[event]) == 1
        assert len(bist._callbacks) == 1
        crypto.start.assert_awaited_once()
        bist.start.assert_awaited_once()
    finally:
        await bootstrap.stop_realtime_services(runtime_state=state, logger=logger)
    assert not state["realtime_ready"]
    assert all(not callbacks for callbacks in crypto._callbacks.values())
    assert bist._callbacks == []
    await bootstrap.start_realtime_services(runtime_state=state, logger=logger)
    await bootstrap.stop_realtime_services(runtime_state=state, logger=logger)
    assert crypto.start.await_count == 2


@pytest.mark.asyncio
async def test_status_exposes_only_error_type_not_sql_or_provider_details(monkeypatch):
    monkeypatch.setattr(bootstrap, "_providers", None)
    monkeypatch.setattr(
        bootstrap,
        "_status_state",
        {
            "market_realtime_error": "provider: credential details",
        },
    )
    status = await realtime.realtime_status()
    assert status["providers"]["startup_failed"] is True
    assert "secret" not in str(status)
    assert "credential" not in str(status)


@pytest.mark.asyncio
async def test_vendor_start_failure_keeps_other_provider_live_and_health_degraded(fake_vendors):
    crypto, bist = fake_vendors
    crypto.start.side_effect = RuntimeError("vendor unavailable")
    state = {}
    try:
        await bootstrap.start_realtime_services(runtime_state=state, logger=Mock())
        assert not state["market_realtime_ready"]
        assert not state["realtime_ready"]
        assert "vendor unavailable" in state["realtime_error"]
        bist.start.assert_awaited_once()
    finally:
        await bootstrap.stop_realtime_services(runtime_state=state, logger=Mock())


@pytest.mark.asyncio
async def test_market_bootstrap_never_reads_or_polls_signal_archive(monkeypatch, fake_vendors):
    def fail(*args, **kwargs):
        raise AssertionError("Market streams must not read archived signals")

    monkeypatch.setattr(db_session, "get_session", fail)
    monkeypatch.setattr(db_session, "get_engine", fail)
    tasks_before = asyncio.all_tasks()
    state = {}
    try:
        await bootstrap.start_realtime_services(runtime_state=state, logger=Mock())
        await asyncio.sleep(0)
        assert state["realtime_ready"]
        assert asyncio.all_tasks() == tasks_before
    finally:
        await bootstrap.stop_realtime_services(runtime_state=state, logger=Mock())


@pytest.mark.asyncio
async def test_cancelled_provider_start_cleans_callbacks_and_owned_providers(fake_vendors):
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
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert all(not callbacks for callbacks in crypto._callbacks.values())
