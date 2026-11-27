"""Own the optional closed-candle projection throughout the API lifespan."""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from infrastructure.persistence.rsi_tracker_history import TrackerHistory, pilot_members

logger = logging.getLogger(__name__)
REFRESH_SECONDS = 30


@asynccontextmanager
async def tracker_history_runtime(app, settings):
    source = settings.rsi_tracker_history_source
    if not source:
        yield
        return
    try:
        cache = TrackerHistory(
            Path(settings.cache_database_path).parent,
            source,
            pilot_members(settings.rsi_tracker_history_symbols),
        )
    except ValueError:
        logger.warning("Tracker history source or pilot scope is invalid")
        yield
        return

    try:
        await asyncio.to_thread(cache.load)
    except (OSError, sqlite3.Error, ValueError):
        logger.warning("Tracker history could not load its sidecar")
    app.state.rsi_tracker_history = cache
    stop = asyncio.Event()

    async def prepare():
        while not stop.is_set():
            try:
                await asyncio.to_thread(cache.refresh)
            except (OSError, sqlite3.Error):
                logger.warning("Tracker history refresh failed; keeping its last committed data")
            try:
                await asyncio.wait_for(stop.wait(), timeout=REFRESH_SECONDS)
            except TimeoutError:
                continue

    worker = asyncio.create_task(prepare(), name="tracker-closed-history")
    try:
        yield
    finally:
        stop.set()
        await worker
        app.state.rsi_tracker_history = None
