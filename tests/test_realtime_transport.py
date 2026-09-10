import asyncio
import inspect
import json
from unittest.mock import AsyncMock

import pytest
from starlette.websockets import WebSocketDisconnect

from api import realtime
from api.runtime import realtime_bootstrap as bootstrap


class Socket:
    def __init__(self, *, block_send=False):
        self.messages = []
        self.block_send = block_send
        self.sent = asyncio.Event()
        self.closed = False
        self.code = None

    async def accept(self):
        return None

    async def send_text(self, data):
        if self.block_send:
            await asyncio.Event().wait()
        self.messages.append(json.loads(data))
        self.sent.set()

    async def close(self, code=1000):
        self.closed = True
        self.code = code

    async def receive_text(self):
        raise WebSocketDisconnect()


@pytest.mark.asyncio
async def test_slow_socket_is_evicted_without_delaying_other_clients():
    manager = realtime.ConnectionManager(send_timeout=0.02)
    slow, fast = Socket(block_send=True), Socket()
    await manager.connect(slow, "signals")
    await manager.connect(fast, "signals")
    broadcasting = asyncio.create_task(manager.broadcast({"type": "signal"}, "signals"))
    await asyncio.wait_for(fast.sent.wait(), 1)
    assert not broadcasting.done()
    await asyncio.wait_for(broadcasting, 1)
    assert slow.closed and slow.code == 1013
    assert manager._active_connections["signals"] == [fast]
    assert slow not in manager._send_locks


@pytest.mark.asyncio
async def test_sse_overflow_requests_rest_resync_and_generator_removes_queue(monkeypatch):
    manager = realtime.ConnectionManager(sse_queue_size=1)
    monkeypatch.setattr(realtime, "manager", manager)
    queue = manager.create_sse_queue("signals")
    await manager.broadcast({"type": "signal", "data": {"id": 1}}, "signals")
    await manager.broadcast({"type": "signal", "data": {"id": 2}}, "signals")
    assert queue.qsize() == 1
    generator = realtime.event_generator(queue, "signals")
    event = await anext(generator)
    assert "signal_feed_overflow" in event
    # Overflow is a resync hint, not a promise to replay either dropped event.
    await generator.aclose()
    assert manager._sse_queues["signals"] == []


@pytest.mark.asyncio
async def test_provider_callbacks_route_normalized_kline_and_trade_channels(monkeypatch):
    manager = realtime.ConnectionManager()
    monkeypatch.setattr(realtime, "manager", manager)
    kline, trade, other = Socket(), Socket(), Socket()
    await manager.connect(kline, "kline_BTCUSDT_1M")
    await manager.connect(trade, "trades_BTCUSDT")
    await manager.connect(other, "kline_BTCUSDT_1m")
    await bootstrap._on_kline({"symbol": "btcusdt", "interval": "1M", "close": 1})
    await bootstrap._on_trade({"symbol": "btcusdt", "price": 1})
    assert kline.messages[0]["type"] == "kline"
    assert trade.messages[0]["type"] == "trade"
    assert other.messages == []


@pytest.mark.asyncio
@pytest.mark.parametrize("stream", ["kline", "trades"])
async def test_stream_route_normalizes_and_releases_subscription_on_disconnect(monkeypatch, stream):
    import websocket_manager

    manager = realtime.ConnectionManager()
    monkeypatch.setattr(realtime, "manager", manager)
    subscribe = AsyncMock()
    unsubscribe = AsyncMock()
    method = "kline" if stream == "kline" else "agg_trade"
    monkeypatch.setattr(websocket_manager.ws_manager, f"subscribe_{method}", subscribe)
    monkeypatch.setattr(websocket_manager.ws_manager, f"unsubscribe_{method}", unsubscribe)
    socket = Socket()
    if stream == "kline":
        await realtime.websocket_kline(socket, " btcusdt ", "1M")
        subscribe.assert_awaited_once_with("BTCUSDT", "1M")
        unsubscribe.assert_awaited_once_with("BTCUSDT", "1M")
    else:
        await realtime.websocket_trades(socket, " btcusdt ")
        subscribe.assert_awaited_once_with("BTCUSDT")
        unsubscribe.assert_awaited_once_with("BTCUSDT")
    assert manager.total_connections == 0
    assert manager._send_locks == {}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload", ["[1,2]", "broken-json", '{"action":"subscribe","symbol":"BTC/USDT"}']
)
async def test_ticker_route_closes_bad_payload_and_cleans_membership(monkeypatch, payload):
    import bist_service
    import websocket_manager

    manager = realtime.ConnectionManager()
    monkeypatch.setattr(realtime, "manager", manager)
    monkeypatch.setattr(bist_service.bist_service, "get_all_stocks", lambda: [])
    monkeypatch.setattr(websocket_manager.ws_manager, "get_cached_tickers", lambda: {})
    socket = Socket()
    socket.receive_text = AsyncMock(return_value=payload)
    await realtime.websocket_ticker(socket)
    assert socket.closed and socket.code == 1008
    assert manager.total_connections == 0


@pytest.mark.asyncio
async def test_ticker_route_repeated_subscription_has_one_matching_release(monkeypatch):
    import bist_service
    import websocket_manager

    manager = realtime.ConnectionManager()
    monkeypatch.setattr(realtime, "manager", manager)
    monkeypatch.setattr(bist_service.bist_service, "get_all_stocks", lambda: [])
    monkeypatch.setattr(websocket_manager.ws_manager, "get_cached_tickers", lambda: {})
    subscribe, unsubscribe = AsyncMock(), AsyncMock()
    monkeypatch.setattr(websocket_manager.ws_manager, "subscribe_ticker", subscribe)
    monkeypatch.setattr(websocket_manager.ws_manager, "unsubscribe_ticker", unsubscribe)
    socket = Socket()
    message = '{"action":"subscribe","symbol":"btcusdt"}'
    socket.receive_text = AsyncMock(side_effect=[message, message, WebSocketDisconnect()])
    await realtime.websocket_ticker(socket)
    subscribe.assert_awaited_once_with("BTCUSDT")
    unsubscribe.assert_awaited_once_with("BTCUSDT")


def test_schedule_without_a_loop_closes_unawaited_coroutine(monkeypatch):
    monkeypatch.setattr(realtime, "_broadcast_loop", None)

    async def send():
        return None

    coroutine = send()
    assert not realtime._schedule_coro(coroutine)
    assert inspect.getcoroutinestate(coroutine) == inspect.CORO_CLOSED


@pytest.mark.asyncio
async def test_signal_disconnect_cleanup_and_reset_message_contract(monkeypatch):
    manager = realtime.ConnectionManager()
    monkeypatch.setattr(realtime, "manager", manager)
    socket = Socket()
    await manager.connect(socket, "signals")
    await realtime.broadcast_signal_resync()
    assert socket.messages[0]["type"] == "resync"
    assert socket.messages[0]["reason"] == "signal_feed_reset"
    manager.disconnect(socket, "signals")
    await realtime.websocket_signals(socket)
    assert manager.total_connections == 0
