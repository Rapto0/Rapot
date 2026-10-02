"""Own one persistent alarm loop for the API process, independently of browser sessions."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from pathlib import Path

from infrastructure.runtime_lock import BotAlreadyRunningError, bot_instance_lock
from logger import get_logger
from settings import settings

logger = get_logger(__name__)
POLL_SECONDS = 60
_task: asyncio.Task[None] | None = None
_stop: asyncio.Event | None = None


def alarm_lock_path() -> Path:
    """Use the shared SQLite volume without contending with the scanner's own lock."""
    from sqlalchemy.engine import make_url

    from db_session import get_database_url

    url = make_url(get_database_url())
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise RuntimeError("Server alarms require a shared on-disk SQLite database")
    return Path(url.database).resolve().parent / "server-alarms.lock"


async def _run(stop: asyncio.Event, path: Path) -> None:
    from application.services.server_alarm_service import run_alarm_cycle, set_runtime_running

    while not stop.is_set():
        try:
            with bot_instance_lock(path):
                set_runtime_running(True)
                try:
                    while not stop.is_set():
                        try:
                            await run_alarm_cycle(should_stop=stop.is_set)
                        except asyncio.CancelledError:
                            raise
                        except Exception as exc:
                            # Exception text may contain a provider URL or a secret.
                            logger.error("Server alarm cycle failed (%s)", type(exc).__name__)
                        await _wait(stop)
                finally:
                    set_runtime_running(False)
        except BotAlreadyRunningError:
            set_runtime_running(False)
            await _wait(stop)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            set_runtime_running(False)
            logger.error("Server alarm worker unavailable (%s)", type(exc).__name__)
            await _wait(stop)


async def _wait(stop: asyncio.Event) -> None:
    with suppress(TimeoutError):
        await asyncio.wait_for(stop.wait(), timeout=POLL_SECONDS)


async def start_server_alarms() -> None:
    global _task, _stop
    if _task is not None and not _task.done():
        return
    if not settings.server_alarms_enabled:
        return
    _stop = asyncio.Event()
    _task = asyncio.create_task(_run(_stop, alarm_lock_path()), name="server-alarms")
    # Let the worker claim its lock before the API begins reporting its status.
    await asyncio.sleep(0)


async def stop_server_alarms() -> None:
    global _task, _stop
    if _stop is not None:
        _stop.set()
    if _task is not None:
        # The cycle checks stop between bounded provider/delivery requests. Do not
        # abandon an in-flight send and release the lock while its thread continues.
        await _task
    _task = None
    _stop = None
