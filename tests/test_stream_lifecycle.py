import asyncio
from unittest.mock import AsyncMock

import pytest

import bist_service
import websocket_manager
from websocket_manager import BinanceWebSocketManager


class UpstreamSocket:
    def __init__(self):
        self.closed = False
        self.messages = []

    async def send_json(self, message):
        self.messages.append(message)

    async def close(self):
        self.closed = True


@pytest.fixture
def stream_manager(monkeypatch):
    manager = BinanceWebSocketManager()
    manager._ws = UpstreamSocket()
    clock = [100.0]
    waits = []
    monkeypatch.setattr(websocket_manager, "monotonic", lambda: clock[0])

    async def sleep(delay):
        waits.append(delay)
        clock[0] += delay

    manager._control_sleep = sleep
    return manager, clock, waits


@pytest.mark.asyncio
async def test_dynamic_stream_references_pacing_and_last_client_unsubscribe(stream_manager):
    manager, _clock, waits = stream_manager
    await manager.subscribe_kline("btcusdt", "1M")
    await manager.subscribe_kline("BTCUSDT", "1M")
    await manager.subscribe_agg_trade("BTCUSDT")
    await manager.unsubscribe_kline("btcusdt", "1M")
    assert "btcusdt@kline_1M" in manager._subscriptions
    assert len(manager._ws.messages) == 2
    await manager.unsubscribe_kline("BTCUSDT", "1M")
    assert "btcusdt@kline_1M" not in manager._subscriptions
    await manager.unsubscribe_agg_trade("BTCUSDT")
    assert not manager._subscriptions
    assert [message["method"] for message in manager._ws.messages] == [
        "SUBSCRIBE",
        "SUBSCRIBE",
        "UNSUBSCRIBE",
        "UNSUBSCRIBE",
    ]
    assert [message["id"] for message in manager._ws.messages] == [1, 2, 3, 4]
    assert manager._ws.messages[0]["params"] == ["btcusdt@kline_1M"]
    assert waits == pytest.approx([0.35, 0.35, 0.35])


@pytest.mark.asyncio
async def test_stream_cap_does_not_block_existing_reference_or_modify_requested_set(stream_manager):
    manager, _clock, _waits = stream_manager
    manager._subscriptions = {f"symbol{i}@ticker" for i in range(1023)} | {"btcusdt@ticker"}
    manager._subscription_counts = dict.fromkeys(manager._subscriptions, 1)
    await manager.subscribe_ticker("BTCUSDT")
    assert manager._subscription_counts["btcusdt@ticker"] == 2
    with pytest.raises(ValueError, match="limit"):
        await manager.subscribe_ticker("ETHUSDT")
    assert "ethusdt@ticker" not in manager._subscriptions
    assert len(manager._subscriptions) == 1024
    assert manager._ws.messages == []


@pytest.mark.asyncio
@pytest.mark.parametrize("symbol", ["", "BTC/USDT", "BTCUSDT@ticker", "BTCUSDT?stream=", 123])
async def test_untrusted_stream_symbol_cannot_be_embedded_into_upstream_requests(
    stream_manager, symbol
):
    manager, _clock, _waits = stream_manager
    with pytest.raises(ValueError):
        await manager.subscribe_ticker(symbol)
    assert not manager._subscriptions
    assert manager._ws.messages == []


@pytest.mark.asyncio
async def test_interval_is_validated_and_month_case_preserved(stream_manager):
    manager, _clock, _waits = stream_manager
    with pytest.raises(ValueError):
        await manager.subscribe_kline("BTCUSDT", "1m/ethusdt@trade")
    await manager.subscribe_kline("BTCUSDT", "1M")
    await manager.subscribe_kline("BTCUSDT", "1m")
    assert manager._subscriptions == {"btcusdt@kline_1M", "btcusdt@kline_1m"}


