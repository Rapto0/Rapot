"""Process-local reader of the shared SQLite signal table.

Startup snapshots the high watermark; clients fetch REST after connecting.
The cursor is intentionally not a delivery receipt or a durable replay offset.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any

from infrastructure.persistence import signal_feed_repository as repository
from logger import get_logger

logger = get_logger(__name__)


async def _read_in_thread(reader: Callable[..., Any], **kwargs: Any) -> Any:
    task = asyncio.create_task(asyncio.to_thread(reader, **kwargs))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        # The driver cannot cancel a running SQLite call. Drain this read-only
        # operation so its session closes before lifecycle shutdown completes.
        with suppress(Exception):
            await task
        raise


class SignalFeed:
    def __init__(
        self,
        *,
        emit_signal: Callable[[dict[str, Any]], Awaitable[None]],
        emit_resync: Callable[[], Awaitable[None]],
        poll_interval: float = 1.0,
        batch_size: int = 100,
        on_health: Callable[[bool, str | None], None] | None = None,
    ) -> None:
        if poll_interval <= 0 or not 1 <= batch_size <= 1000:
            raise ValueError("Invalid signal feed polling configuration")
        self.cursor: int | None = None
        self._emit_signal = emit_signal
        self._emit_resync = emit_resync
        self._poll_interval = poll_interval
        self._batch_size = batch_size
        self._on_health = on_health
        self._task: asyncio.Task[None] | None = None
        self._last_error: str | None = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def _report_health(self, ready: bool, error: str | None = None) -> None:
        if error and error != self._last_error:
            logger.warning("Signal feed paused; committed rows retained: %s", error)
        self._last_error = error
        if self._on_health is not None:
            self._on_health(ready, error)

    async def start(self) -> None:
        if self.running:
            return
        # Lifespan awaits this before accepting any WebSocket connections.
        self.cursor = await _read_in_thread(repository.get_signal_feed_max_id)
        self._report_health(True)
        self._task = asyncio.create_task(self._run(), name="rapot-signal-feed")

    async def stop(self) -> None:
        task = self._task
        if task is not None:
            task.cancel()
            try:
                with suppress(asyncio.CancelledError):
                    await task
            finally:
                self._task = None
        self._report_health(False)

    async def poll_once(self) -> int:
        if self.cursor is None:
            raise RuntimeError("Signal feed must initialize before polling")
        batch = await _read_in_thread(
            repository.read_signal_feed_batch, after_id=self.cursor, limit=self._batch_size
        )
        if batch.max_id < self.cursor:
            # DB restore/reset: REST is authoritative. Do not replay old rows as
            # new notifications. Equal/higher-ID replacements require REST too.
            await self._emit_resync()
            self.cursor = batch.max_id
            return 0
        published = 0
        for signal in batch.signals:
            await self._emit_signal(signal)
            self.cursor = signal["id"]
            published += 1
        return published

    async def _run(self) -> None:
        while True:
            try:
                await self.poll_once()
                self._report_health(True)
            except Exception as exc:
                self._report_health(False, f"{type(exc).__name__}: {exc}")
            await asyncio.sleep(self._poll_interval)
