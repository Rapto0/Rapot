"""UTC deprecation fixes must preserve the main database's naive-UTC contract."""

import json
import sqlite3
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest

import data_loader
import infrastructure.time as clock
import migrate_db
from api.calendar_service import CalendarService
from application.services import signal_trade_service
from db_session import get_engine, get_session
from infrastructure.persistence import ops_repository, signal_repository
from infrastructure.persistence.signal_feed_repository import read_signal_feed_batch
from models import AIAnalysis, BotStat, Order, ScanHistory, Signal, Trade

pytestmark = pytest.mark.filterwarnings("error:.*utcnow.*:DeprecationWarning")


@pytest.fixture
def fixed_clock(monkeypatch: pytest.MonkeyPatch) -> dict[str, datetime]:
    current = {"now": datetime(2026, 9, 11, 1, 2, 3, 456789, tzinfo=UTC)}

    class NonUtcLocalClock(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                # A naive local-clock implementation would silently shift stored values.
                return current["now"].astimezone(timezone(timedelta(hours=3))).replace(tzinfo=None)
            return current["now"].astimezone(tz)

    monkeypatch.setattr(clock, "datetime", NonUtcLocalClock)
    return current


def test_clock_uses_utc_and_removes_only_timezone(fixed_clock: dict[str, datetime]) -> None:
    expected = fixed_clock["now"].replace(tzinfo=None)
    assert clock.utc_now_naive() == expected
    assert clock.utc_now_naive().tzinfo is None
    fixed_clock["now"] += timedelta(microseconds=1)
    assert clock.utc_now_naive() == expected + timedelta(microseconds=1)


def test_real_clock_remains_between_aware_utc_bounds() -> None:
    before = datetime.now(UTC)
    actual = clock.utc_now_naive()
    after = datetime.now(UTC)
    assert actual.tzinfo is None
    assert before <= actual.replace(tzinfo=UTC) <= after


MODEL_CASES = [
    (
        Signal,
        {
            "symbol": "UTC",
            "market_type": "BIST",
            "strategy": "COMBO",
            "signal_type": "AL",
            "timeframe": "1D",
        },
        ("created_at",),
    ),
    (
        Trade,
        {"symbol": "UTC", "market_type": "BIST", "direction": "BUY", "price": 10.0},
        ("created_at",),
    ),
    (Order, {"symbol": "UTC", "market_type": "BIST", "side": "BUY"}, ("created_at", "updated_at")),
    (ScanHistory, {"scan_type": "BIST"}, ("created_at",)),
    (BotStat, {"stat_name": "utc_test", "stat_value": "1"}, ("updated_at",)),
    (
        AIAnalysis,
        {"symbol": "UTC", "market_type": "BIST", "analysis_text": "Offline test"},
        ("created_at",),
    ),
]


@pytest.mark.parametrize(
    ("model", "values", "fields"), MODEL_CASES, ids=[row[0].__name__ for row in MODEL_CASES]
)
def test_all_model_defaults_round_trip_as_naive_utc(
    fixed_clock: dict[str, datetime], model: Any, values: dict[str, Any], fields: tuple[str, ...]
) -> None:
    expected = fixed_clock["now"].replace(tzinfo=None)
    with get_session() as session:
        row = model(**values)
        session.add(row)
        session.flush()
        row_id = row.id
        for field in fields:
            assert getattr(row, field) == expected
            assert getattr(row, field).tzinfo is None
            assert row.to_dict()[field] == expected.isoformat()
    # SQLAlchemy's SQLite adapter could hide an accidental aware value on reload;
    # check both the un-reloaded object above and the exact underlying text below.
    with get_engine().connect() as connection:
        stored = connection.exec_driver_sql(
            f"SELECT {', '.join(fields)} FROM {model.__tablename__} WHERE id = ?", (row_id,)
        ).one()
    assert tuple(stored) == (expected.isoformat(sep=" "),) * len(fields)
    with get_session() as session:
        restored = session.get(model, row_id)
        assert all(getattr(restored, field) == expected for field in fields)
        assert all(getattr(restored, field).tzinfo is None for field in fields)


def test_updates_trade_close_and_counter_use_current_utc_without_changing_created_at(
    fixed_clock: dict[str, datetime],
) -> None:
    created = fixed_clock["now"].replace(tzinfo=None)
    with get_session() as session:
        trade = Trade(symbol="UTC", market_type="BIST", direction="BUY", price=10, quantity=2)
        order = Order(symbol="UTC", market_type="BIST", side="BUY")
        session.add_all([trade, order])
        session.flush()
        trade_id, order_id = trade.id, order.id
    ops_repository.set_bot_stat("utc_test", "first")
    ops_repository.increment_bot_stat_int("counter")

    fixed_clock["now"] += timedelta(days=1, seconds=4)
    updated = fixed_clock["now"].replace(tzinfo=None)
    with get_session() as session:
        trade = session.get(Trade, trade_id)
        trade.close(12)
        order = session.get(Order, order_id)
        order.status = "CLOSED"
        session.flush()
        assert trade.created_at == created and order.created_at == created
        assert trade.closed_at == updated and trade.closed_at.tzinfo is None
        assert trade.pnl == 4 and trade.status == "CLOSED"
        assert order.updated_at == updated and order.updated_at.tzinfo is None
    ops_repository.set_bot_stat("utc_test", "second")
    assert ops_repository.increment_bot_stat_int("counter") == 2
    assert ops_repository.get_bot_stats_last_updated(("utc_test", "counter")) == updated


def test_legacy_row_and_api_timestamp_shapes_are_preserved(
    fixed_clock: dict[str, datetime],
) -> None:
    legacy = "2020-01-02 03:04:05.678901"
    with get_engine().begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO signals (symbol, market_type, strategy, signal_type, timeframe, created_at) "
            "VALUES ('LEGACY', 'BIST', 'COMBO', 'AL', '1D', ?)",
            (legacy,),
        )
    new_id = signal_repository.save_signal("NEW", "BIST", "COMBO", "AL", "1D")
    expected = fixed_clock["now"].replace(tzinfo=None).isoformat()
    listed = signal_trade_service.list_signals(
        symbol="NEW", strategy=None, signal_type=None, market_type=None, special_tag=None, limit=10
    )
    assert listed[0]["created_at"] == expected + "Z"
    assert signal_trade_service.get_signal_by_id(new_id)["created_at"] == expected
    feed = read_signal_feed_batch(after_id=0, limit=10)
    assert next(row for row in feed.signals if row["id"] == new_id)["createdAt"] == expected + "Z"
    with get_engine().connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT created_at FROM signals WHERE symbol = 'LEGACY'"
            ).scalar_one()
            == legacy
        )


