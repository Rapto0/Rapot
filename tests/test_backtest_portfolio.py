"""Offline, hand-calculated shared-cash chronology and end-of-day valuation checks."""

import importlib
import sys
import warnings
from copy import deepcopy
from types import ModuleType, SimpleNamespace
from typing import Any

import pandas as pd
import pytest


@pytest.fixture
def backtest() -> ModuleType:
    with warnings.catch_warnings():
        return importlib.import_module("backtesting_system")


def _feed(marker: float, *, close: float = 100.0) -> pd.DataFrame:
    dates = pd.date_range("2020-01-01", periods=160)
    return pd.DataFrame(
        {"Open": 100.0, "High": 1000.0, "Low": 1.0, "Close": close, "Volume": marker},
        index=dates,
    )


def _zero_costs(backtest: ModuleType) -> Any:
    return backtest.TradingCosts(
        bist_commission=0.0,
        bist_slippage=0.0,
        crypto_commission=0.0,
        crypto_slippage=0.0,
    )


def _signals(plan: dict[tuple[float, str, str], tuple[str, ...]]) -> Any:
    def calculate(history: pd.DataFrame, market: str, strategy: str = "combo") -> dict[str, Any]:
        marker = float(history["Volume"].iloc[0])
        day = str(history.index[-1].date())
        actions = plan.get((marker, day, strategy), ())
        return {
            "buy": {"cok_ucuz": "buy" in actions, "beles": "beles" in actions},
            "sell": {"pahali": "sell" in actions},
        }

    return calculate


def _provider_runner(
    backtest: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    feeds: dict[str, pd.DataFrame],
    plan: dict[tuple[float, str, str], tuple[str, ...]],
) -> tuple[Any, list[str]]:
    class Progress:
        def __enter__(self) -> Any:
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def update(self, *args: Any) -> None:
            return None

        def set_postfix(self, *args: Any) -> None:
            return None

    calls: list[str] = []

    def provider(symbol: str, **kwargs: Any) -> pd.DataFrame:
        calls.append(symbol)
        return feeds[symbol].copy(deep=True)

    monkeypatch.setitem(sys.modules, "tqdm", SimpleNamespace(tqdm=lambda **kwargs: Progress()))
    monkeypatch.setattr(backtest, "get_bist_data_isyatirim_only", provider)
    monkeypatch.setattr(
        backtest, "get_crypto_data", lambda *args, **kwargs: pytest.fail("No crypto provider")
    )
    monkeypatch.setattr(backtest, "trading_costs", _zero_costs(backtest))
    engine = backtest.BacktestEngine(
        start_date="2020-03-02", end_date="2020-04-30", as_of="2020-06-10T00:00:00Z"
    )
    monkeypatch.setattr(engine, "check_signals", _signals(plan))
    return engine, calls


