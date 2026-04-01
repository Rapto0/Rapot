from __future__ import annotations

import asyncio
from typing import Any

from api.realtime import (
    broadcast_bist_update,
    broadcast_ticker,
    publish_signal,
    register_broadcast_loop,
)
from signal_dispatcher import register_signal_publisher


async def start_realtime_services(*, runtime_state: dict[str, Any], logger: Any) -> None:
    """Start realtime providers and register broadcast wiring."""
    runtime_state["realtime_ready"] = False
    runtime_state["realtime_error"] = None
    try:
        from bist_service import bist_service
        from websocket_manager import ws_manager

        register_broadcast_loop(asyncio.get_running_loop())
        ws_manager.on("ticker", broadcast_ticker)
        bist_service.on_update(broadcast_bist_update)

        await ws_manager.start()
        await bist_service.start()
        register_signal_publisher(publish_signal)

        runtime_state["realtime_ready"] = True
        logger.info("Real-time WebSocket services started")
        logger.info("Otonom Analiz API baslatildi")
    except Exception as exc:
        runtime_state["realtime_error"] = str(exc)
        logger.exception("Real-time services failed to start.")
        raise


async def stop_realtime_services(*, runtime_state: dict[str, Any], logger: Any) -> None:
    """Stop realtime providers and clear runtime publisher."""
    try:
        from bist_service import bist_service
        from websocket_manager import ws_manager

        await ws_manager.stop()
        await bist_service.stop()
        logger.info("Real-time services stopped")
    except Exception:
        logger.exception("Error stopping real-time services.")
    finally:
        register_signal_publisher(None)
        runtime_state["realtime_ready"] = False
