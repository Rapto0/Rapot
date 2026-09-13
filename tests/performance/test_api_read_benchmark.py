"""Opt-in, offline ASGI benchmark; prints aggregate JSON, never production data.

PowerShell: $env:RAPOT_RUN_API_BENCHMARK='1'; python -m pytest -s <this file>
The root conftest enforces environment/network/SQLite isolation. No app lifespan
is entered: external feeds and schedulers are not part of this measurement.
"""

import asyncio
import json
import math
import os
import platform
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from types import SimpleNamespace

import httpx2
import pytest
from sqlalchemy import event

SIGNALS = 1_750_000
TRADES = 25_000
ROUNDS = 20
PATHS = (
    "/health",
    "/signals?market_type=BIST&limit=150",
    "/signals?market_type=Kripto&limit=150",
    "/signals?special_tag=BELES&limit=50",
    "/signals?special_tag=COK_UCUZ&limit=50",
    "/signals/1750000",
    "/trades?limit=50",
    "/stats",
)
# Fixed before running this representative dashboard scenario; local acceptance,
# not a production SLA. Artificial SQL waits only gate WS/event-loop responsiveness.
RESPONSIVENESS_P95_MS = 250
REST_P95_MS = 500
pytestmark = pytest.mark.skipif(
    os.environ.get("RAPOT_RUN_API_BENCHMARK") != "1", reason="opt-in offline load measurement"
)


def _summary(values: list[float]) -> dict[str, float | int]:
    ordered = sorted(values)
    return {
        "n": len(values),
        "p50_ms": round(ordered[math.ceil(len(values) * 0.50) - 1], 3),
        "p95_ms": round(ordered[math.ceil(len(values) * 0.95) - 1], 3),
        "max_ms": round(max(values), 3),
    }


def _seed(engine) -> None:
    # SQL generation keeps Python memory bounded; indexes match the actual schema.
    with engine.begin() as connection:
        connection.exec_driver_sql(
            f"""WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n WHERE x<{SIGNALS})
            INSERT INTO signals
                (symbol,market_type,strategy,signal_type,timeframe,price,special_tag,created_at)
            SELECT 'SYN'||(x%100), CASE WHEN x%2=0 THEN 'BIST' ELSE 'Kripto' END,
                CASE WHEN x%3=0 THEN 'HUNTER' ELSE 'COMBO' END,
                CASE WHEN x%5=0 THEN 'SAT' ELSE 'AL' END, '1D', 100.0+(x%50),
                CASE WHEN x%7=0 THEN 'BELES' WHEN x%11=0 THEN 'COK_UCUZ' ELSE NULL END,
                datetime('2026-01-01', '+'||x||' seconds') FROM n"""
        )
        connection.exec_driver_sql(
            f"""WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n WHERE x<{TRADES})
            INSERT INTO trades
                (symbol,market_type,direction,price,quantity,pnl,status,created_at)
            SELECT 'SYN'||(x%100), 'BIST', 'BUY', 100, 1, (x%11)-5,
                CASE x%3 WHEN 0 THEN 'OPEN' WHEN 1 THEN 'CLOSED' ELSE 'CANCELLED' END,
                datetime('2026-01-01', '+'||x||' seconds') FROM n"""
        )


@asynccontextmanager
async def _socket(app):
    incoming, outgoing = asyncio.Queue(), asyncio.Queue()
    await incoming.put({"type": "websocket.connect"})
    task = asyncio.create_task(
        app(
            {
                "type": "websocket",
                "asgi": {"version": "3.0"},
                "scheme": "ws",
                "path": "/realtime/ws/signals",
                "raw_path": b"/realtime/ws/signals",
                "query_string": b"",
                "headers": [],
                "subprotocols": [],
                "client": ("benchmark", 1),
                "server": ("benchmark", 80),
            },
            incoming.get,
            outgoing.put,
        )
    )
    try:
        assert (await asyncio.wait_for(outgoing.get(), 10))["type"] == "websocket.accept"
        yield outgoing
    finally:
        await incoming.put({"type": "websocket.disconnect", "code": 1000})
        try:
            await asyncio.wait_for(task, 10)
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)


