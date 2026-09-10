"""Offline process-boundary acceptance using a fresh temporary database only.

Run with ``python -m scripts.smoke_signal_feed``. No provider, bot, broker or API
lifespan is started. The real signal WebSocket route is driven directly as ASGI;
a separate Python process writes through the real repository, without a publisher.
"""

from __future__ import annotations

import ast
import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

WRITER = """
import json, os, sys
from pathlib import Path
base = Path.cwd().resolve()
assert (base / '.signal-feed-smoke').read_text() == 'temporary-offline-test'
assert Path(os.environ['DATABASE_PATH']).resolve().parent == base
from db_session import get_session, get_engine
from infrastructure.persistence.signal_repository import save_signal
from models import Signal
import signal_dispatcher
assert signal_dispatcher._publisher is None
try:
    with get_session() as session:
        session.add(Signal(symbol='ROLLED_BACK', market_type='BIST', strategy='COMBO',
                           signal_type='AL', timeframe='1D', score='+4/-0', price=1))
        session.flush()
        raise RuntimeError('intentional rollback')
except RuntimeError:
    pass
ids = [save_signal(symbol=f'{sys.argv[1]}{i}', market_type='Kripto', strategy='COMBO',
                   signal_type='AL', timeframe='1D', score='+4/-0', price=123.5,
                   special_tag='BELES') for i in range(int(sys.argv[2]))]
get_engine().dispose()
print(json.dumps({'ids': ids, 'publisher_registered': False}))
"""


def isolate_environment(base: Path) -> None:
    """Remove account settings before any application module can load a singleton."""
    for relative, class_name, prefix in (
        ("settings.py", "Settings", ""),
        ("middleware/infra/settings.py", "MiddlewareSettings", "MW_"),
    ):
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        keys = {
            prefix + field.target.id.upper()
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == class_name
            for field in node.body
            if isinstance(field, ast.AnnAssign) and isinstance(field.target, ast.Name)
        }
        for key in list(os.environ):
            if key.upper() in keys:
                del os.environ[key]
    os.environ.update(
        TELEGRAM_TOKEN="offline-unused-token",
        TELEGRAM_CHAT_ID="offline-unused-chat",
        APP_ENV="test",
        AI_ENABLED="0",
        RUN_EMBEDDED_BOT="false",
        JWT_SECRET_KEY="offline-smoke-secret-never-used-for-real-sessions",
        DATABASE_PATH=str(base / "signals.sqlite3"),
        DATABASE_URL="",
        CACHE_DATABASE_PATH=str(base / "cache.sqlite3"),
        PYTHONPATH=str(ROOT),
    )
    os.chdir(base)
    (base / ".signal-feed-smoke").write_text("temporary-offline-test")


async def write_in_separate_process(prefix: str, count: int) -> list[int]:
    completed = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-X", "utf8", "-B", "-c", WRITER, prefix, str(count)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if completed.returncode:
        raise RuntimeError("Isolated writer failed: " + completed.stderr[-2000:])
    result = json.loads(completed.stdout.splitlines()[-1])
    assert not result["publisher_registered"]
    assert len(result["ids"]) == count and all(value > 0 for value in result["ids"])
    return result["ids"]


@asynccontextmanager
async def signal_socket(app: Any):
    """Use the production route with in-memory ASGI receive/send queues."""
    incoming: asyncio.Queue = asyncio.Queue()
    outgoing: asyncio.Queue = asyncio.Queue()
    await incoming.put({"type": "websocket.connect"})
    scope = {
        "type": "websocket",
        "asgi": {"version": "3.0", "spec_version": "2.1"},
        "http_version": "1.1",
        "scheme": "ws",
        "path": "/realtime/ws/signals",
        "raw_path": b"/realtime/ws/signals",
        "root_path": "",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "subprotocols": [],
    }
    task = asyncio.create_task(app(scope, incoming.get, outgoing.put))
    try:
        accepted = await asyncio.wait_for(outgoing.get(), timeout=3)
        assert accepted["type"] == "websocket.accept"
        yield outgoing
    finally:
        await incoming.put({"type": "websocket.disconnect", "code": 1000})
        try:
            await asyncio.wait_for(task, timeout=3)
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


async def receive_signal(queue: asyncio.Queue) -> dict[str, Any]:
    message = await asyncio.wait_for(queue.get(), timeout=5)
    assert message["type"] == "websocket.send"
    payload = json.loads(message["text"])
    assert payload["type"] == "signal"
    return payload["data"]


async def verify() -> dict[str, Any]:
    from fastapi import FastAPI

    from api import realtime
    from api.runtime.signal_feed import SignalFeed
    from application.services.signal_trade_service import list_signals
    from db_session import init_db

    init_db()
    app = FastAPI()
    app.include_router(realtime.router)
    feed = SignalFeed(
        emit_signal=realtime.broadcast_signal,
        emit_resync=realtime.broadcast_signal_resync,
        poll_interval=0.02,
        batch_size=2,
    )
    try:
        await feed.start()
        async with signal_socket(app) as messages:
            ids = await write_in_separate_process("LIVE", 5)
            events = [await receive_signal(messages) for _ in ids]
            assert [event["id"] for event in events] == ids
            assert all(event["marketType"] == "Kripto" for event in events)
            assert all(event["specialTag"] == "BELES" for event in events)
            assert all(event["symbol"] != "ROLLED_BACK" for event in events)
        await feed.stop()
        offline_ids = await write_in_separate_process("OFFLINE", 2)
        await feed.start()
        assert feed.cursor == offline_ids[-1]
        async with signal_socket(app) as messages:
            snapshot = list_signals(
                symbol=None,
                strategy=None,
                signal_type=None,
                market_type=None,
                special_tag=None,
                limit=100,
            )
            assert {row["id"] for row in snapshot} == set(ids + offline_ids)
            assert not any(row["symbol"] == "ROLLED_BACK" for row in snapshot)
            resumed_ids = await write_in_separate_process("RESUMED", 1)
            resumed = await receive_signal(messages)
            assert resumed["id"] == resumed_ids[0]
    finally:
        await feed.stop()
    assert not feed.running and realtime.manager.total_connections == 0
    return {
        "status": "verified",
        "live_events": len(events),
        "offline_rows_recovered_by_read_model": len(offline_ids),
        "events_after_restart": 1,
        "rolled_back_rows": 0,
        "publisher_registered_in_writer": False,
        "remaining_connections": realtime.manager.total_connections,
    }


def main() -> None:
    original_directory = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="rapot-signal-feed-smoke-") as temporary:
        isolate_environment(Path(temporary).resolve())
        try:
            result = asyncio.run(verify())
        finally:
            from db_session import get_engine

            get_engine().dispose()
            logging.shutdown()
            # Windows cannot remove the current working directory.
            os.chdir(original_directory)
        print(json.dumps(result))


if __name__ == "__main__":
    main()
