"""Offline REST worker/session regression checks against the real temporary SQLite DB.

Routes and the WebSocket connection manager run on the same event loop. The socket
is an in-memory transport, so these checks do not measure network or VPS latency.
"""

import asyncio
import json
import threading
from contextlib import contextmanager, suppress
from datetime import datetime
from typing import Any

import pytest
from fastapi import Response
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
from starlette.requests import Request

import api.main as api_main
import db_session
from api.realtime import ConnectionManager
from models import Signal, Trade


def _request(path: str) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "scheme": "http",
            "app": api_main.app,
        }
    )


async def _read_endpoint(endpoint: str) -> Any:
    if endpoint == "signals":
        return await api_main.get_signals(
            _request("/signals"),
            symbol="btcusdt",
            strategy="combo",
            signal_type="al",
            market_type="Kripto",
            special_tag="BELES",
            limit=1,
        )
    if endpoint == "signal":
        return await api_main.get_signal(1)
    if endpoint == "trades":
        return await api_main.get_trades(
            _request("/trades"), symbol="btcusdt", status="closed", limit=1
        )
    assert endpoint == "stats"
    return await api_main.get_stats(_request("/stats"))


class MemorySocket:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def accept(self) -> None:
        pass

    async def send_text(self, data: str) -> None:
        self.messages.append(json.loads(data))

    async def close(self, code: int = 1000) -> None:
        raise AssertionError(f"Healthy socket must not be evicted: {code}")


@pytest.fixture
def persisted_records() -> None:
    with db_session.get_session() as session:
        session.add(
            Signal(
                id=1,
                symbol="BTCUSDT",
                market_type="Kripto",
                strategy="COMBO",
                signal_type="AL",
                timeframe="1D",
                score="+4/-0",
                special_tag="BELES",
                price=100,
                created_at=datetime(2026, 9, 12),
            )
        )
        session.add(
            Trade(
                symbol="BTCUSDT",
                market_type="Kripto",
                direction="BUY",
                price=100,
                quantity=2,
                status="CLOSED",
                pnl=7,
            )
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ["signals", "signal", "trades", "stats"])
@pytest.mark.parametrize("outcome", ["success", "error", "cancel"])
async def test_slow_rest_read_keeps_health_and_websocket_live_and_releases_session(
    persisted_records, monkeypatch, endpoint: str, outcome: str
) -> None:
    loop = asyncio.get_running_loop()
    loop_thread = threading.get_ident()
    entered, finished = asyncio.Event(), asyncio.Event()
    release = threading.Event()
    engine = db_session.get_engine()
    sessions = []
    worker_threads = []
    original_session = db_session.get_session
    blocked = False

    @contextmanager
    def observe_completion():
        try:
            with original_session() as session:
                sessions.append(session)
                yield session
        finally:
            if threading.get_ident() in worker_threads:
                loop.call_soon_threadsafe(finished.set)

    def slow_first_query(_connection, _cursor, statement, _parameters, _context, _many):
        nonlocal blocked
        if blocked or not statement.lstrip().upper().startswith("SELECT"):
            return
        blocked = True
        worker_threads.append(threading.get_ident())
        loop.call_soon_threadsafe(entered.set)
        if not release.wait(timeout=5):
            raise AssertionError("REST read blocked its event loop or test did not release it")
        if outcome == "error":
            raise OperationalError(statement, {}, RuntimeError("synthetic read failure"))

    monkeypatch.setattr(db_session, "get_session", observe_completion)
    api_main._RUNTIME_STATE.update(db_ready=True, realtime_ready=True)
    event.listen(engine, "before_cursor_execute", slow_first_query)
    manager = ConnectionManager()
    socket = MemorySocket()
    read_task = asyncio.create_task(_read_endpoint(endpoint))
    try:
        await asyncio.wait_for(entered.wait(), timeout=2)
        assert len(worker_threads) == 1
        assert worker_threads[0] != loop_thread
        assert not read_task.done()
        assert engine.pool.checkedout() == 1

        await asyncio.wait_for(manager.connect(socket, "signals"), timeout=2)
        await asyncio.wait_for(
            manager.broadcast({"type": "heartbeat", "source": "offline-test"}, "signals"),
            timeout=2,
        )
        health_response = Response()
        health = await asyncio.wait_for(
            api_main.health_check(_request("/health"), health_response), timeout=2
        )
        assert health_response.status_code == 200
        assert health.database == "connected"
        assert socket.messages == [{"type": "heartbeat", "source": "offline-test"}]
        assert not read_task.done()

        if outcome == "cancel":
            read_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await read_task
            # Cancellation cannot terminate a running SQLite call. It must close
            # its own session after returning, even though its caller is gone.
            assert not finished.is_set()
            assert engine.pool.checkedout() == 1
            release.set()
        else:
            release.set()
            if outcome == "error":
                with pytest.raises(OperationalError, match="synthetic read failure"):
                    await asyncio.wait_for(read_task, timeout=2)
            else:
                result = await asyncio.wait_for(read_task, timeout=2)
                if endpoint in {"signals", "trades"}:
                    assert len(result) == 1
                    assert result[0].symbol == "BTCUSDT"
                elif endpoint == "signal":
                    assert result.id == 1 and result.special_tag == "BELES"
                else:
                    assert result.total_signals == 1
                    assert result.closed_trades == 1
                    assert result.total_pnl == 7

        await asyncio.wait_for(finished.wait(), timeout=2)
        assert engine.pool.checkedout() == 0
        assert sessions and all(not session.in_transaction() for session in sessions)
    finally:
        release.set()
        try:
            with suppress(asyncio.CancelledError, Exception):
                await read_task
            if blocked:
                await asyncio.wait_for(finished.wait(), timeout=6)
        finally:
            event.remove(engine, "before_cursor_execute", slow_first_query)
            manager.disconnect(socket, "signals")

    assert manager.total_connections == 0
    assert manager._send_locks == {}