async def _workload(app, manager, client, *, sockets: bool, rounds: int) -> dict:
    samples = defaultdict(list)
    for _ in range(rounds):
        start, rest_done = time.perf_counter(), asyncio.Event()

        async def request(path, enqueued=start):
            response = await client.get(path)
            assert response.status_code == 200, (path, response.status_code)
            samples[path].append((time.perf_counter() - enqueued) * 1000)

        async def websocket_probe(enqueued=start):
            async with _socket(app) as outgoing:
                samples["ws_handshake"].append((time.perf_counter() - enqueued) * 1000)
                while True:
                    message = await asyncio.wait_for(outgoing.get(), 10)
                    assert message["type"] == "websocket.send"
                    payload = json.loads(message["text"])
                    if payload["type"] == "benchmark_done":
                        return
                    samples["ws_delivery"].append(
                        max(0, time.perf_counter() - payload["scheduled_at"]) * 1000
                    )

        async def pulse(done=rest_done):
            while not done.is_set():
                deadline = time.perf_counter() + 0.005
                await asyncio.sleep(0.005)
                samples["loop_lag"].append(max(0, time.perf_counter() - deadline) * 1000)

        async def broadcast(done=rest_done, scheduled=start):
            while manager.total_connections < 3:
                await asyncio.sleep(0)
            while True:
                await manager.broadcast({"type": "benchmark", "scheduled_at": scheduled}, "signals")
                if done.is_set():
                    await manager.broadcast({"type": "benchmark_done"}, "signals")
                    return
                scheduled = time.perf_counter() + 0.020
                await asyncio.sleep(0.020)

        # Arm recurring probes first, then enqueue REST and WS on the same loop.
        # Inline SQL may finish before WS accepts; its first delivery still times from start.
        jobs = [asyncio.create_task(pulse())]
        if sockets:
            jobs.append(asyncio.create_task(broadcast()))
        requests = [asyncio.create_task(request(path)) for path in PATHS]
        jobs += requests
        if sockets:
            jobs += [asyncio.create_task(websocket_probe()) for _ in range(3)]
        try:
            await asyncio.wait_for(asyncio.gather(*requests), 30)
            rest_done.set()
            await asyncio.wait_for(asyncio.gather(*jobs), 10)
        finally:
            rest_done.set()
            for task in jobs:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*jobs, return_exceptions=True)
        assert manager.total_connections == 0
        samples["round"].append((time.perf_counter() - start) * 1000)
    return {name: _summary(values) for name, values in samples.items()}


async def _validate(client) -> dict:
    checks = {}
    for path in ("/signals?limit=0", "/signals?limit=1200", "/trades?limit=0", "/trades?limit=501"):
        assert (await client.get(path)).status_code == 422
    checks["invalid_limits"] = 4
    filters = {
        "symbol": "SYN0",
        "strategy": "HUNTER",
        "signal_type": "AL",
        "market_type": "BIST",
        "special_tag": "BELES",
    }
    for name, value in filters.items():
        response = await client.get("/signals", params={name: value, "limit": 7})
        rows = response.json()
        assert response.status_code == 200 and len(rows) == 7
        assert all(row[name] == value for row in rows)
    combined = (await client.get("/signals", params={**filters, "limit": 7})).json()
    # SYN0 is always SAT in this synthetic data: all filters must actually apply.
    assert combined == []
    rows = (await client.get("/signals?special_tag=COK_UCUZ&limit=50")).json()
    assert len(rows) == 50 and all(row["special_tag"] == "COK_UCUZ" for row in rows)
    checks["signal_filters"] = len(filters) + 2
    rows = (await client.get("/trades?symbol=SYN0&status=CLOSED&limit=7")).json()
    assert len(rows) == 7 and all(r["symbol"] == "SYN0" and r["status"] == "CLOSED" for r in rows)
    assert (await client.get("/signals/1750001")).status_code == 404
    stats = (await client.get("/stats")).json()
    assert stats["total_signals"] == SIGNALS and stats["total_trades"] == TRADES
    assert stats["open_trades"] == 8333 and stats["closed_trades"] == 8334
    checks.update(trade_filters=True, missing_signal_404=True, mixed_stats=True)
    return checks


def _acceptance(report: dict) -> dict:
    checks = {}
    for scenario in ("threaded_rest", "threaded_3ws", "threaded_sql_delay_20ms"):
        metrics = {"loop_lag": RESPONSIVENESS_P95_MS}
        if scenario != "threaded_rest":
            metrics["ws_handshake"] = RESPONSIVENESS_P95_MS
            metrics["ws_delivery"] = RESPONSIVENESS_P95_MS
        if scenario != "threaded_sql_delay_20ms":
            metrics.update(dict.fromkeys(PATHS, REST_P95_MS))
            metrics["/health"] = RESPONSIVENESS_P95_MS
        for metric, budget in metrics.items():
            observed = report[scenario][metric]["p95_ms"]
            checks[f"{scenario}:{metric}"] = {
                "p95_ms": observed,
                "budget_ms_exclusive": budget,
                "passed": observed < budget,
            }
    return {"passed": all(check["passed"] for check in checks.values()), "checks": checks}


