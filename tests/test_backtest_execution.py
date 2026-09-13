"""Synthetic daily feeds exercise the real backtest loop without provider access."""

import importlib
import warnings
from copy import deepcopy
from datetime import UTC, datetime
from types import ModuleType
from typing import Any

import pandas as pd
import pytest


@pytest.fixture
def execution() -> ModuleType:
    with warnings.catch_warnings():
        return importlib.import_module("backtesting_system")


@pytest.fixture
def daily_feed() -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "Open": [100.0 + day for day in range(160)],
            "High": [105.0 + day for day in range(160)],
            "Low": [95.0 + day for day in range(160)],
            "Close": [102.0 + day for day in range(160)],
            "Volume": [1000.0] * 160,
        },
        index=pd.date_range("2020-01-01", periods=160, freq="D"),
    )
    frame.attrs["open_quality"] = "provider"
    return frame


def _buy_on_combo(frame: pd.DataFrame, market: str, strategy: str = "combo") -> dict[str, Any]:
    assert market == "BIST"
    assert not frame.empty
    return {
        "buy": {"cok_ucuz": strategy == "combo", "beles": False},
        "sell": {"pahali": False},
    }


def test_end_date_limits_executions_and_equity(
    execution: ModuleType, daily_feed: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        execution,
        "get_bist_data_isyatirim_only",
        lambda *args, **kwargs: daily_feed.copy(deep=True),
    )
    engine = execution.BacktestEngine(start_date="2020-03-01", end_date="2020-04-30")
    monkeypatch.setattr(engine, "check_signals", _buy_on_combo)
    portfolio = execution.Portfolio(100000.0, "BIST", 100.0)

    engine.run_single_symbol("AAA", "BIST", portfolio)

    assert portfolio.all_trades, "The fixture must execute trades inside the requested range."
    assert all(
        pd.Timestamp("2020-03-01") <= trade["Tarih"] <= pd.Timestamp("2020-04-30")
        for trade in portfolio.all_trades
    )
    assert all(row["Tarih"] <= pd.Timestamp("2020-04-30") for row in portfolio.equity_curve)


def test_start_after_the_feed_returns_without_indexing_past_the_end(
    execution: ModuleType, daily_feed: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        execution,
        "get_bist_data_isyatirim_only",
        lambda *args, **kwargs: daily_feed.copy(deep=True),
    )
    engine = execution.BacktestEngine(start_date="2021-01-01", end_date="2021-02-01")
    monkeypatch.setattr(engine, "check_signals", _buy_on_combo)
    portfolio = execution.Portfolio(100000.0, "BIST", 100.0)

    assert engine.run_single_symbol("AAA", "BIST", portfolio) is None
    assert portfolio.cash == 100000.0
    assert not portfolio.all_trades
    assert not portfolio.lots
    assert not portfolio.equity_curve


def _no_provider(*args: Any, **kwargs: Any) -> None:
    pytest.fail("Fixed-data execution must never request provider data.")


def _portfolio_state(portfolio: Any) -> dict[str, Any]:
    return deepcopy(
        {
            "cash": portfolio.cash,
            "lots": {
                symbol: [vars(lot) for lot in queue] for symbol, queue in portfolio.lots.items()
            },
            "trades": portfolio.all_trades,
            "performance": portfolio.symbol_performance,
            "equity": portfolio.equity_curve,
            "commission": portfolio.total_commission_paid,
            "slippage": portfolio.total_slippage_cost,
        }
    )


