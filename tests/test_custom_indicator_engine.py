"""Real engine/repository/hub acceptance with synthetic native candles only.

This validates persistent mixed watchlist delivery records, not TradingView
runtime parity, live data entitlement, Telegram transport or production load.
"""

from datetime import UTC, datetime
from types import SimpleNamespace

import numpy as np
import pandas as pd

from api.routes.advanced_alarm_routes import AlarmWrite
from application.services.advanced_alarm_market_data import AdvancedMarketData
from application.services.advanced_alarm_service import AdvancedAlarmEngine
from application.services.custom_indicator_data import CustomIndicatorData
from infrastructure.repositories import advanced_alarm_repository as repository
from tests.test_advanced_alarm_backend import payload
from tests.test_advanced_alarm_market_data import MemoryCache
from tests.test_custom_indicator_data import SESSION

START = datetime(2026, 10, 13, 14, 0, 30, tzinfo=UTC).timestamp()
SYMBOLS = [
    {"symbol": "THYAO", "market_type": "BIST"},
    {"symbol": "BTCUSDT", "market_type": "Kripto"},
]


class NativeProvider:
    def __init__(self):
        self.epoch = 1
        self.advanced = False
        self.missing_daily = False
        self.calls = []

    def data_epoch(self):
        return self.epoch

    def memory_epoch(self):
        return self.epoch

    def custom_indicator_history(self, symbol, *, exchange, timeframe, bars):
        self.calls.append((symbol, exchange, timeframe, bars))
        if timeframe == "1D":
            if self.missing_daily:
                raise ValueError("Synthetic required timeframe unavailable")
            index = pd.date_range(
                end="2026-10-13", periods=60, freq="B" if exchange == "BIST" else "D", tz="UTC"
            )
            if exchange == "BIST":
                index += pd.Timedelta(hours=7)
            values = np.linspace(100, 20, len(index))
        else:
            assert timeframe == "1"
            index = pd.date_range(end="2026-10-13 14:00", periods=60, freq="min", tz="UTC")
            values = np.linspace(100, 130, len(index))
            if self.advanced:
                values[-1] = 20
                index = index.append(pd.DatetimeIndex([index[-1] + pd.Timedelta(minutes=1)]))
                values = np.append(values, 21)
        result = pd.DataFrame(
            {"Open": values, "High": values + 1, "Low": values - 1, "Close": values}, index=index
        )
        result.attrs.update(native_timeframe=timeframe, session_metadata=SESSION.copy())
        return result


def vote_leaf():
    inputs = {
        **{f"en{i}": i == 1 for i in range(1, 11)},
        "tf1": "1",
        "len1": 2,
        "requiredBuyVotes": 1,
        "requiredSellVotes": 1,
    }
    return {
        "op": "eq",
        "left": {
            "field": "custom",
            "indicator": "rsi_votes",
            "inputs": inputs,
            "output": "buy_signal",
        },
        "right": 1,
    }


def score_leaf():
    inputs = {
        **{
            f"en_{tf}": tf == "1d"
            for tf in ("1d", "2d", "3d", "4d", "5d", "6d", "1w", "2w", "3w", "1m")
        },
        "rsiLength": 2,
    }
    return {
        "op": "lt",
        "left": {
            "field": "custom",
            "indicator": "htf_rsi_score",
            "inputs": inputs,
            "output": "score",
        },
        "right": 30,
    }