@pytest.mark.asyncio
async def test_offline_api_read_benchmark(monkeypatch, tmp_path):
    import api.main as api_main
    import api.realtime as realtime
    import db_session
    import market_scanner
    from infrastructure.repositories import signal_trade_repository as repository

    for name in ("_engine", "_SessionFactory", "_ScopedSession"):
        monkeypatch.setattr(db_session, name, None)
    engine = db_session.get_engine(tmp_path / "benchmark.sqlite3")
    monkeypatch.setattr(api_main.limiter, "enabled", False)
    monkeypatch.setattr(api_main, "_RUNTIME_STATE", {"db_ready": True, "realtime_ready": True})
    monkeypatch.setattr(market_scanner, "get_scan_count", lambda: 0)
    manager = realtime.ConnectionManager()
    monkeypatch.setattr(realtime, "manager", manager)
    started = time.perf_counter()
    db_session.init_db()
    try:
        _seed(engine)
        report = {
            "scope": "isolated local ASGI, no lifespan/network/providers; not a VPS diagnosis",
            "python": platform.python_version(),
            "platform": platform.system(),
            "signals": SIGNALS,
            "trades": TRADES,
            "rounds": ROUNDS,
            "seed_seconds": round(time.perf_counter() - started, 3),
            "latency": "shared-enqueue to response completion, nearest-rank percentiles",
            "method": "warm caches, fixed inline-then-threaded order, rate limiter disabled",
            "inline_model": (
                "current SQL + inline simulation of all api_main.to_thread calls, "
                "including health; not a historical commit checkout"
            ),
            "rest_wave": list(PATHS),
            "websockets": (
                "3 same-loop ASGI connections enqueued with REST, kept through wave completion; "
                "inline SQL may delay acceptance until after REST"
            ),
            "probes": (
                "5ms loop pulse through whole REST wave; 20ms broadcast; ws_delivery measures "
                "scheduled broadcast time to receive, including event-loop scheduling delay"
            ),
            "sql_sentinel": "20ms sleep per statement; 5 rounds, artificial delay only",
        }
        calls = {
            "signals": lambda: repository.list_signals(
                symbol=None,
                strategy=None,
                signal_type=None,
                market_type=None,
                special_tag=None,
                limit=50,
            ),
            "detail": lambda: repository.get_signal_by_id(SIGNALS),
            "trades": lambda: repository.list_trades(symbol=None, status=None, limit=50),
            "stats": repository.get_trade_stats_aggregate,
        }
        report["repository"] = {}
        for name, call in calls.items():
            call()  # Untimed warm-up; reported repetitions use warm caches.
            values = []
            for _ in range(ROUNDS):
                started = time.perf_counter()
                call()
                values.append((time.perf_counter() - started) * 1000)
            report["repository"][name] = _summary(values)

        async def inline(function, /, *args, **kwargs):
            return function(*args, **kwargs)

        def delay_sql(*args):
            time.sleep(0.020)

        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=api_main.app), base_url="http://benchmark"
        ) as client:
            report["validation"] = await _validate(client)
            for mode in ("inline", "threaded"):
                with monkeypatch.context() as patch:
                    if mode == "inline":
                        patch.setattr(api_main, "asyncio", SimpleNamespace(to_thread=inline))
                    for sockets in (False, True):
                        key = f"{mode}_{'3ws' if sockets else 'rest'}"
                        await _workload(api_main.app, manager, client, sockets=sockets, rounds=1)
                        report[key] = await _workload(
                            api_main.app, manager, client, sockets=sockets, rounds=ROUNDS
                        )
                    event.listen(engine, "before_cursor_execute", delay_sql)
                    try:
                        report[f"{mode}_sql_delay_20ms"] = await _workload(
                            api_main.app, manager, client, sockets=True, rounds=5
                        )
                    finally:
                        event.remove(engine, "before_cursor_execute", delay_sql)
                assert engine.pool.checkedout() == 0
            report["validation"].update(
                session_cleanup=True, reconnect=True, active_websockets=manager.total_connections
            )
        report["acceptance"] = _acceptance(report)
        print("RAPOT_API_BENCHMARK=" + json.dumps(report, sort_keys=True))
        assert report["acceptance"]["passed"], (
            "Local performance budget exceeded; see aggregate JSON"
        )
    finally:
        # Cancelling an awaiting task does not stop its synchronous SQL worker.
        # Join this function-scoped loop's executor before closing database connections.
        await asyncio.get_running_loop().shutdown_default_executor()
        engine.dispose()