@pytest.mark.asyncio
async def test_server_ack_and_rejection_are_not_treated_as_market_data(stream_manager, caplog):
    manager, _clock, _waits = stream_manager
    await manager.subscribe_ticker("BTCUSDT")
    assert 1 in manager._pending_controls
    await manager._handle_message({"id": 1, "result": None})
    assert not manager._pending_controls
    await manager.subscribe_agg_trade("BTCUSDT")
    await manager._handle_message({"id": 2, "code": 2, "msg": "invalid request"})
    assert manager._ws.closed
    assert not manager._pending_controls
    assert "rejected" in caplog.text
    assert "invalid request" in manager._last_subscription_error
    assert "btcusdt@aggTrade" in manager._subscriptions


@pytest.mark.asyncio
async def test_handshake_and_dynamic_subscription_share_one_consistent_snapshot(stream_manager):
    manager, _clock, _waits = stream_manager
    manager._ws = None
    await manager.subscribe_all_tickers()
    entered, release = asyncio.Event(), asyncio.Event()
    socket = UpstreamSocket()
    urls = []

    async def connect(url, **_kwargs):
        urls.append(url)
        entered.set()
        await release.wait()
        return socket

    manager._session = type("Session", (), {"ws_connect": staticmethod(connect)})()
    connecting = asyncio.create_task(manager._connect())
    await entered.wait()
    subscribing = asyncio.create_task(manager.subscribe_kline("BTCUSDT", "1m"))
    await asyncio.sleep(0)
    assert not subscribing.done()
    release.set()
    await connecting
    await subscribing
    assert "!miniTicker@arr" in urls[0]
    assert socket.messages[0]["params"] == ["btcusdt@kline_1m"]


@pytest.mark.asyncio
async def test_start_stop_cancel_vendor_tasks_close_sessions_and_restart_once(monkeypatch):
    sessions = []

    class Session:
        def __init__(self, *args, **kwargs):
            self.closed = False
            sessions.append(self)

        async def close(self):
            self.closed = True

    monkeypatch.setattr(websocket_manager.aiohttp, "ClientSession", Session)
    monkeypatch.setattr(bist_service, "get_isyatirim_ssl_context", lambda: None)
    manager = BinanceWebSocketManager()
    bist = bist_service.BISTDataService()

    async def hold():
        await asyncio.Event().wait()

    monkeypatch.setattr(manager, "_connection_loop", hold)
    monkeypatch.setattr(bist, "_refresh_loop", hold)
    for provider, task_name in ((manager, "_connection_task"), (bist, "_refresh_task")):
        await provider.start()
        first_task = getattr(provider, task_name)
        await provider.start()
        assert getattr(provider, task_name) is first_task
        await provider.stop()
        assert first_task.done()
        assert getattr(provider, task_name) is None
        await provider.start()
        assert getattr(provider, task_name) is not first_task
        await provider.stop()
    assert len(sessions) == 4
    assert all(session.closed for session in sessions)


@pytest.mark.asyncio
async def test_failed_control_write_closes_transport_without_acquiring_reference(stream_manager):
    manager, _clock, _waits = stream_manager
    manager._ws.send_json = AsyncMock(side_effect=RuntimeError("write failed"))
    with pytest.raises(RuntimeError, match="write failed"):
        await manager.subscribe_ticker("BTCUSDT")
    assert not manager._subscriptions
    assert not manager._subscription_counts
    assert not manager._pending_controls
    assert manager._ws.closed


@pytest.mark.asyncio
async def test_socket_close_failure_does_not_skip_session_cleanup(stream_manager):
    manager, _clock, _waits = stream_manager
    manager._ws.close = AsyncMock(side_effect=RuntimeError("close failed"))
    session = UpstreamSocket()
    manager._session = session
    with pytest.raises(RuntimeError, match="close failed"):
        await manager.stop()
    assert session.closed
    assert manager._session is None
    assert manager._ws is not None  # Preserve the failed resource for a cleanup retry.


@pytest.mark.asyncio
async def test_cancelled_unsubscribe_during_pacing_closes_stale_upstream(stream_manager):
    manager, _clock, _waits = stream_manager
    await manager.subscribe_ticker("BTCUSDT")
    entered = asyncio.Event()

    async def wait(_delay):
        entered.set()
        await asyncio.Event().wait()

    manager._control_sleep = wait
    task = asyncio.create_task(manager.unsubscribe_ticker("BTCUSDT"))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert manager._ws.closed
    assert not manager._subscriptions
