"""Offline window coverage and honest buy-and-hold analysis contracts."""

import importlib
import math
import warnings
from fractions import Fraction
from types import ModuleType
from typing import Any

import pandas as pd
import pytest


@pytest.fixture
def backtest() -> ModuleType:
    with warnings.catch_warnings():
        return importlib.import_module("backtesting_system")


def _feed(rows: int = 240) -> pd.DataFrame:
    return pd.DataFrame(
        {"Open": 100.0, "High": 300.0, "Low": 50.0, "Close": 200.0, "Volume": 1000.0},
        index=pd.date_range("2020-01-01", periods=rows),
    )


def _no_provider(*args: Any, **kwargs: Any) -> None:
    pytest.fail("Fixed window analysis must not access a provider")


@pytest.fixture(autouse=True)
def no_provider(backtest: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(backtest, "get_bist_data_isyatirim_only", _no_provider)
    monkeypatch.setattr(backtest, "get_crypto_data", _no_provider)
    monkeypatch.setattr(
        backtest.BacktestEngine,
        "check_signals",
        lambda *args, **kwargs: pytest.fail("Buy-and-hold must not claim to evaluate a strategy"),
    )


def _analysis(backtest: ModuleType, **kwargs: Any) -> Any:
    zero_costs = backtest.TradingCosts(
        bist_commission=0.0, bist_slippage=0.0, crypto_commission=0.0, crypto_slippage=0.0
    )
    return backtest.RollingBuyAndHoldAnalysis(
        **{"as_of": "2025-01-01T00:00:00Z", "costs": zero_costs, **kwargs}
    )


def test_legacy_windows_cover_the_entire_remaining_period(backtest: ModuleType) -> None:
    frame = _feed(1000)
    with pytest.warns(FutureWarning, match="legacy name"):
        analysis = backtest.WalkForwardAnalysis(
            n_splits=5, train_ratio=0.7, as_of="2025-01-01T00:00:00Z"
        )
    windows = analysis.split_data(frame)
    observed = [stamp for _, test in windows for stamp in test.index]
    assert observed == list(frame.index[700:])


def test_legacy_strategy_parameter_is_not_reported_as_an_evaluated_strategy(
    backtest: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(backtest, "get_crypto_data", lambda *args, **kwargs: _feed())
    with pytest.warns(FutureWarning, match="legacy name"):
        analysis = backtest.WalkForwardAnalysis(
            n_splits=5, train_ratio=0.7, as_of="2025-01-01T00:00:00Z"
        )
    with pytest.warns(FutureWarning, match="strategy is ignored"):
        result = analysis.run_walk_forward("BTCUSDT", "CRYPTO", strategy="hunter")
    assert result["strategy"] == "buy_and_hold"
    assert result["ignored_strategy"] == "hunter"
    assert result["strategy_evaluated"] is False
    assert result["optimization_performed"] is False
    assert result["warning"] and result["legacy_api"] == "run_walk_forward"
    assert result["windows"][0]["train_start"] == result["windows"][0]["history_start"]


def test_uneven_partition_covers_every_remaining_row_once_and_expands_only_past_context(
    backtest: ModuleType,
) -> None:
    frame = _feed(11)
    analysis = _analysis(backtest, n_splits=3, history_ratio=0.3)
    splits = analysis.split_data(frame, "CRYPTO")
    assert [len(window) for _, window in splits] == [3, 3, 2]
    assert [len(context) for context, _ in splits] == [3, 6, 9]
    assert [day for _, window in splits for day in window.index] == list(frame.index[3:])
    for context, window in splits:
        assert context.index[-1] < window.index[0]
        assert context.index[0] == frame.index[0]


def test_returns_use_first_real_open_and_independent_window_arithmetic_statistics(
    backtest: ModuleType,
) -> None:
    frame = _feed(11)
    frame.loc[frame.index[[3, 6, 9]], "Open"] = [100.0, 200.0, 50.0]
    frame.loc[frame.index[[5, 8, 10]], "Close"] = [110.0, 180.0, 75.0]
    analysis = _analysis(backtest, n_splits=3, history_ratio=0.3)
    result = analysis.run("AAA", "BIST", data=frame)
    returns = [10.0, -10.0, 50.0]
    mean = 50.0 / 3.0
    assert [window["net_return"] for window in result["windows"]] == pytest.approx(returns)
    assert result["avg_return"] == pytest.approx(mean)
    assert result["std_return"] == pytest.approx(
        math.sqrt(sum((value - mean) ** 2 for value in returns) / 3)
    )
    assert result["min_return"] == pytest.approx(-10.0)
    assert result["max_return"] == pytest.approx(50.0)
    assert result["model"] == "rolling_buy_and_hold"
    assert result["history_usage"] == "context_only_no_training"
    assert result["aggregation"] == "arithmetic_statistics_of_independent_window_returns"
    assert result["strategy_evaluated"] is False and result["optimization_performed"] is False


@pytest.mark.parametrize("market", ["BIST", "CRYPTO"])
def test_round_trip_costs_match_fraction_oracle(backtest: ModuleType, market: str) -> None:
    frame = _feed(4)
    frame.loc[frame.index[-1], "Close"] = 110.0
    costs = backtest.TradingCosts(
        bist_commission=0.01, bist_slippage=0.02, crypto_commission=0.01, crypto_slippage=0.02
    )
    result = _analysis(backtest, n_splits=1, history_ratio=0.5, costs=costs).run(
        "AAA", market, data=frame
    )
    window = result["windows"][0]
    final_value = Fraction(110, 100) * Fraction(97, 103)
    assert window["final_value"] == pytest.approx(float(final_value))
    assert window["net_return"] == pytest.approx(float((final_value - 1) * 100))
    assert window["gross_return"] == pytest.approx(10.0)
    assert window["commission_paid"] == pytest.approx(float(Fraction(21, 1030)))
    assert window["slippage_cost"] == pytest.approx(float(Fraction(21, 515)))
    assert window["test_return"] == window["net_return"]
    assert result["initial_capital_per_window"] == 1.0


def test_one_day_holding_window_is_valid_without_indicator_warmup(backtest: ModuleType) -> None:
    result = _analysis(backtest, n_splits=1, history_ratio=0.5).run("AAA", "BIST", data=_feed(2))
    assert result["n_windows"] == 1
    window = result["windows"][0]
    assert window["test_start"] == window["test_end"] == pd.Timestamp("2020-01-02")
    assert window["net_return"] == 100.0
    assert result["std_return"] == 0.0


@pytest.mark.parametrize("splits", [0, -1, True, 1.5, "5"])
def test_invalid_split_count_is_rejected(backtest: ModuleType, splits: Any) -> None:
    with pytest.raises(ValueError, match="n_splits"):
        _analysis(backtest, n_splits=splits)


@pytest.mark.parametrize("ratio", [0.0, 1.0, -0.1, True, float("nan"), float("inf"), "0.7"])
def test_invalid_history_ratio_is_rejected(backtest: ModuleType, ratio: Any) -> None:
    with pytest.raises(ValueError, match="history_ratio"):
        _analysis(backtest, history_ratio=ratio)


@pytest.mark.parametrize("rows,splits,ratio", [(0, 1, 0.5), (1, 1, 0.5), (4, 3, 0.5), (4, 1, 0.1)])
def test_insufficient_rows_raise_instead_of_zero_return(
    backtest: ModuleType, rows: int, splits: int, ratio: float
) -> None:
    analysis = _analysis(backtest, n_splits=splits, history_ratio=ratio)
    with pytest.raises(ValueError, match="one history row"):
        analysis.run("AAA", "BIST", data=_feed(rows))
    assert analysis.results == []


@pytest.mark.parametrize(
    "market,cutoff,last_day",
    [
        ("BIST", "2020-01-09T20:59:59Z", "2020-01-08"),
        ("BIST", "2020-01-09T21:00:00Z", "2020-01-09"),
        ("CRYPTO", "2020-01-09T23:59:59Z", "2020-01-08"),
        ("CRYPTO", "2020-01-10T00:00:00Z", "2020-01-09"),
    ],
)
def test_start_end_and_conservative_market_closure_boundaries(
    backtest: ModuleType, market: str, cutoff: str, last_day: str
) -> None:
    analysis = _analysis(
        backtest,
        n_splits=2,
        history_ratio=0.5,
        start_date="2020-01-04",
        end_date="2020-01-09",
        as_of=cutoff,
    )
    result = analysis.run("AAA", market, data=_feed(30))
    assert result["windows"][0]["history_start"] == pd.Timestamp("2020-01-04")
    assert result["windows"][-1]["test_end"] == pd.Timestamp(last_day)
    assert result["as_of"] == pd.Timestamp(cutoff)
    assert all(window["test_end"] <= pd.Timestamp("2020-01-09") for window in result["windows"])


def test_end_date_excludes_future_outliers_and_inputs_are_not_mutated(backtest: ModuleType) -> None:
    frame = _feed(15)
    frame.attrs["open_quality"] = "provider"
    original = frame.copy(deep=True)
    analysis = _analysis(backtest, n_splits=2, history_ratio=0.5, end_date="2020-01-10")
    result = analysis.run("AAA", "BIST", data=frame)
    changed = frame.copy(deep=True)
    changed.loc["2020-01-11":, ["High", "Close"]] = 1e12
    assert analysis.run("AAA", "BIST", data=changed.iloc[::-1]) == result
    pd.testing.assert_frame_equal(frame, original)
    assert frame.attrs == original.attrs


def test_later_window_prices_cannot_change_an_earlier_window_return(backtest: ModuleType) -> None:
    frame = _feed(12)
    analysis = _analysis(backtest, n_splits=3, history_ratio=0.5)
    baseline = analysis.run("AAA", "BIST", data=frame)
    frame.loc["2020-01-09":, ["Open", "High", "Low", "Close"]] *= 3
    changed = analysis.run("AAA", "BIST", data=frame)
    assert changed["windows"][0] == baseline["windows"][0]


@pytest.mark.parametrize("market", ["BIST", "CRYPTO"])
def test_provider_is_read_once_with_the_same_validated_snapshot(
    backtest: ModuleType, monkeypatch: pytest.MonkeyPatch, market: str
) -> None:
    calls: list[str] = []

    def provider(symbol: str, **kwargs: Any) -> pd.DataFrame:
        calls.append(symbol)
        return _feed(12)

    monkeypatch.setattr(
        backtest,
        "get_bist_data_isyatirim_only" if market == "BIST" else "get_crypto_data",
        provider,
    )
    result = _analysis(backtest, n_splits=3, history_ratio=0.5).run("AAA", market)
    assert calls == ["AAA"] and result["n_windows"] == 3


@pytest.mark.parametrize(
    "failure", ["none", "exception", "bad_symbol", "bad_market", "proxy", "nan", "duplicate"]
)
def test_failed_new_run_clears_previous_results_and_does_not_hide_the_error(
    backtest: ModuleType, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    analysis = _analysis(backtest, n_splits=2, history_ratio=0.5)
    analysis.run("AAA", "BIST", data=_feed(12))
    assert analysis.results
    frame = _feed(12)
    symbol, market = "AAA", "BIST"
    error = ValueError
    if failure == "none":
        monkeypatch.setattr(backtest, "get_bist_data_isyatirim_only", lambda *args, **kwargs: None)
        frame = None
    elif failure == "exception":

        def fail(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("Synthetic provider failure")

        monkeypatch.setattr(backtest, "get_bist_data_isyatirim_only", fail)
        frame, error = None, RuntimeError
    elif failure == "bad_symbol":
        symbol = " AAA"
    elif failure == "bad_market":
        market = "UNKNOWN"
    elif failure == "proxy":
        frame.attrs["open_quality"] = "aof_proxy"
    elif failure == "nan":
        frame.loc[frame.index[-1], "Close"] = float("nan")
    else:
        frame = pd.concat([frame, frame.iloc[:1]])
    with pytest.raises(error):
        analysis.run(symbol, market, data=frame)
    assert analysis.results == []


def test_legacy_and_canonical_calls_agree_and_the_legacy_ratio_alias_is_honest(
    backtest: ModuleType,
) -> None:
    options = {"n_splits": 2, "as_of": "2025-01-01T00:00:00Z"}
    canonical = backtest.RollingBuyAndHoldAnalysis(history_ratio=0.5, **options)
    with pytest.warns(FutureWarning, match="legacy name"):
        legacy = backtest.WalkForwardAnalysis(train_ratio=0.7, **options)
    legacy.train_ratio = 0.5
    with pytest.warns(FutureWarning, match="strategy is ignored"):
        old_result = legacy.run_walk_forward("AAA", "BIST", "combo", data=_feed(12))
    result = canonical.run("AAA", "BIST", data=_feed(12))
    assert old_result["avg_return"] == result["avg_return"]
    assert legacy.history_ratio == 0.5
    assert old_result["ignored_strategy"] == "combo"
    assert all(window["train_end"] == window["history_end"] for window in old_result["windows"])


def test_unrepresentable_price_ratio_raises_and_leaves_no_partial_results(
    backtest: ModuleType,
) -> None:
    frame = _feed(4)
    frame.loc[frame.index[-1], ["Open", "Low"]] = 1e-308
    analysis = _analysis(backtest, n_splits=2, history_ratio=0.5)
    with pytest.raises(ValueError, match="overflow"):
        analysis.run("AAA", "BIST", data=frame)
    assert analysis.results == []
