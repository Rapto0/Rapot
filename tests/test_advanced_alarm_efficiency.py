"""Production engine/hub with shared synthetic mixed-market inputs; no provider or Telegram I/O."""

import json
import os
import time
import tracemalloc
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import func, select

from api.routes.advanced_alarm_routes import AlarmWrite
from application.services.advanced_alarm_market_data import AdvancedMarketData
from application.services.advanced_alarm_service import AdvancedAlarmEngine
from db_session import get_session_factory
from infrastructure.repositories import advanced_alarm_repository as repository
from models import AdvancedAlarmRule, AdvancedAlarmState
from tests.test_advanced_alarm_backend import payload
from tests.test_advanced_alarm_market_data import NOW, MemoryCache, Provider


def test_three_thousand_rules_share_mixed_watchlist_data_with_bounded_ticks(tmp_path):
    symbols = [
        {"symbol": "THYAO", "market_type": "BIST"},
        {"symbol": "BTCUSDT", "market_type": "Kripto"},
    ]
    watchlist = repository.save_watchlist("admin", {"name": "Synthetic mixed", "symbols": symbols})
    condition = {
        "op": "and",
        "children": [
            {"op": "gte", "left": {"field": field}, "right": 0}
            for field in ("price", "close", "rsi", "ema") * 8
        ],
    }
    now = datetime.fromtimestamp(NOW, UTC)
    with get_session_factory()() as session:
        for category in ("price", "technical", "watchlist"):
            params = AlarmWrite(
                **payload(
                    category=category,
                    symbols=[] if category == "watchlist" else symbols,
                    scope="watchlist" if category == "watchlist" else "symbols",
                    watchlist_id=watchlist["id"] if category == "watchlist" else None,
                    condition=payload()["condition"] if category == "price" else condition,
                )
            ).model_dump()
            session.add_all(
                AdvancedAlarmRule(
                    id=f"{category}-{number:04}",
                    owner="admin",
                    revision=1,
                    symbols_json=json.dumps(params["symbols"]),
                    condition_json=json.dumps(params["condition"]),
                    created_at=now.replace(tzinfo=None),
                    updated_at=now.replace(tzinfo=None),
                    **{
                        key: value
                        for key, value in params.items()
                        if key not in {"symbols", "condition", "revision"}
                    },
                )
                for number in range(1000)
            )
        session.commit()
    settings = SimpleNamespace(
        database_path=str(tmp_path / "synthetic.sqlite3"),
        advanced_alarm_cache_path=None,
        advanced_alarm_market_enabled=True,
        advanced_alarm_all_bist_enabled=False,
        advanced_alarm_max_symbols=2000,
        advanced_alarm_quote_stale_seconds=120,
    )
    provider = Provider()
    hub = AdvancedMarketData(settings, provider=provider, cache=MemoryCache(), clock=lambda: NOW)
    engine = AdvancedAlarmEngine(hub, clock=lambda: 10, wall_clock=lambda: now)
    tracemalloc.start()
    try:
        baseline, _ = tracemalloc.get_traced_memory()
        engine.tick()  # Configure and record unknowns; does not request network data.
        assert len(hub._requests) == 2
        for key in hub._requests:
            hub.fetch_history(key, hub._refs(key), hub._reset_count)
        for item in symbols:
            hub.enqueue_quote(
                item["symbol"], {"price": 99, "source_timestamp": NOW}, market=item["market_type"]
            )
        hub.poll()
        for _ in range(24):
            engine.tick()
        retained, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert len(engine._states) == 6000
    assert engine._runtime["last_error"] is None
    assert len(hub._series) == 2
    memberships = list(hub._rules.values())
    assert all(members is memberships[0] for members in memberships)
    assert provider.calls == [
        ("history", "THYAO", "BIST", "1m"),
        ("history", "BTCUSDT", "Kripto", "1m"),
    ]
    with get_session_factory()() as session:
        assert session.scalar(select(func.count()).select_from(AdvancedAlarmState)) == 6000
    durations, checked = [], []
    engine._clock = time.monotonic
    cpu = time.process_time()
    for _ in range(6):
        start = time.perf_counter()
        engine.tick()
        durations.append(time.perf_counter() - start)
        result = engine._runtime["evaluation"]
        checked.append(result["checked"])
        assert result["state_changes"] == 0
        assert 0 < result["checked"] <= result["max_comparisons"]
    assert repository.events("admin")["events"] == []
    assert retained - baseline < 32 * 1024**2
    sample = {
        "kind": "synthetic_real_engine_hub_temp_sqlite_no_network_no_telegram",
        "rules": 3000,
        "watchlist_rules": 1000,
        "mixed_symbols": 2,
        "rule_symbol_pairs": 6000,
        "technical_leaves": 32,
        "shared_native_series": len(hub._series),
        "warm_tick_checked": checked,
        "warm_tick_seconds": durations,
        "warm_cpu_seconds": time.process_time() - cpu,
        "retained_python_bytes": retained - baseline,
        "peak_python_bytes": peak - baseline,
        "provider_network_requests": 0,
        "telegram_requests": 0,
        "production_capacity_proven": False,
    }
    if destination := os.environ.get("RAPOT_ADVANCED_MIXED_REPORT"):
        Path(destination).write_text(json.dumps(sample, indent=2), encoding="utf8")
