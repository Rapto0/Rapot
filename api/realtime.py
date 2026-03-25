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

    def __init__(self):
        self._active_connections: dict[str, list[WebSocket]] = defaultdict(list)
        self._sse_queues: dict[str, list[asyncio.Queue]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, channel: str = "default"):
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        self._active_connections[channel].append(websocket)
        logger.info(f"Client connected to channel: {channel}")

    def disconnect(self, websocket: WebSocket, channel: str = "default"):
        """Remove a WebSocket connection."""
        if websocket in self._active_connections[channel]:
            self._active_connections[channel].remove(websocket)
            logger.info(f"Client disconnected from channel: {channel}")

    async def broadcast(self, message: dict, channel: str = "default"):
        """Broadcast message to all connections in a channel."""
        data = json.dumps(message)

        # WebSocket broadcast
        dead_connections = []
        for connection in self._active_connections[channel]:
            try:
                await connection.send_text(data)
            except Exception as exc:
                logger.warning(
                    "Realtime send failed on channel %s (%s): %s",
                    channel,
                    type(exc).__name__,
                    exc,
                )
                dead_connections.append(connection)

        # Cleanup dead connections
        for conn in dead_connections:
            self.disconnect(conn, channel)

        # SSE broadcast
        for queue in self._sse_queues[channel]:
            with suppress(asyncio.QueueFull):
                queue.put_nowait(message)

    def create_sse_queue(self, channel: str = "default") -> asyncio.Queue:
        """Create a queue for SSE client."""
        queue = asyncio.Queue(maxsize=100)
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


def _schedule_coro(coro: Coroutine[Any, Any, Any]) -> bool:
    """Schedules a coroutine on the current or registered broadcast loop."""
    try:
        running_loop = asyncio.get_running_loop()
        running_loop.create_task(coro)
        return True
    except RuntimeError:
        pass

    if _broadcast_loop is None or not _broadcast_loop.is_running():
        return False

    asyncio.run_coroutine_threadsafe(coro, _broadcast_loop)
    return True


# ==================== WebSocket Endpoints ====================


@router.websocket("/ws/ticker")
async def websocket_ticker(websocket: WebSocket):
    """
    WebSocket endpoint for real-time ticker data.
    Receives both BIST and Crypto ticker updates.
    """
    await manager.connect(websocket, "ticker")
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
        await websocket.send_json(initial_data)

        # Keep connection alive and handle client messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                message = json.loads(data)

                # Handle subscription requests
                if message.get("action") == "subscribe":
                    symbol = message.get("symbol")
                    if symbol:
                        await ws_manager.subscribe_ticker(symbol)
                        await websocket.send_json({"type": "subscribed", "symbol": symbol})

            except TimeoutError:
                # Send heartbeat
                await websocket.send_json(
                    {"type": "heartbeat", "timestamp": datetime.now().isoformat()}
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket, "ticker")
    except Exception:
        logger.exception("WebSocket error on /realtime/ws/ticker.")
        manager.disconnect(websocket, "ticker")


@router.websocket("/ws/kline/{symbol}")
async def websocket_kline(websocket: WebSocket, symbol: str, interval: str = "1m"):
    """
    WebSocket endpoint for real-time kline/candlestick data.
    """
    channel = f"kline_{symbol}_{interval}"
    await manager.connect(websocket, channel)

    try:
        from websocket_manager import ws_manager

        # Subscribe to kline stream
        await ws_manager.subscribe_kline(symbol.upper(), interval)

        # Keep connection alive
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except TimeoutError:
                await websocket.send_json({"type": "heartbeat"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
    except Exception:
        logger.exception("Kline WebSocket error on /realtime/ws/kline/%s.", symbol)
        manager.disconnect(websocket, channel)


@router.websocket("/ws/trades/{symbol}")
async def websocket_trades(websocket: WebSocket, symbol: str):
    """
    WebSocket endpoint for real-time trade stream.
    """
    channel = f"trades_{symbol}"
    await manager.connect(websocket, channel)

    try:
        from websocket_manager import ws_manager

        # Subscribe to trade stream
        await ws_manager.subscribe_agg_trade(symbol.upper())

        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except TimeoutError:
                await websocket.send_json({"type": "heartbeat"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
    except Exception:
        logger.exception("Trades WebSocket error on /realtime/ws/trades/%s.", symbol)
        manager.disconnect(websocket, channel)


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
                await websocket.send_json({"type": "heartbeat"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, "signals")
    except Exception:
        logger.exception("Signals WebSocket error on /realtime/ws/signals.")
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
    channel = f"kline_{symbol}_{interval}"
    await manager.broadcast(
        {
            "type": "kline",
            "data": data,
            "timestamp": datetime.now().isoformat(),
        },
        channel,
    )


async def broadcast_trade(symbol: str, data: dict):
    """Broadcast trade to subscribers."""
    channel = f"trades_{symbol}"
    await manager.broadcast(
        {
            "type": "trade",
            "data": data,
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
    return {
        "connections": manager.total_connections,
        "channels": {channel: len(conns) for channel, conns in manager._active_connections.items()},
        "timestamp": datetime.now().isoformat(),
    }