def test_shared_cash_cannot_spend_a_later_sale_in_an_earlier_symbol(
    backtest: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, second = _feed(1.0), _feed(2.0)
    first.loc["2020-03-10", "Open"] = 200.0
    engine, _ = _provider_runner(
        backtest,
        monkeypatch,
        {"AAA": first, "BBB": second},
        {
            (1.0, "2020-03-01", "combo"): ("buy",),
            (1.0, "2020-03-09", "combo"): ("sell",),
            (2.0, "2020-03-04", "combo"): ("buy",),
        },
    )
    portfolio = engine.run_backtest(["AAA", "BBB"], "BIST", 100.0, 100.0)
    assert [row["Sembol"] for row in portfolio.all_trades] == ["AAA", "AAA"]
    assert portfolio.cash == pytest.approx(200.0)
    assert not portfolio.lots


def test_shared_valuation_marks_all_symbols_at_their_latest_close(
    backtest: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine, _ = _provider_runner(
        backtest,
        monkeypatch,
        {"AAA": _feed(1.0, close=150.0), "BBB": _feed(2.0, close=110.0)},
        {
            (1.0, "2020-03-01", "combo"): ("buy",),
            (2.0, "2020-03-02", "combo"): ("buy",),
        },
    )
    portfolio = engine.run_backtest(["AAA", "BBB"], "BIST", 200.0, 100.0)
    assert portfolio.equity_curve[-1]["Toplam Değer"] == 260.0


def _no_provider(*args: Any, **kwargs: Any) -> None:
    pytest.fail("Supplied daily feeds must not use any provider")


def _engine(
    backtest: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    plan: dict[tuple[float, str, str], tuple[str, ...]] | None = None,
    **bounds: str,
) -> Any:
    monkeypatch.setattr(backtest, "get_bist_data_isyatirim_only", _no_provider)
    monkeypatch.setattr(backtest, "get_crypto_data", _no_provider)
    options = {
        "start_date": "2020-03-02",
        "end_date": "2020-04-30",
        "as_of": "2020-06-10T00:00:00Z",
        **bounds,
    }
    engine = backtest.BacktestEngine(**options)
    monkeypatch.setattr(engine, "check_signals", _signals(plan or {}))
    return engine


def _state(portfolio: Any) -> dict[str, Any]:
    return deepcopy(
        {
            "cash": portfolio.cash,
            "compensation": portfolio._cash_compensation,
            "lots": {
                symbol: [vars(lot) for lot in lots] for symbol, lots in portfolio.lots.items()
            },
            "trades": portfolio.all_trades,
            "performance": portfolio.symbol_performance,
            "equity": portfolio.equity_curve,
            "commission": portfolio.total_commission_paid,
            "slippage": portfolio.total_slippage_cost,
            "metadata": portfolio.backtest_metadata,
        }
    )


def _run(
    backtest: ModuleType,
    engine: Any,
    feeds: dict[str, pd.DataFrame],
    *,
    symbols: list[str] | None = None,
    initial_cash: float = 200.0,
    trade_amount: float = 100.0,
    costs: Any = None,
    market: str = "BIST",
) -> Any:
    return engine.run_backtest(
        list(feeds) if symbols is None else symbols,
        market,
        initial_cash,
        trade_amount,
        data_by_symbol=feeds,
        costs=_zero_costs(backtest) if costs is None else costs,
    )


def test_same_day_cash_priority_is_lexical_and_input_order_invariant(
    backtest: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = {
        (1.0, "2020-03-01", "combo"): ("buy",),
        (2.0, "2020-03-01", "combo"): ("buy",),
    }
    engine = _engine(backtest, monkeypatch, plan)
    feeds = {"BBB": _feed(2.0, close=900.0), "AAA": _feed(1.0, close=150.0)}
    feeds["AAA"].attrs["open_quality"] = "provider"
    originals = {symbol: frame.copy(deep=True) for symbol, frame in feeds.items()}
    first = _run(backtest, engine, feeds, initial_cash=100.0)
    reordered = {symbol: feeds[symbol].iloc[::-1].copy(deep=True) for symbol in ("AAA", "BBB")}
    second = _run(backtest, engine, reordered, initial_cash=100.0)

    assert [trade["Sembol"] for trade in first.all_trades] == ["AAA"]
    assert first.equity_curve[-1]["Toplam Değer"] == 150.0
    assert _state(first) == _state(second)
    assert first.backtest_metadata["processed_symbols"] == ["AAA", "BBB"]
    for symbol, frame in feeds.items():
        pd.testing.assert_frame_equal(frame, originals[symbol])
        assert frame.attrs == originals[symbol].attrs


def test_same_day_sales_are_not_globally_moved_before_lexical_buys(
    backtest: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = _engine(
        backtest,
        monkeypatch,
        {
            (2.0, "2020-03-01", "combo"): ("buy",),
            (1.0, "2020-03-02", "combo"): ("buy",),
            (2.0, "2020-03-02", "combo"): ("sell",),
        },
    )
    portfolio = _run(backtest, engine, {"ZZZ": _feed(2.0), "AAA": _feed(1.0)}, initial_cash=100.0)
    assert [(row["Sembol"], row["İşlem"]) for row in portfolio.all_trades] == [
        ("ZZZ", "ALIM"),
        ("ZZZ", "SATIM"),
    ]
    assert portfolio.cash == 100.0
    assert not portfolio.lots


def test_strategy_and_action_order_preserves_existing_fifo_contract(
    backtest: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = _engine(
        backtest,
        monkeypatch,
        {
            (1.0, "2020-03-01", strategy): ("buy", "beles", "sell")
            for strategy in ("combo", "hunter")
        },
    )
    portfolio = _run(backtest, engine, {"AAA": _feed(1.0)}, initial_cash=1000.0)
    assert [row["Sinyal"] for row in portfolio.all_trades] == [
        "COMBO: ÇOK UCUZ",
        "COMBO: BELEŞ",
        "COMBO: PAHALI",
        "HUNTER: ÇOK UCUZ",
        "HUNTER: BELEŞ",
        "HUNTER: PAHALI",
    ]
    assert [row["İşlem"] for row in portfolio.all_trades] == ["ALIM", "ALIM", "SATIM"] * 2
    assert [lot.signal for lot in portfolio.lots["AAA"]] == [
        "HUNTER: ÇOK UCUZ",
        "HUNTER: BELEŞ",
    ]
    assert portfolio.cash == 800.0


def test_daily_equity_carries_observed_close_and_never_a_future_or_entry_price(
    backtest: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _feed(1.0, close=150.0).drop(pd.Timestamp("2020-03-03"))
    first.loc["2020-03-04":, "Close"] = 900.0
    first = first.loc[:"2020-05-01"]
    second = _feed(2.0, close=110.0)
    engine = _engine(
        backtest,
        monkeypatch,
        {
            (1.0, "2020-03-01", "combo"): ("buy",),
            (2.0, "2020-03-02", "combo"): ("buy",),
        },
        end_date="2020-05-05",
    )
    portfolio = _run(backtest, engine, {"BBB": second, "AAA": first})
    rows = {row["Tarih"]: row for row in portfolio.equity_curve}
    assert list(rows) == list(pd.date_range("2020-03-02", "2020-05-05"))
    assert len(rows) == len(portfolio.equity_curve), "One complete EOD mark per union day"
    gap = rows[pd.Timestamp("2020-03-03")]
    assert gap["Toplam Değer"] == 260.0
    assert gap["Fiyat Tarihleri"] == {
        "AAA": pd.Timestamp("2020-03-02"),
        "BBB": pd.Timestamp("2020-03-03"),
    }
    assert gap["Eski Fiyatlı Semboller"] == ["AAA"]
    assert rows[pd.Timestamp("2020-03-04")]["Toplam Değer"] == 1010.0
    assert rows[pd.Timestamp("2020-03-04")]["Eski Fiyatlı Semboller"] == []
    final = portfolio.equity_curve[-1]
    assert final["Toplam Değer"] == portfolio.get_portfolio_value({"AAA": 900.0, "BBB": 110.0})
    assert final["Fiyat Tarihleri"]["AAA"] == pd.Timestamp("2020-05-01")
    assert final["Eski Fiyatlı Semboller"] == ["AAA"]


def test_disjoint_calendars_execute_only_on_next_observed_symbol_day(
    backtest: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, second = _feed(1.0), _feed(2.0)
    first.index = pd.date_range("2019-08-01", periods=160, freq="2D")
    second.index = pd.date_range("2019-08-02", periods=160, freq="2D")
    first.loc["2020-04-01", "Open"] = 125.0
    second.loc["2020-04-02", "Open"] = 200.0
    engine = _engine(
        backtest,
        monkeypatch,
        {
            (1.0, "2020-03-30", "combo"): ("buy",),
            (2.0, "2020-03-31", "combo"): ("buy",),
        },
        start_date="2020-04-01",
        end_date="2020-05-01",
        as_of="2020-07-01T00:00:00Z",
    )
    portfolio = _run(backtest, engine, {"BBB": second, "AAA": first})
    assert [(row["Tarih"], row["Sinyal Tarihi"], row["Fiyat"]) for row in portfolio.all_trades] == [
        (pd.Timestamp("2020-04-01"), pd.Timestamp("2020-03-30"), 125.0),
        (pd.Timestamp("2020-04-02"), pd.Timestamp("2020-03-31"), 200.0),
    ]
    union = sorted(
        set(first.loc["2020-04-01":"2020-05-01"].index)
        | set(second.loc["2020-04-01":"2020-05-01"].index)
    )
    assert [row["Tarih"] for row in portfolio.equity_curve] == union
    assert portfolio.equity_curve[-1]["Toplam Değer"] == 130.0


@pytest.mark.parametrize(
    "market,cutoff", [("BIST", "2020-05-02T20:59:59Z"), ("CRYPTO", "2020-05-02T23:59:59Z")]
)
def test_shared_cutoff_start_end_and_signal_prefix_are_all_respected(
    backtest: ModuleType, monkeypatch: pytest.MonkeyPatch, market: str, cutoff: str
) -> None:
    engine = _engine(
        backtest,
        monkeypatch,
        start_date="2020-04-30",
        end_date="2020-05-03",
        as_of=cutoff,
    )
    seen: list[tuple[float, pd.Timestamp]] = []

    def spy(history: pd.DataFrame, selected_market: str, strategy: str = "combo") -> Any:
        assert selected_market == market
        seen.append((float(history["Volume"].iloc[0]), history.index[-1]))
        # Mutation by one strategy must not leak into the next strategy/symbol/feed.
        assert (history["Open"] == 100.0).all()
        history.loc[:, "Open"] = 999.0
        return {"buy": {"cok_ucuz": strategy == "combo", "beles": False}, "sell": {"pahali": False}}

    monkeypatch.setattr(engine, "check_signals", spy)
    portfolio = _run(
        backtest, engine, {"AAA": _feed(1.0), "BBB": _feed(2.0)}, initial_cash=1000.0, market=market
    )
    assert [row["Tarih"] for row in portfolio.equity_curve] == list(
        pd.date_range("2020-04-30", "2020-05-01")
    )
    assert [row["Tarih"] for row in portfolio.all_trades] == [pd.Timestamp("2020-04-30")] * 2 + [
        pd.Timestamp("2020-05-01")
    ] * 2
    assert seen == [
        (marker, day)
        for day in pd.date_range("2020-04-29", "2020-04-30")
        for marker in (1.0, 1.0, 2.0, 2.0)
    ]
    assert all(row["Yürütme Modeli"] == "next_open" for row in portfolio.all_trades)


def test_earliest_execution_keeps_61_row_warmup_and_120_admitted_row_gate(
    backtest: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = _engine(backtest, monkeypatch, start_date="2020-01-01", end_date="2020-04-29")
    portfolio = _run(backtest, engine, {"AAA": _feed(1.0)})
    assert portfolio.equity_curve[0]["Tarih"] == pd.Timestamp("2020-03-02")
    assert portfolio.equity_curve[-1]["Tarih"] == pd.Timestamp("2020-04-29")
    too_short = _engine(backtest, monkeypatch, start_date="2020-01-01", end_date="2020-04-28")
    skipped = _run(backtest, too_short, {"AAA": _feed(1.0)})
    assert skipped.backtest_metadata["processed_symbols"] == []
    assert skipped.backtest_metadata["skipped_symbols"]["AAA"]
    assert not skipped.all_trades and not skipped.equity_curve


@pytest.mark.parametrize("symbols", [["AAA", "AAA"], [""], [" "], [" AAA"], ["AAA "], [3], [None]])
def test_invalid_symbol_collection_is_rejected_before_provider_or_trade(
    backtest: ModuleType, monkeypatch: pytest.MonkeyPatch, symbols: list[Any]
) -> None:
    engine = _engine(backtest, monkeypatch)
    monkeypatch.setattr(
        backtest.Portfolio,
        "buy",
        lambda *args, **kwargs: pytest.fail("Invalid symbols reached execution"),
    )
    with pytest.raises(ValueError):
        engine.run_backtest(symbols, "BIST", 1000.0, 100.0)


@pytest.mark.parametrize("keys", [[], ["AAA", "BBB"], ["BBB"]])
def test_supplied_mapping_requires_exact_symbol_keys_before_execution(
    backtest: ModuleType, monkeypatch: pytest.MonkeyPatch, keys: list[str]
) -> None:
    engine = _engine(backtest, monkeypatch)
    monkeypatch.setattr(
        backtest.Portfolio,
        "buy",
        lambda *args, **kwargs: pytest.fail("Invalid mapping reached execution"),
    )
    with pytest.raises(ValueError):
        _run(backtest, engine, {key: _feed(1.0) for key in keys}, symbols=["AAA"])


@pytest.mark.parametrize(
    "invalid", ["nan_close", "duplicate_day", "proxy_open", "missing_column", "not_frame"]
)
def test_all_symbol_feeds_are_validated_before_any_signal_or_trade(
    backtest: ModuleType, monkeypatch: pytest.MonkeyPatch, invalid: str
) -> None:
    broken: Any = _feed(2.0)
    if invalid == "nan_close":
        broken.loc["2020-04-20", "Close"] = float("nan")
    elif invalid == "duplicate_day":
        broken = pd.concat([broken, broken.iloc[:1]])
    elif invalid == "proxy_open":
        broken.attrs["open_quality"] = "close_proxy"
    elif invalid == "missing_column":
        broken = broken.drop(columns="Open")
    else:
        broken = {"Close": [100.0]}
    engine = _engine(backtest, monkeypatch, {(1.0, "2020-03-01", "combo"): ("buy",)})
    monkeypatch.setattr(
        engine,
        "check_signals",
        lambda *args, **kwargs: pytest.fail("Malformed later feed allowed partial execution"),
    )
    monkeypatch.setattr(
        backtest.Portfolio,
        "buy",
        lambda *args, **kwargs: pytest.fail("Malformed later feed allowed mutation"),
    )
    with pytest.raises(ValueError):
        _run(backtest, engine, {"AAA": _feed(1.0), "BBB": broken})


def test_provider_exception_does_not_return_a_partially_traded_portfolio(
    backtest: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = _engine(backtest, monkeypatch)
    calls: list[str] = []

    def provider(symbol: str, **kwargs: Any) -> pd.DataFrame:
        calls.append(symbol)
        if symbol == "BBB":
            raise RuntimeError("Synthetic unavailable feed")
        return _feed(1.0)

    monkeypatch.setattr(backtest, "get_bist_data_isyatirim_only", provider)
    monkeypatch.setattr(
        engine,
        "check_signals",
        lambda *args, **kwargs: pytest.fail("Provider failure allowed partial execution"),
    )
    with pytest.raises(RuntimeError, match="Synthetic unavailable feed"):
        engine.run_backtest(["AAA", "BBB"], "BIST", 200.0, 100.0)
    assert calls == ["AAA", "BBB"]


@pytest.mark.parametrize("market", ["BIST", "CRYPTO"])
def test_each_provider_is_read_once_and_skips_are_reported(
    backtest: ModuleType, monkeypatch: pytest.MonkeyPatch, market: str
) -> None:
    engine = _engine(backtest, monkeypatch)
    calls: list[str] = []

    def provider(symbol: str, **kwargs: Any) -> pd.DataFrame | None:
        calls.append(symbol)
        if symbol == "MISSING":
            return None
        if symbol == "SHORT":
            return _feed(2.0).iloc[:119]
        return _feed(1.0)

    monkeypatch.setattr(
        backtest,
        "get_bist_data_isyatirim_only" if market == "BIST" else "get_crypto_data",
        provider,
    )
    portfolio = engine.run_backtest(["SHORT", "AAA", "MISSING"], market, 200.0, 100.0)
    assert sorted(calls) == ["AAA", "MISSING", "SHORT"]
    assert portfolio.backtest_metadata["processed_symbols"] == ["AAA"]
    assert set(portfolio.backtest_metadata["skipped_symbols"]) == {"SHORT", "MISSING"}
    assert all(
        isinstance(reason, str) and reason
        for reason in portfolio.backtest_metadata["skipped_symbols"].values()
    )
    assert portfolio.equity_curve[-1]["Toplam Değer"] == 200.0


def test_no_execution_range_returns_cash_and_explicit_skip_without_equity(
    backtest: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = _engine(
        backtest,
        monkeypatch,
        start_date="2021-01-01",
        end_date="2021-02-01",
        as_of="2021-03-01T00:00:00Z",
    )
    portfolio = _run(backtest, engine, {"AAA": _feed(1.0)})
    assert portfolio.backtest_metadata["processed_symbols"] == []
    assert portfolio.backtest_metadata["skipped_symbols"]["AAA"]
    assert not portfolio.all_trades and not portfolio.equity_curve and not portfolio.lots
    assert portfolio.cash == 200.0


@pytest.mark.parametrize(
    "prices",
    [{}, {"BBB": 100.0}, {"AAA": 0.0}, {"AAA": -1.0}, {"AAA": float("nan")}, {"AAA": float("inf")}],
)
def test_incomplete_or_invalid_held_marks_raise_without_portfolio_mutation(
    backtest: ModuleType, prices: dict[str, float]
) -> None:
    portfolio = backtest.Portfolio(200.0, "BIST", 100.0, costs=_zero_costs(backtest))
    assert portfolio.buy("AAA", 100.0, pd.Timestamp("2020-03-02"), "fixture")
    before = _state(portfolio)
    with pytest.raises(ValueError):
        portfolio.get_portfolio_value(prices)
    assert _state(portfolio) == before
    with pytest.raises(ValueError):
        portfolio.record_equity(pd.Timestamp("2020-03-03"), prices)
    assert _state(portfolio) == before


@pytest.mark.parametrize(
    "mark_date", [None, pd.NaT, pd.Timestamp("2020-03-04"), pd.Timestamp("2020-03-03", tz="UTC")]
)
def test_invalid_held_price_date_cannot_append_an_equity_row(
    backtest: ModuleType, mark_date: Any
) -> None:
    portfolio = backtest.Portfolio(200.0, "BIST", 100.0, costs=_zero_costs(backtest))
    assert portfolio.buy("AAA", 100.0, pd.Timestamp("2020-03-02"), "fixture")
    before = _state(portfolio)
    with pytest.raises(ValueError):
        portfolio.record_equity(
            pd.Timestamp("2020-03-03"), {"AAA": 150.0}, price_dates={"AAA": mark_date}
        )
    assert _state(portfolio) == before


def test_valuation_uses_all_fifo_lots_and_only_held_price_dates(
    backtest: ModuleType,
) -> None:
    portfolio = backtest.Portfolio(300.0, "BIST", 100.0, costs=_zero_costs(backtest))
    assert portfolio.get_portfolio_value({}) == 300.0
    assert portfolio.buy("AAA", 100.0, pd.Timestamp("2020-03-02"), "first")
    assert portfolio.buy("AAA", 200.0, pd.Timestamp("2020-03-03"), "second")
    portfolio.record_equity(
        pd.Timestamp("2020-03-04"),
        {"AAA": 150.0},
        price_dates={"AAA": pd.Timestamp("2020-03-03"), "UNHELD": pd.Timestamp("2030-01-01")},
    )
    row = portfolio.equity_curve[-1]
    assert row["Toplam Değer"] == 325.0
    assert row["Fiyat Tarihleri"] == {"AAA": pd.Timestamp("2020-03-03")}
    assert row["Eski Fiyatlı Semboller"] == ["AAA"]


def test_shared_cash_and_all_symbol_marks_match_independent_fee_oracle(
    backtest: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = _engine(
        backtest,
        monkeypatch,
        {
            (1.0, "2020-03-01", "combo"): ("buy",),
            (2.0, "2020-03-01", "combo"): ("buy",),
            (1.0, "2020-03-02", "combo"): ("sell",),
        },
    )
    first = _feed(1.0)
    first.loc["2020-03-03", "Open"] = 110.0
    costs = backtest.TradingCosts(bist_commission=0.01, bist_slippage=0.02)
    portfolio = _run(
        backtest,
        engine,
        {"AAA": first, "BBB": _feed(2.0, close=150.0)},
        initial_cash=2060.0,
        trade_amount=1030.0,
        costs=costs,
    )
    assert portfolio.cash == pytest.approx(1067.0)
    assert portfolio.total_commission_paid == pytest.approx(31.0)
    assert portfolio.total_slippage_cost == pytest.approx(62.0)
    assert portfolio.symbol_performance["AAA"]["Toplam Kar/Zarar"] == pytest.approx(37.0)
    assert portfolio.lots["BBB"][0].shares == pytest.approx(10.0)
    open_basis = sum(lot.invested for lots in portfolio.lots.values() for lot in lots)
    assert portfolio.cash + open_basis == pytest.approx(2060.0 + 37.0)
    assert portfolio.equity_curve[-1]["Toplam Değer"] == 2567.0
    assert portfolio.symbol_performance["AAA"]["Toplam Alım"] == 1


def test_one_symbol_shared_execution_matches_single_symbol_trades_and_final_value(
    backtest: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = _engine(
        backtest,
        monkeypatch,
        {
            (1.0, "2020-03-01", "combo"): ("buy",),
            (1.0, "2020-03-04", "hunter"): ("buy",),
            (1.0, "2020-03-09", "combo"): ("sell",),
        },
    )
    frame = _feed(1.0, close=150.0)
    frame.loc["2020-03-10", "Open"] = 120.0
    costs = backtest.TradingCosts(bist_commission=0.01, bist_slippage=0.02)
    single = backtest.Portfolio(1000.0, "BIST", 100.0, costs=costs)
    assert engine.run_single_symbol("AAA", "BIST", single, data=frame)
    shared = _run(backtest, engine, {"AAA": frame}, initial_cash=1000.0, costs=costs)
    assert shared.all_trades == single.all_trades
    assert shared.cash == single.cash
    assert shared.total_transaction_cost == single.total_transaction_cost
    assert shared.equity_curve[-1]["Toplam Değer"] == single.equity_curve[-1]["Toplam Değer"]
    assert len(single.equity_curve) < len(shared.equity_curve)


@pytest.mark.parametrize("supplied_feed", [False, True])
def test_single_symbol_foreign_holdings_are_rejected_before_provider_or_mutation(
    backtest: ModuleType, monkeypatch: pytest.MonkeyPatch, supplied_feed: bool
) -> None:
    engine = _engine(backtest, monkeypatch, {(1.0, "2020-03-01", "combo"): ("buy",)})
    portfolio = backtest.Portfolio(300.0, "BIST", 100.0, costs=_zero_costs(backtest))
    assert portfolio.buy("FOREIGN", 100.0, pd.Timestamp("2020-02-01"), "fixture")
    before = _state(portfolio)
    with pytest.raises(ValueError):
        engine.run_single_symbol(
            "AAA", "BIST", portfolio, data=_feed(1.0) if supplied_feed else None
        )
    assert _state(portfolio) == before
