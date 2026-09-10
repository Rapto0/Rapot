from __future__ import annotations

import asyncio
from typing import Any

from api.realtime import (
    broadcast_bist_update,
    broadcast_kline,
    broadcast_signal,
    broadcast_signal_resync,
    broadcast_ticker,
    broadcast_trade,
    clear_broadcast_loop,
    register_broadcast_loop,
)
from api.runtime.signal_feed import SignalFeed
from signal_dispatcher import register_signal_publisher

_signal_feed: SignalFeed | None = None
_providers: tuple[Any, Any] | None = None
_status_state: dict[str, Any] = {}


def get_realtime_status() -> dict[str, Any]:
    """Safe operational state; no SQL, provider response bodies or credentials."""
    feed_error = _status_state.get("signal_feed_error")
    crypto, bist = _providers if _providers is not None else (None, None)
    socket = getattr(crypto, "_ws", None)
    return {
        "signal_feed": {
            "running": bool(_signal_feed and _signal_feed.running),
            "ready": bool(_status_state.get("signal_feed_ready")),
            "cursor": _signal_feed.cursor if _signal_feed else None,
            "error_type": str(feed_error).split(":", 1)[0] if feed_error else None,
        },
        "providers": {
            "started": bool(_status_state.get("market_realtime_ready")),
            "binance_connected": bool(socket is not None and not socket.closed),
            "bist_running": bool(getattr(bist, "_running", False)),
            "startup_failed": bool(_status_state.get("market_realtime_error")),
        },
    }


async def _on_kline(data: dict[str, Any]) -> None:
    await broadcast_kline(data["symbol"], data["interval"], data)


async def _on_trade(data: dict[str, Any]) -> None:
    await broadcast_trade(data["symbol"], data)


def _update_readiness(runtime_state: dict[str, Any]) -> None:
    runtime_state["realtime_ready"] = bool(
        runtime_state.get("signal_feed_ready") and runtime_state.get("market_realtime_ready")
    )
    runtime_state["realtime_error"] = runtime_state.get("signal_feed_error") or runtime_state.get(
        "market_realtime_error"
    )


async def start_realtime_services(*, runtime_state: dict[str, Any], logger: Any) -> None:
    """Initialize the DB feed before serving sockets; vendors start independently.

    The shared DB is the sole source of signal events, including embedded/manual
    inserts. Registering a process-local publisher would duplicate those events.
    """
    global _signal_feed, _providers, _status_state
    if _signal_feed is not None and _signal_feed.running:
        return
    _status_state = runtime_state
    runtime_state.update(
        realtime_ready=False,
        realtime_error=None,
        signal_feed_ready=False,
        signal_feed_error=None,
        market_realtime_ready=False,
        market_realtime_error=None,
    )
    register_signal_publisher(None)
    register_broadcast_loop(asyncio.get_running_loop())

    def feed_health(ready: bool, error: str | None) -> None:
        runtime_state["signal_feed_ready"] = ready
        runtime_state["signal_feed_error"] = error
        _update_readiness(runtime_state)

    _signal_feed = SignalFeed(
        emit_signal=broadcast_signal, emit_resync=broadcast_signal_resync, on_health=feed_health
    )
    try:
        # Failure here aborts lifespan; serving sockets without an initial cursor
        # would create a startup race. Provider failures do not stop this feed.
        await _signal_feed.start()
    except BaseException:
        await stop_realtime_services(runtime_state=runtime_state, logger=logger)
        raise

    errors = []
    try:
        from bist_service import bist_service
        from websocket_manager import ws_manager

        _providers = (ws_manager, bist_service)
        ws_manager.on("ticker", broadcast_ticker)
        ws_manager.on("kline", _on_kline)
        ws_manager.on("trade", _on_trade)
        bist_service.on_update(broadcast_bist_update)

        for name, provider in (("binance", ws_manager), ("bist", bist_service)):
            try:
                await provider.start()
            except Exception as exc:
                errors.append(f"{name}: {type(exc).__name__}: {exc}")
                logger.exception("Market realtime provider failed to start: %s", name)
                try:
                    await provider.stop()
                except Exception:
                    logger.exception("Unable to clean up failed provider: %s", name)
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
        logger.exception("Market realtime setup failed; DB signal feed remains active.")
    except BaseException:
        await stop_realtime_services(runtime_state=runtime_state, logger=logger)
        raise
    runtime_state["market_realtime_ready"] = not errors
    runtime_state["market_realtime_error"] = "; ".join(errors) or None
    _update_readiness(runtime_state)
    logger.info("DB signal feed started; market providers ready=%s", not errors)


async def stop_realtime_services(*, runtime_state: dict[str, Any], logger: Any) -> None:
    """Stop every owned task and remove exactly the callbacks registered here."""
    global _signal_feed, _providers
    runtime_state["market_realtime_ready"] = False
    register_signal_publisher(None)
    try:
        if _signal_feed is not None:
            try:
                await _signal_feed.stop()
            except Exception:
                logger.exception("Error stopping DB signal feed.")
            finally:
                _signal_feed = None
        if _providers is not None:
            ws_manager, bist_service = _providers
            ws_manager.off("ticker", broadcast_ticker)
            ws_manager.off("kline", _on_kline)
            ws_manager.off("trade", _on_trade)
            bist_service.off_update(broadcast_bist_update)
            for provider in _providers:
                try:
                    await provider.stop()
                except Exception:
                    logger.exception("Error stopping market realtime provider.")
    finally:
        _providers = None
        clear_broadcast_loop()
        runtime_state["signal_feed_ready"] = False
        runtime_state["realtime_ready"] = False
    logger.info("Real-time services stopped")