def _fixed_run(
    execution: ModuleType,
    frame: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
    *,
    start: str = "2020-03-01",
    end: str = "2020-04-30",
    as_of: str = "2020-06-10T00:00:00Z",
    market: str = "BIST",
    signal: Any = None,
) -> Any:
    monkeypatch.setattr(execution, "get_bist_data_isyatirim_only", _no_provider)
    monkeypatch.setattr(execution, "get_crypto_data", _no_provider)
    engine = execution.BacktestEngine(start_date=start, end_date=end, as_of=as_of)

    def default_signal(
        history: pd.DataFrame, selected_market: str, strategy: str = "combo"
    ) -> dict[str, Any]:
        assert selected_market == market
        assert not history.empty
        return {
            "buy": {"cok_ucuz": strategy == "combo", "beles": False},
            "sell": {"pahali": False},
        }

    monkeypatch.setattr(engine, "check_signals", signal or default_signal)
    portfolio = execution.Portfolio(100000.0, market, 100.0)
    engine.run_single_symbol("AAA", market, portfolio, data=frame)
    return portfolio


def test_fixed_data_sorts_a_copy_and_makes_no_provider_calls(
    execution: ModuleType, daily_feed: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    shuffled = daily_feed.sample(frac=1.0, random_state=7)
    before = shuffled.copy(deep=True)
    original_attrs = deepcopy(shuffled.attrs)
    sorted_result = _fixed_run(execution, daily_feed, monkeypatch)
    shuffled_result = _fixed_run(execution, shuffled, monkeypatch)

    pd.testing.assert_frame_equal(shuffled, before)
    assert shuffled.attrs == original_attrs
    assert sorted_result.all_trades
    assert _portfolio_state(shuffled_result) == _portfolio_state(sorted_result)


def test_previous_close_signal_executes_at_next_real_open_with_metadata(
    execution: ModuleType, daily_feed: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    frame = daily_feed.copy(deep=True)
    frame.loc["2020-03-02", ["Open", "High", "Low", "Close"]] = [500.0, 1000.0, 150.0, 999.0]

    def signal(history: pd.DataFrame, market: str, strategy: str) -> dict[str, Any]:
        return {
            "buy": {
                "cok_ucuz": strategy == "combo" and history.index[-1] == pd.Timestamp("2020-03-01"),
                "beles": False,
            },
            "sell": {"pahali": False},
        }

    portfolio = _fixed_run(execution, frame, monkeypatch, signal=signal)
    assert len(portfolio.all_trades) == 1
    trade = portfolio.all_trades[0]
    assert trade["Tarih"] == pd.Timestamp("2020-03-02")
    assert trade["Fiyat"] == 500.0
    assert trade["Sinyal Tarihi"] == pd.Timestamp("2020-03-01")
    assert trade["Yürütme Modeli"] == "next_open"
    assert portfolio.cash == pytest.approx(99900.0)


def test_next_open_means_the_next_observed_bar_across_a_gap(
    execution: ModuleType, daily_feed: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    frame = daily_feed.drop(index=pd.Timestamp("2020-03-02"))
    frame.loc["2020-03-03", ["Open", "High", "Low", "Close"]] = [500.0, 1000.0, 150.0, 999.0]

    def signal(history: pd.DataFrame, market: str, strategy: str) -> dict[str, Any]:
        return {
            "buy": {
                "cok_ucuz": strategy == "combo" and history.index[-1] == pd.Timestamp("2020-03-01"),
                "beles": False,
            },
            "sell": {"pahali": False},
        }

    portfolio = _fixed_run(execution, frame, monkeypatch, signal=signal)
    assert len(portfolio.all_trades) == 1
    trade = portfolio.all_trades[0]
    assert trade["Sinyal Tarihi"] == pd.Timestamp("2020-03-01")
    assert trade["Tarih"] == pd.Timestamp("2020-03-03")
    assert trade["Fiyat"] == 500.0


def test_next_open_buy_and_sell_preserve_the_fifo_cost_and_cash_oracle(
    execution: ModuleType, daily_feed: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    frame = daily_feed.copy(deep=True)
    frame.loc["2020-03-02", ["Open", "High", "Low", "Close"]] = [100.0, 170.0, 90.0, 163.0]
    frame.loc["2020-03-04", ["Open", "High", "Low", "Close"]] = [110.0, 170.0, 100.0, 165.0]
    monkeypatch.setattr(execution, "get_bist_data_isyatirim_only", _no_provider)
    engine = execution.BacktestEngine(
        start_date="2020-03-01", end_date="2020-04-30", as_of="2020-06-10T00:00:00Z"
    )

    def signal(history: pd.DataFrame, market: str, strategy: str) -> dict[str, Any]:
        date = history.index[-1]
        return {
            "buy": {
                "cok_ucuz": strategy == "combo" and date == pd.Timestamp("2020-03-01"),
                "beles": False,
            },
            "sell": {"pahali": strategy == "combo" and date == pd.Timestamp("2020-03-03")},
        }

    monkeypatch.setattr(engine, "check_signals", signal)
    costs = execution.TradingCosts(bist_commission=0.01, bist_slippage=0.02)
    portfolio = execution.Portfolio(2060.0, "BIST", 1030.0, costs)
    assert engine.run_single_symbol("AAA", "BIST", portfolio, data=frame) is True
    purchase, sale = portfolio.all_trades
    assert (purchase["Fiyat"], sale["Fiyat"]) == (100.0, 110.0)
    assert (purchase["Miktar"], sale["Miktar"]) == (10.0, 10.0)
    assert purchase["Sinyal Tarihi"] == pd.Timestamp("2020-03-01")
    assert sale["Sinyal Tarihi"] == pd.Timestamp("2020-03-03")
    assert sale["Tarih"] == pd.Timestamp("2020-03-04")
    assert sale["Yürütme Modeli"] == "next_open"
    assert sale["Maliyet Tabanı"] == 1030.0
    assert sale["Kar/Zarar"] == 37.0
    assert portfolio.cash == pytest.approx(2097.0)
    assert portfolio.total_commission_paid == pytest.approx(21.0)
    assert portfolio.total_slippage_cost == pytest.approx(42.0)
    assert not portfolio.lots
    assert portfolio.symbol_performance["AAA"]["Toplam Kar/Zarar"] == pytest.approx(
        portfolio.cash - portfolio.initial_cash
    )
    assert portfolio.equity_curve[-1]["Toplam Değer"] == 2097.0


def test_first_included_execution_uses_prestart_history_without_exposing_its_own_bar(
    execution: ModuleType, daily_feed: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[pd.Timestamp, pd.Timestamp, int]] = []

    def signal(history: pd.DataFrame, market: str, strategy: str) -> dict[str, Any]:
        seen.append((history.index[0], history.index[-1], len(history)))
        return _buy_on_combo(history, market, strategy)

    portfolio = _fixed_run(
        execution, daily_feed, monkeypatch, start="2020-05-01", end="2020-05-05", signal=signal
    )
    assert [trade["Tarih"] for trade in portfolio.all_trades] == list(
        pd.date_range("2020-05-01", "2020-05-05")
    )
    assert len(seen) == 10  # Both strategies see one immutable prefix per execution day.
    assert seen[0] == (pd.Timestamp("2020-01-01"), pd.Timestamp("2020-04-30"), 121)
    assert seen[-1][1] == pd.Timestamp("2020-05-04")
    for trade in portfolio.all_trades:
        assert trade["Sinyal Tarihi"] < trade["Tarih"]


def test_sixty_warmup_rows_are_not_replaced_by_the_execution_candle(
    execution: ModuleType, daily_feed: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    portfolio = _fixed_run(execution, daily_feed, monkeypatch, start="2020-01-01")
    first = portfolio.all_trades[0]
    assert first["Sinyal Tarihi"] == daily_feed.index[60]
    assert first["Tarih"] == daily_feed.index[61]


def test_signal_without_an_in_range_next_bar_never_becomes_a_trade(
    execution: ModuleType, daily_feed: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    def signal(history: pd.DataFrame, market: str, strategy: str) -> dict[str, Any]:
        return {
            "buy": {
                "cok_ucuz": strategy == "combo" and history.index[-1] == pd.Timestamp("2020-04-30"),
                "beles": False,
            },
            "sell": {"pahali": False},
        }

    portfolio = _fixed_run(execution, daily_feed, monkeypatch, signal=signal)
    assert portfolio.cash == 100000.0
    assert not portfolio.all_trades
    assert not portfolio.lots


def test_future_values_outside_end_date_cannot_change_results_or_invalidate_the_prefix(
    execution: ModuleType, daily_feed: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    baseline = _fixed_run(execution, daily_feed.loc[:"2020-04-30"].copy(), monkeypatch)
    poisoned = daily_feed.copy(deep=True)
    poisoned.loc["2020-05-01":, ["Open", "High", "Low", "Close", "Volume"]] = float("nan")
    result = _fixed_run(execution, poisoned, monkeypatch)
    assert baseline.all_trades
    assert _portfolio_state(result) == _portfolio_state(baseline)


@pytest.mark.parametrize(
    ("market", "as_of", "last_closed"),
    [
        ("CRYPTO", "2020-05-01T00:00:00Z", "2020-04-30"),
        ("CRYPTO", "2020-04-30T23:59:59Z", "2020-04-29"),
        ("BIST", "2020-04-30T21:00:00Z", "2020-04-30"),
        ("BIST", "2020-04-30T20:59:59Z", "2020-04-29"),
    ],
)
def test_as_of_requires_the_execution_day_to_be_fully_closed_in_its_market_calendar(
    execution: ModuleType,
    daily_feed: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
    market: str,
    as_of: str,
    last_closed: str,
) -> None:
    portfolio = _fixed_run(
        execution, daily_feed, monkeypatch, market=market, as_of=as_of, end="2020-05-10"
    )
    assert portfolio.all_trades[-1]["Tarih"] == pd.Timestamp(last_closed)
    assert max(row["Tarih"] for row in portfolio.equity_curve) <= pd.Timestamp(last_closed)


@pytest.mark.parametrize(
    ("as_of", "last_closed"),
    [("2015-03-29T20:59:59Z", "2015-03-28"), ("2015-03-29T21:00:00Z", "2015-03-29")],
)
def test_bist_historical_dst_uses_next_local_midnight_instead_of_twenty_four_hours(
    execution: ModuleType,
    daily_feed: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
    as_of: str,
    last_closed: str,
) -> None:
    frame = daily_feed.copy(deep=True)
    frame.index = pd.date_range("2014-11-01", periods=len(frame), freq="D")
    portfolio = _fixed_run(
        execution, frame, monkeypatch, start="2015-03-01", end="2015-04-01", as_of=as_of
    )
    assert portfolio.all_trades[-1]["Tarih"] == pd.Timestamp(last_closed)


@pytest.mark.parametrize("market", ["BIST", "CRYPTO"])
def test_aware_feed_dates_convert_to_market_midnight_without_changing_results(
    execution: ModuleType,
    daily_feed: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
    market: str,
) -> None:
    aware = daily_feed.copy(deep=True)
    zone = "Europe/Istanbul" if market == "BIST" else "UTC"
    aware.index = aware.index.tz_localize(zone).tz_convert("UTC")
    original = aware.copy(deep=True)
    baseline = _fixed_run(execution, daily_feed, monkeypatch, market=market)
    result = _fixed_run(execution, aware, monkeypatch, market=market)
    assert _portfolio_state(result) == _portfolio_state(baseline)
    pd.testing.assert_frame_equal(aware, original)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"start_date": "not-a-date"},
        {"end_date": "2020-04-30T12:00:00"},
        {"start_date": "2020-05-02", "end_date": "2020-05-01"},
        {"start_date": datetime(2020, 1, 1, tzinfo=UTC)},
        {"as_of": "2020-05-01"},
        {"as_of": datetime(2020, 5, 1)},
    ],
)
def test_invalid_bounds_and_naive_as_of_fail_before_any_provider_access(
    execution: ModuleType, monkeypatch: pytest.MonkeyPatch, kwargs: dict[str, Any]
) -> None:
    monkeypatch.setattr(execution, "get_bist_data_isyatirim_only", _no_provider)
    monkeypatch.setattr(execution, "get_crypto_data", _no_provider)
    with pytest.raises(ValueError):
        execution.BacktestEngine(**kwargs)


@pytest.mark.parametrize(
    "problem",
    [
        "non_datetime_index",
        "nat_date",
        "duplicate_date",
        "intraday_date",
        "duplicate_column",
        "missing_open",
        "nan_close",
        "infinite_high",
        "zero_price",
        "negative_volume",
        "high_below_close",
        "low_above_open",
    ],
)
def test_invalid_feed_fails_before_mutating_an_existing_portfolio(
    execution: ModuleType,
    daily_feed: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
    problem: str,
) -> None:
    frame = daily_feed.copy(deep=True)
    if problem == "non_datetime_index":
        frame.index = frame.index.astype(str)
    elif problem in {"nat_date", "duplicate_date", "intraday_date"}:
        dates = list(frame.index)
        dates[65] = {
            "nat_date": pd.NaT,
            "duplicate_date": dates[64],
            "intraday_date": dates[65] + pd.Timedelta(hours=1),
        }[problem]
        frame.index = pd.DatetimeIndex(dates)
    elif problem == "duplicate_column":
        frame = pd.concat([frame, frame[["Open"]]], axis=1)
    elif problem == "missing_open":
        frame = frame.drop(columns="Open")
    else:
        column, value = {
            "nan_close": ("Close", float("nan")),
            "infinite_high": ("High", float("inf")),
            "zero_price": ("Open", 0.0),
            "negative_volume": ("Volume", -1.0),
            "high_below_close": ("High", 1.0),
            "low_above_open": ("Low", 1000.0),
        }[problem]
        frame.iloc[65, frame.columns.get_loc(column)] = value
    monkeypatch.setattr(execution, "get_bist_data_isyatirim_only", _no_provider)
    engine = execution.BacktestEngine(
        start_date="2020-03-01", end_date="2020-04-30", as_of="2020-06-10T00:00:00Z"
    )
    portfolio = execution.Portfolio(100000.0, "BIST", 100.0)
    assert portfolio.buy("EXISTING", 100.0, datetime(2019, 1, 1), "BEFORE")
    before = _portfolio_state(portfolio)
    with pytest.raises(ValueError):
        engine.run_single_symbol("AAA", "BIST", portfolio, data=frame)
    assert _portfolio_state(portfolio) == before


def test_duplicate_dates_outside_the_end_date_are_still_a_structural_error(
    execution: ModuleType, daily_feed: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    frame = pd.concat([daily_feed, daily_feed.iloc[[-1]]])
    with pytest.raises(ValueError):
        _fixed_run(execution, frame, monkeypatch)


@pytest.mark.parametrize("quality", ["close_proxy", "aof_proxy", "synthetic_fallback", "mapped"])
def test_known_proxy_open_prices_cannot_be_used_for_next_open_execution(
    execution: ModuleType,
    daily_feed: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
    quality: str,
) -> None:
    frame = daily_feed.copy(deep=True)
    frame.attrs["open_quality"] = quality
    with pytest.raises(ValueError):
        _fixed_run(execution, frame, monkeypatch)


def test_explicit_ohlcv_without_provider_metadata_is_allowed(
    execution: ModuleType, daily_feed: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    frame = daily_feed.copy(deep=True)
    frame.attrs.clear()
    assert _fixed_run(execution, frame, monkeypatch).all_trades


@pytest.mark.parametrize("market", ["UNKNOWN", "CRYPTO"])
def test_unknown_or_mismatched_market_fails_without_portfolio_mutation(
    execution: ModuleType, daily_feed: pd.DataFrame, market: str
) -> None:
    engine = execution.BacktestEngine(as_of="2020-06-10T00:00:00Z")
    portfolio = execution.Portfolio(100000.0, "BIST", 100.0)
    before = _portfolio_state(portfolio)
    with pytest.raises(ValueError):
        engine.run_single_symbol("AAA", market, portfolio, data=daily_feed)
    assert _portfolio_state(portfolio) == before


def test_future_rows_do_not_satisfy_the_minimum_closed_history_requirement(
    execution: ModuleType, daily_feed: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    portfolio = _fixed_run(execution, daily_feed, monkeypatch, end="2020-04-28")
    assert portfolio.cash == 100000.0
    assert not portfolio.all_trades
    assert not portfolio.equity_curve


@pytest.mark.parametrize("market", ["BIST", "CRYPTO"])
def test_actual_resampler_keeps_developing_htf_snapshots_from_only_supplied_daily_rows(
    execution: ModuleType,
    daily_feed: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
    market: str,
) -> None:
    engine = execution.BacktestEngine(as_of="2020-06-10T00:00:00Z")
    monkeypatch.setattr(engine, "MIN_PERIODS", {code: 1 for code, _ in engine.TIMEFRAMES})
    seen: dict[str, pd.DataFrame] = {}

    def inspect_calculator(frame: pd.DataFrame, timeframe: str) -> dict[str, bool]:
        seen[timeframe] = frame.copy(deep=True)
        return {"buy": False, "sell": False}

    monkeypatch.setattr(execution, "calculate_combo_signal", inspect_calculator)
    source = daily_feed.loc[:"2020-05-05"].copy()
    engine.check_signals(source, market, "combo")
    assert set(seen) == {"1D", "W-FRI", "2W-FRI", "3W-FRI", "ME"}
    weekly = seen["W-FRI"]
    monthly = seen["ME"]
    # These are developing groups labelled by their first observed day, not closed bars.
    assert weekly.index[-1] == pd.Timestamp("2020-05-04")
    assert weekly.iloc[-1]["Volume"] == 2000.0
    assert monthly.index[-1] == pd.Timestamp("2020-05-01")
    assert monthly.iloc[-1]["Volume"] == 5000.0
    assert weekly.iloc[-1]["Close"] == source.iloc[-1]["Close"]
    assert monthly.iloc[-1]["Close"] == source.iloc[-1]["Close"]


def test_worker_fetches_once_and_propagates_end_date_and_as_of(
    execution: ModuleType, daily_feed: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    portfolios: list[Any] = []
    original_run = execution.BacktestEngine.run_single_symbol

    def provider(symbol: str, **kwargs: Any) -> pd.DataFrame:
        calls.append(symbol)
        return daily_feed.copy(deep=True)

    def capture_run(
        engine: Any, symbol: str, market: str, portfolio: Any, *args: Any, **kwargs: Any
    ) -> Any:
        portfolios.append(portfolio)
        return original_run(engine, symbol, market, portfolio, *args, **kwargs)

    monkeypatch.setattr(execution, "get_bist_data_isyatirim_only", provider)
    monkeypatch.setattr(execution, "get_crypto_data", _no_provider)
    monkeypatch.setattr(execution.BacktestEngine, "run_single_symbol", capture_run)
    monkeypatch.setattr(
        execution.BacktestEngine,
        "check_signals",
        lambda self, frame, market, strategy="combo": _buy_on_combo(frame, market, strategy),
    )
    result = execution._run_symbol_backtest(
        ("AAA", "BIST", "2020-03-01", 100.0, "2020-05-10", "2020-04-30T21:00:00Z")
    )
    assert result["success"] is True
    assert calls == ["AAA"]
    assert len(portfolios) == 1
    assert portfolios[0].all_trades[-1]["Tarih"] == pd.Timestamp("2020-04-30")
