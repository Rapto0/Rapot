"""Independent engine and durable delivery workers under one process ownership lock."""

from __future__ import annotations

import asyncio
from contextlib import suppress

from api.runtime.server_alarms import alarm_lock_path
from application.services.advanced_alarm_service import deliver_one, get_advanced_alarm_engine
from infrastructure.repositories import advanced_alarm_repository as repository
from infrastructure.runtime_lock import BotAlreadyRunningError, bot_instance_lock
from settings import settings

_task = None
_stop = None


async def _wait(stop, seconds):
    with suppress(TimeoutError):
        await asyncio.wait_for(stop.wait(), timeout=seconds)


async def _evaluate(stop, engine):
    loop = asyncio.get_running_loop()
    while not stop.is_set():
        started = loop.time()
        await asyncio.to_thread(engine.tick)
        await _wait(stop, max(0.01, 1 - (loop.time() - started)))


async def _deliver(stop):
    last_pruned = 0.0
    while not stop.is_set():
        try:
            if asyncio.get_running_loop().time() - last_pruned >= 3600:
                await asyncio.to_thread(repository.prune_history)
                last_pruned = asyncio.get_running_loop().time()
            await deliver_one()
        except Exception:
            # Outbox claims have a durable lease. Do not print exception bodies.
            pass
        await _wait(stop, 1.1)


async def _run(stop):
    engine = get_advanced_alarm_engine()
    while not stop.is_set():
        try:
            with bot_instance_lock(alarm_lock_path().with_name("advanced-alarms.lock")):
                try:
                    await engine.hub.start()
                    engine.set_running(True)
                    await _workers(stop, engine)
                finally:
                    engine.set_running(False)
                    await engine.hub.stop()
        except BotAlreadyRunningError:
            engine.set_running(False)
        except Exception:
            engine.set_running(False)
        if not stop.is_set():
            await _wait(stop, 5)


async def _workers(stop, engine):
    """Drain in-flight DB work and sends before releasing the ownership lock."""
    worker_stop = asyncio.Event()
    tasks = [
        asyncio.create_task(_evaluate(worker_stop, engine)),
        asyncio.create_task(_deliver(worker_stop)),
    ]
    stopping = asyncio.create_task(stop.wait())
    try:
        done, _ = await asyncio.wait([*tasks, stopping], return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            if task is not stopping:
                task.result()
    finally:
        worker_stop.set()
        await asyncio.gather(*tasks, return_exceptions=True)
        stopping.cancel()
        with suppress(asyncio.CancelledError):
            await stopping


async def start_advanced_alarms():
    global _task, _stop
    if not settings.advanced_alarms_enabled or (_task is not None and not _task.done()):
        return
    _stop = asyncio.Event()
    _task = asyncio.create_task(_run(_stop), name="advanced-alarms")
    await asyncio.sleep(0)


async def stop_advanced_alarms():
    global _task, _stop
    if _stop is not None:
        _stop.set()
    if _task is not None:
        await _task
    _task = _stop = None