def test_signal_tag_age_retains_the_exact_900_second_boundary(
    fixed_clock: dict[str, datetime],
) -> None:
    signal_id = signal_repository.save_signal("UTC", "BIST", "COMBO", "AL", "1D")
    args = ("UTC", "BIST", "COMBO", "AL", "1D", "BELES")
    fixed_clock["now"] += timedelta(seconds=900)
    assert signal_repository.set_signal_special_tag(*args, signal_id=signal_id)
    fixed_clock["now"] += timedelta(microseconds=1)
    assert not signal_repository.set_signal_special_tag(*args, signal_id=signal_id)


def test_lock_expiry_and_json_keep_naive_utc_at_the_ttl_boundary(
    fixed_clock: dict[str, datetime],
) -> None:
    expected_expiry = (fixed_clock["now"] + timedelta(seconds=60)).replace(tzinfo=None).isoformat()
    assert ops_repository.acquire_distributed_lock("utc", "first", ttl_seconds=60)
    payload = json.loads(ops_repository.get_bot_stat("distributed_lock:utc"))
    assert payload["expires_at"] == expected_expiry
    fixed_clock["now"] += timedelta(seconds=59)
    assert ops_repository.get_distributed_lock_state("utc")["locked"] is True
    assert not ops_repository.acquire_distributed_lock("utc", "second", ttl_seconds=60)
    fixed_clock["now"] += timedelta(seconds=1)
    assert ops_repository.get_distributed_lock_state("utc")["locked"] is False
    assert ops_repository.acquire_distributed_lock("utc", "second", ttl_seconds=60)


def test_coverage_since_filter_keeps_inclusive_utc_cutoff(fixed_clock: dict[str, datetime]) -> None:
    cutoff = fixed_clock["now"].replace(tzinfo=None) - timedelta(hours=1)
    with get_session() as session:
        for name, timestamp in (("BOUNDARY", cutoff), ("OLD", cutoff - timedelta(microseconds=1))):
            session.add(
                Signal(
                    symbol=name,
                    market_type="BIST",
                    strategy="COMBO",
                    signal_type="AL",
                    timeframe="1D",
                    created_at=timestamp,
                )
            )
        session.flush()
        query, target = ops_repository._build_special_tag_candidate_query(
            session=session,
            signal_type="AL",
            target_timeframe="1D",
            required_timeframes=("1D",),
            window_seconds=900,
            market_type="BIST",
            strategy="COMBO",
            since_hours=1,
        )
        assert query.with_entities(target.symbol).all() == [("BOUNDARY",)]


def test_offline_order_staleness_uses_same_utc_boundary(fixed_clock: dict[str, datetime]) -> None:
    current = fixed_clock["now"].replace(tzinfo=None)
    with get_session() as session:
        for name, age in (("STALE", timedelta(minutes=180)), ("RECENT", timedelta(minutes=179))):
            session.add(
                Order(
                    symbol=name,
                    market_type="BIST",
                    side="BUY",
                    created_at=current - age,
                    updated_at=current - age,
                )
            )
    summary = ops_repository.reconcile_active_orders_on_startup(stale_minutes=180)
    assert summary["checked"] == 2 and summary["marked_stale"] == 1
    assert summary["exchange_sync_attempted"] is False
    with get_session() as session:
        stale = session.query(Order).filter_by(symbol="STALE").one()
        assert stale.closed_at == current and stale.closed_at.tzinfo is None
        assert stale.status == "STALE"
        assert session.query(Order).filter_by(symbol="RECENT").one().status == "NEW"


