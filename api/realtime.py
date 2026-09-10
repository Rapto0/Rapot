"""
Real-time Data API - WebSocket & SSE Endpoints
Provides real-time market data streams to frontend clients.
"""

import asyncio
import json
from collections import defaultdict
from collections.abc import Coroutine
from contextlib import suppress
from datetime import datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/realtime", tags=["Real-time Data"])


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self, *, send_timeout: float = 2.0, sse_queue_size: int = 100):
        self._active_connections: dict[str, list[WebSocket]] = defaultdict(list)
        self._sse_queues: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._send_locks: dict[WebSocket, asyncio.Lock] = {}
        self._send_timeout = send_timeout
        self._sse_queue_size = sse_queue_size

    async def connect(self, websocket: WebSocket, channel: str = "default"):
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        self._active_connections[channel].append(websocket)
        self._send_locks.setdefault(websocket, asyncio.Lock())
        logger.info(f"Client connected to channel: {channel}")

    def disconnect(self, websocket: WebSocket, channel: str = "default"):
        """Remove a WebSocket connection."""
        if websocket in self._active_connections[channel]:
            self._active_connections[channel].remove(websocket)
            logger.info(f"Client disconnected from channel: {channel}")
        self._send_locks.pop(websocket, None)

    async def _send_text(self, websocket: WebSocket, data: str) -> None:
        lock = self._send_locks.setdefault(websocket, asyncio.Lock())
        async with lock:
            await websocket.send_text(data)

    async def send_json(self, websocket: WebSocket, message: dict) -> None:
        await asyncio.wait_for(
            self._send_text(websocket, json.dumps(message)), timeout=self._send_timeout
        )

    async def broadcast(self, message: dict, channel: str = "default"):
        """Broadcast message to all connections in a channel."""
        data = json.dumps(message)

        async def send_one(connection: WebSocket) -> None:
            try:
                await asyncio.wait_for(
                    self._send_text(connection, data), timeout=self._send_timeout
                )
            except Exception as exc:
                logger.warning(
                    "Realtime send failed on channel %s (%s): %s",
                    channel,
                    type(exc).__name__,
                    exc,
                )
                self.disconnect(connection, channel)
                with suppress(Exception):
                    await asyncio.wait_for(connection.close(code=1013), self._send_timeout)

        # Snapshot membership before awaiting; a slow socket cannot delay the
        # first send to healthy clients or mutate the list being iterated.
        await asyncio.gather(
            *(send_one(connection) for connection in tuple(self._active_connections[channel]))
        )

        # SSE broadcast
        for queue in tuple(self._sse_queues[channel]):
            if queue.full():
                if channel == "signals":
                    while not queue.empty():
                        queue.get_nowait()
                    queue.put_nowait(
                        {
                            "type": "resync",
                            "reason": "signal_feed_overflow",
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                    continue
                queue.get_nowait()
            queue.put_nowait(message)

    def create_sse_queue(self, channel: str = "default") -> asyncio.Queue:
        """Create a queue for SSE client."""
        queue = asyncio.Queue(maxsize=self._sse_queue_size)
        self._sse_queues[channel].append(queue)
        return queue

    def remove_sse_queue(self, queue: asyncio.Queue, channel: str = "default"):
        """Remove an SSE queue."""
        if queue in self._sse_queues[channel]:
            self._sse_queues[channel].remove(queue)

    @property
    def total_connections(self) -> int:
        """Total number of active connections."""
        return sum(len(conns) for conns in self._active_connections.values())


# Global connection manager
manager = ConnectionManager()
_broadcast_loop: asyncio.AbstractEventLoop | None = None


def register_broadcast_loop(loop: asyncio.AbstractEventLoop | None = None) -> None:
    """
    Registers the event loop used by API realtime services.
    Allows non-async threads (scanner/bot) to publish realtime events safely.
    """
    global _broadcast_loop
    if loop is None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
    _broadcast_loop = loop


def clear_broadcast_loop() -> None:
    global _broadcast_loop
    _broadcast_loop = None


def _schedule_coro(coro: Coroutine[Any, Any, Any]) -> bool:
    """Schedules a coroutine on the current or registered broadcast loop."""

    def completed(future: Any) -> None:
        if not future.cancelled() and future.exception() is not None:
            logger.warning("Scheduled realtime broadcast failed: %s", future.exception())

    try:
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None
        target_loop = _broadcast_loop or running_loop
        if target_loop is None or not target_loop.is_running():
            coro.close()
            return False
        if target_loop is running_loop:
            future = target_loop.create_task(coro)
        else:
            future = asyncio.run_coroutine_threadsafe(coro, target_loop)
        future.add_done_callback(completed)
        return True
    except Exception:
        coro.close()
        logger.exception("Unable to schedule realtime broadcast.")
        return False


# ==================== WebSocket Endpoints ====================


@router.websocket("/ws/ticker")
async def websocket_ticker(websocket: WebSocket):
    """
    WebSocket endpoint for real-time ticker data.
    Receives both BIST and Crypto ticker updates.
    """
    await manager.connect(websocket, "ticker")
    subscriptions: set[str] = set()
    try:
        # Send initial data
        from bist_service import bist_service
        from websocket_manager import ws_manager

        initial_data = {
            "type": "init",
            "crypto": ws_manager.get_cached_tickers(),
            "bist": bist_service.get_all_stocks(),
            "timestamp": datetime.now().isoformat(),
        }
        await manager.send_json(websocket, initial_data)

        # Keep connection alive and handle client messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                message = json.loads(data)
                if not isinstance(message, dict):
                    await websocket.close(code=1008)
                    break

                # Handle subscription requests
                if message.get("action") == "subscribe":
                    symbol = message.get("symbol")
                    if symbol:
                        from websocket_manager import normalize_stream_symbol

                        symbol = normalize_stream_symbol(symbol)
                        if message.get("type", "ticker") != "ticker":
                            await manager.send_json(
                                websocket,
                                {"type": "error", "error": "Use the dedicated stream endpoint"},
                            )
                            continue
                        if symbol not in subscriptions:
                            await ws_manager.subscribe_ticker(symbol)
                            subscriptions.add(symbol)
                        await manager.send_json(websocket, {"type": "subscribed", "symbol": symbol})

            except TimeoutError:
                # Send heartbeat
                await manager.send_json(
                    websocket, {"type": "heartbeat", "timestamp": datetime.now().isoformat()}
                )

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error on /realtime/ws/ticker.")
        with suppress(Exception):
            await websocket.close(code=1008)
    finally:
        manager.disconnect(websocket, "ticker")
        for symbol in subscriptions:
            with suppress(Exception):
                await ws_manager.unsubscribe_ticker(symbol)


@router.websocket("/ws/kline/{symbol}")
async def websocket_kline(websocket: WebSocket, symbol: str, interval: str = "1m"):
    """
    WebSocket endpoint for real-time kline/candlestick data.
    """
    from websocket_manager import normalize_kline_interval, normalize_stream_symbol, ws_manager

    try:
        symbol = normalize_stream_symbol(symbol)
        interval = normalize_kline_interval(interval)
    except ValueError:
        await websocket.close(code=1008)
        return
    channel = f"kline_{symbol}_{interval}"
    await manager.connect(websocket, channel)
    subscribed = False

    try:
        # Subscribe to kline stream
        await ws_manager.subscribe_kline(symbol, interval)
        subscribed = True

        # Keep connection alive
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except TimeoutError:
                await manager.send_json(websocket, {"type": "heartbeat"})

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Kline WebSocket error on /realtime/ws/kline/%s.", symbol)
    finally:
        manager.disconnect(websocket, channel)
        if subscribed:
            with suppress(Exception):
                await ws_manager.unsubscribe_kline(symbol, interval)


@router.websocket("/ws/trades/{symbol}")
async def websocket_trades(websocket: WebSocket, symbol: str):
    """
    WebSocket endpoint for real-time trade stream.
    """
    from websocket_manager import normalize_stream_symbol, ws_manager

    try:
        symbol = normalize_stream_symbol(symbol)
    except ValueError:
        await websocket.close(code=1008)
        return
    channel = f"trades_{symbol}"
    await manager.connect(websocket, channel)
    subscribed = False

    try:
        # Subscribe to trade stream
        await ws_manager.subscribe_agg_trade(symbol)
        subscribed = True

        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except TimeoutError:
                await manager.send_json(websocket, {"type": "heartbeat"})

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Trades WebSocket error on /realtime/ws/trades/%s.", symbol)
    finally:
        manager.disconnect(websocket, channel)
        if subscribed:
            with suppress(Exception):
                await ws_manager.unsubscribe_agg_trade(symbol)


@router.websocket("/ws/signals")
async def websocket_signals(websocket: WebSocket):
    """
    WebSocket endpoint for real-time trading signals.
    """
    await manager.connect(websocket, "signals")

    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except TimeoutError:
                await manager.send_json(websocket, {"type": "heartbeat"})

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Signals WebSocket error on /realtime/ws/signals.")
    finally:
        manager.disconnect(websocket, "signals")


# ==================== SSE Endpoints ====================


async def event_generator(queue: asyncio.Queue, channel: str):
    """Generate SSE events from queue."""
    try:
        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=30)
                yield f"data: {json.dumps(data)}\n\n"
            except TimeoutError:
                # Send heartbeat
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        manager.remove_sse_queue(queue, channel)


@router.get("/sse/ticker")
async def sse_ticker():
    """
    Server-Sent Events endpoint for ticker data.
    Alternative to WebSocket for simpler clients.
    """
    queue = manager.create_sse_queue("ticker")

    return StreamingResponse(
        event_generator(queue, "ticker"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sse/signals")
async def sse_signals():
    """
    SSE endpoint for trading signals.
    """
    queue = manager.create_sse_queue("signals")

    return StreamingResponse(
        event_generator(queue, "signals"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# ==================== Data Broadcasting Functions ====================


async def broadcast_ticker(data: dict):
    """Broadcast ticker update to all connected clients."""
    await manager.broadcast(
        {
            "type": "ticker",
            "data": data,
            "timestamp": datetime.now().isoformat(),
        },
        "ticker",
    )


async def broadcast_kline(symbol: str, interval: str, data: dict):
    """Broadcast kline update to subscribers."""
    symbol = symbol.strip().upper()
    channel = f"kline_{symbol}_{interval}"
    await manager.broadcast(
        {
            "type": "kline",
            "data": {**data, "symbol": symbol},
            "timestamp": datetime.now().isoformat(),
        },
        channel,
    )


async def broadcast_trade(symbol: str, data: dict):
    """Broadcast trade to subscribers."""
    symbol = symbol.strip().upper()
    channel = f"trades_{symbol}"
    await manager.broadcast(
        {
            "type": "trade",
            "data": {**data, "symbol": symbol},
            "timestamp": datetime.now().isoformat(),
        },
        channel,
    )


async def broadcast_signal(signal: dict):
    """Broadcast new trading signal."""
    await manager.broadcast(
        {
            "type": "signal",
            "data": signal,
            "timestamp": datetime.now().isoformat(),
        },
        "signals",
    )


async def broadcast_signal_resync() -> None:
    await manager.broadcast(
        {"type": "resync", "reason": "signal_feed_reset", "timestamp": datetime.now().isoformat()},
        "signals",
    )


def publish_signal(signal: dict) -> bool:
    """
    Publish a signal update from any context (sync or async).

    Returns:
        True if event was scheduled, False if no realtime loop is active.
    """
    return _schedule_coro(broadcast_signal(signal))


async def broadcast_bist_update(stocks: list[dict]):
    """Broadcast BIST data update."""
    await manager.broadcast(
        {
            "type": "bist",
            "data": stocks,
            "timestamp": datetime.now().isoformat(),
        },
        "ticker",
    )


# ==================== Status Endpoint ====================


@router.get("/status")
async def realtime_status():
    """Get real-time service status."""
    from api.runtime.realtime_bootstrap import get_realtime_status

    return {
        "connections": manager.total_connections,
        "channels": {channel: len(conns) for channel, conns in manager._active_connections.items()},
        "timestamp": datetime.now().isoformat(),
        **get_realtime_status(),
    }