def setup_engine(tmp_path):
    clock = [START]
    provider = NativeProvider()
    settings = SimpleNamespace(
        database_path=str(tmp_path / "synthetic.sqlite3"),
        advanced_alarm_cache_path=None,
        advanced_alarm_market_enabled=True,
        advanced_alarm_all_bist_enabled=False,
        advanced_alarm_max_symbols=2000,
        advanced_alarm_quote_stale_seconds=120,
    )
    hub = AdvancedMarketData(settings, cache=MemoryCache(), clock=lambda: clock[0])
    hub._custom = CustomIndicatorData(provider=provider, clock=lambda: clock[0])
    engine = AdvancedAlarmEngine(
        hub, clock=lambda: 10, wall_clock=lambda: datetime.fromtimestamp(clock[0], UTC)
    )
    watchlist = repository.save_watchlist(
        "admin", {"name": "Synthetic mixed custom list", "symbols": SYMBOLS}
    )
    conditions = [vote_leaf(), {"op": "and", "children": [vote_leaf(), score_leaf()]}]
    for number, condition in enumerate(conditions, 1):
        value = AlarmWrite(
            **payload(
                name=f"Synthetic custom {number}",
                category="watchlist",
                scope="watchlist",
                watchlist_id=watchlist["id"],
                symbols=[],
                timeframe="1m",
                trigger="bar_close",
                condition=condition,
                notify_telegram=False,
            )
        ).model_dump()
        repository.save_rule("admin", value)
    return clock, provider, hub, engine


def run_custom_worker_turns(hub, count=8):
    for _ in range(count):
        job = hub.custom._next_job()
        if job:
            hub.custom.process(*job)


def test_custom_watchlist_native_bar_close_records_once_and_survives_reload(tmp_path):
    clock, provider, hub, engine = setup_engine(tmp_path)
    engine.tick()  # Real repository -> rule/member preparation, no network in tick.
    assert not provider.calls
    assert not hub._requests  # Custom native requirements use their separate shared queue.
    run_custom_worker_turns(hub)
    engine.tick()  # Previous closed candle is a non-matching baseline.
    assert engine._runtime["last_error"] is None
    assert engine._runtime["evaluation"]["ready"] == 4
    assert repository.events("admin")["events"] == []
    provider.advanced = True
    clock[0] += 31
    # Native stream boundary, not the removed 30-second full-history poll.
    for member in SYMBOLS:
        hub.custom.native_refresh((member["market_type"], member["symbol"], "1"))
    run_custom_worker_turns(hub)
    engine.tick()
    events = repository.events("admin")["events"]
    assert len(events) == 4
    assert {row["symbol"] for row in events} == {"THYAO", "BTCUSDT"}
    assert {row["delivery_status"] for row in events} == {"not_requested"}
    assert all(row["bar_time"] == "2026-10-13T14:00:00Z" for row in events)
    assert repository.delivery_status("admin")["pending"] == 0
    for _ in range(3):
        engine.tick()
    assert len(repository.events("admin")["events"]) == 4
    reloaded = AdvancedAlarmEngine(
        hub, clock=lambda: 10, wall_clock=lambda: datetime.fromtimestamp(clock[0], UTC)
    )
    reloaded.tick()
    assert reloaded._runtime["last_error"] is None
    assert len(repository.events("admin")["events"]) == 4
    # Account change invalidates prior values. Returning ready data is a new
    # baseline, never a replay of the most recently closed buy signal.
    provider.epoch += 1
    reloaded.tick()
    assert reloaded._runtime["evaluation"]["ready"] == 0
    hub.custom.invalidate()
    run_custom_worker_turns(hub)
    reloaded.tick()
    assert len(repository.events("admin")["events"]) == 4
    assert repository.delivery_status("admin")["pending"] == 0


def test_missing_required_timeframe_never_creates_custom_alarm_event(tmp_path):
    clock, provider, hub, engine = setup_engine(tmp_path)
    # Only the compound rule requires a daily frame for both markets. Keep the
    # independent minute-only crypto RSI rule out of this missing-HTF scenario.
    for selected in repository.list_rules("admin"):
        if selected["name"].endswith("1"):
            repository.save_rule("admin", {**selected, "enabled": False}, selected["id"])
    provider.missing_daily = True
    engine.tick()
    run_custom_worker_turns(hub)
    engine.tick()
    provider.advanced = True
    clock[0] += 31
    run_custom_worker_turns(hub)
    engine.tick()
    assert engine._runtime["last_error"] is None
    assert engine._runtime["evaluation"]["ready"] == 0
    assert repository.events("admin")["events"] == []
    assert repository.delivery_status("admin")["pending"] == 0