@pytest.mark.parametrize("provider", ["binance", "isyatirim", "yfinance"])
def test_provider_fetch_metadata_retains_offsetless_utc(
    fixed_clock: dict[str, datetime],
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
) -> None:
    monkeypatch.setattr(data_loader, "ensure_isyatirim_ca_bundle", lambda: None)
    monkeypatch.setattr(data_loader, "_bist_force_yfinance_fallback", False)
    monkeypatch.setattr(data_loader, "is_suspicious_bist_ohlcv", lambda frame: False)
    if provider == "binance":
        client = SimpleNamespace(
            get_historical_klines=lambda *_args: [
                [0, "10", "12", "9", "11", "100", 0, 0, 0, 0, 0, 0]
            ]
        )
        monkeypatch.setattr(data_loader, "_get_binance_client", lambda: client)
        frame = data_loader.get_crypto_data("OFFLINE")
    elif provider == "isyatirim":
        raw = pd.DataFrame(
            {
                "HGDG_TARIH": ["2026-09-01"],
                "HGDG_ACILIS": [10],
                "HGDG_MAX": [12],
                "HGDG_MIN": [9],
                "HGDG_KAPANIS": [11],
                "HGDG_HACIM": [100],
            }
        )
        monkeypatch.setattr(data_loader, "fetch_stock_data", lambda **_kwargs: raw)
        frame = data_loader.get_bist_data("OFFLINE")
    else:
        import yfinance

        raw = pd.DataFrame(
            {"Open": [10], "High": [12], "Low": [9], "Close": [11], "Volume": [100]},
            index=pd.date_range("2026-09-01", periods=1),
        )
        monkeypatch.setattr(yfinance, "download", lambda **_kwargs: raw)
        frame = data_loader._fetch_bist_data_yfinance("OFFLINE")
    assert frame is not None
    assert frame.attrs["fetched_at_iso"] == fixed_clock["now"].replace(tzinfo=None).isoformat()
    assert datetime.fromisoformat(frame.attrs["fetched_at_iso"]).tzinfo is None


def test_calendar_cache_expiry_stays_utc_naive_and_refetches_at_boundary(
    fixed_clock: dict[str, datetime],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    service = CalendarService()
    service.api_key = "offline-synthetic-key"
    service.cache_ttl_seconds = 60

    def get(*_args: Any, **_kwargs: Any) -> SimpleNamespace:
        calls.append(True)
        return SimpleNamespace(
            raise_for_status=lambda: None, json=lambda: {"economicCalendar": [{"test": len(calls)}]}
        )

    monkeypatch.setattr("api.calendar_service.requests.get", get)
    assert service.get_economic_calendar("2026-09-01", "2026-09-02") == [{"test": 1}]
    expiry = service._cache_expiry["2026-09-01_2026-09-02"]
    assert expiry == (fixed_clock["now"] + timedelta(seconds=60)).replace(tzinfo=None)
    fixed_clock["now"] += timedelta(seconds=59)
    assert service.get_economic_calendar("2026-09-01", "2026-09-02") == [{"test": 1}]
    fixed_clock["now"] += timedelta(seconds=1)
    assert service.get_economic_calendar("2026-09-01", "2026-09-02") == [{"test": 2}]


@pytest.mark.parametrize(
    ("table", "values", "field", "migrate"),
    [
        (
            "signals",
            {
                "symbol": "UTC",
                "market_type": "BIST",
                "strategy": "COMBO",
                "signal_type": "AL",
                "timeframe": "1D",
                "score": "",
                "price": 10,
                "details": "",
            },
            "created_at",
            migrate_db.migrate_signals,
        ),
        (
            "scan_history",
            {"scan_type": "BIST", "symbols_scanned": 1, "signals_found": 0, "duration_seconds": 1},
            "created_at",
            migrate_db.migrate_scan_history,
        ),
        (
            "bot_stats",
            {"stat_name": "utc_test", "stat_value": "1"},
            "updated_at",
            migrate_db.migrate_bot_stats,
        ),
    ],
)
def test_legacy_migration_missing_date_defaults_to_same_naive_utc(
    fixed_clock: dict[str, datetime],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    table: str,
    values: dict[str, Any],
    field: str,
    migrate: Any,
) -> None:
    source = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(source) as connection:
        connection.execute(f"CREATE TABLE {table} ({', '.join(values)}, {field})")
        connection.execute(
            f"INSERT INTO {table} VALUES ({', '.join('?' for _ in range(len(values) + 1))})",
            (*values.values(), None),
        )
    monkeypatch.setattr(migrate_db, "OLD_DB_PATH", source)
    assert migrate() == 1
    with get_engine().connect() as connection:
        stored = connection.exec_driver_sql(f"SELECT {field} FROM {table}").scalar_one()
    assert stored == fixed_clock["now"].replace(tzinfo=None).isoformat(sep=" ")
