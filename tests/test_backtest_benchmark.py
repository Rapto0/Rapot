"""Benchmark returns use the same marked portfolio period, never missing-as-zero."""

import importlib

import pandas as pd
import pytest


@pytest.fixture
def bt():
    return importlib.import_module("backtesting_system")


def feed():
    return pd.DataFrame(
        {"Open": [10.0, 15.0], "High": 30.0, "Low": 1.0, "Close": [15.0, 20.0], "Volume": 100.0},
        index=pd.date_range("2020-01-01", periods=2),
    )


def portfolio(bt, market="CRYPTO"):
    costs = bt.TradingCosts(0.0, 0.0, 0.0, 0.0)
    result = bt.Portfolio(100.0, market, 100.0, costs=costs)
    dates = feed().index
    result.buy("AAA", 10.0, dates[0], "BUY")
    result.record_equity(dates[0], {"AAA": 15.0})
    result.record_equity(dates[1], {"AAA": 20.0})
    result.backtest_metadata = {
        "comparison_start": dates[0],
        "comparison_end": dates[1],
        "comparison_initial_value": 100.0,
    }
    return result


def test_benchmark_includes_open_position_return(bt, monkeypatch):
    monkeypatch.setattr(bt, "get_crypto_data", lambda *a, **k: feed())
    result = bt.BenchmarkComparison("2020-01-01", "2020-01-02").compare(portfolio(bt), "CRYPTO")
    assert result["portfolio_return"] == pytest.approx(100.0)
    assert result["benchmark_return"] == pytest.approx(100.0)
    assert result["alpha"] == pytest.approx(0.0)


def test_disabled_benchmark_is_unavailable_not_zero(bt):
    result = bt.BenchmarkComparison("2020-01-01", "2020-01-02").compare(
        portfolio(bt, "BIST"), "BIST"
    )
    assert result["benchmark_return"] is None
    assert result["alpha"] is None


def test_supplied_benchmark_never_fetches_and_is_copied(bt, monkeypatch):
    monkeypatch.setattr(bt, "get_crypto_data", lambda *a, **k: pytest.fail("provider"))
    frame = feed()
    original = frame.copy(deep=True)
    comparison = bt.BenchmarkComparison("2020-01-01", as_of="2020-01-03T00:00:00Z")
    result = comparison.compare(portfolio(bt), "CRYPTO", data=frame)
    assert result["status"] == "available"
    assert result["benchmark_symbol"] == "supplied:CRYPTO"
    pd.testing.assert_frame_equal(frame, original)
    frame.iloc[0, 0] = 20.0
    assert comparison.benchmark_data["CRYPTO"].iloc[0]["Open"] == 10.0


def test_marked_benchmark_pays_entry_cost_without_invented_exit(bt):
    held = portfolio(bt)
    held.costs = bt.TradingCosts(0.01, 0.01, 0.02, 0.02)
    result = bt.BenchmarkComparison("2020-01-01").compare(held, "CRYPTO", data=feed())
    expected = (20 / (10 * 1.03) - 1) * 100
    assert result["benchmark_return"] == pytest.approx(expected)
    assert result["benchmark_gross_return"] == pytest.approx(100.0)
    assert result["alpha"] == pytest.approx(100.0 - expected)
    assert result["benchmark_entry_cost_rate"] == pytest.approx(0.03)


@pytest.mark.parametrize("missing", [0, 1])
def test_missing_exact_endpoint_is_not_silently_shifted(bt, missing):
    frame = feed().drop(feed().index[missing])
    result = bt.BenchmarkComparison("2020-01-01").compare(portfolio(bt), "CRYPTO", data=frame)
    assert result["status"] == "unavailable"
    assert result["reason"] == "missing_exact_benchmark_endpoints"
    assert result["benchmark_return"] is result["alpha"] is None
    assert result["portfolio_return"] == 100.0


@pytest.mark.parametrize(
    "options",
    [
        {"as_of": "2020-01-02T23:59:59Z"},
        {"end_date": "2020-01-01"},
        {"start_date": "2020-01-02"},
    ],
)
def test_bounds_cannot_admit_open_or_out_of_range_endpoint(bt, options):
    config = {"start_date": "2020-01-01", "as_of": "2020-02-01T00:00:00Z", **options}
    result = bt.BenchmarkComparison(**config).compare(portfolio(bt), "CRYPTO", data=feed())
    assert result["benchmark_return"] is None
    assert result["alpha"] is None


def test_explicit_bist_benchmark_and_istanbul_closure(bt, monkeypatch):
    monkeypatch.setattr(bt, "get_bist_data_isyatirim_only", lambda *a, **k: pytest.fail("provider"))
    comparison = bt.BenchmarkComparison("2020-01-01", as_of="2020-01-02T21:00:00Z")
    result = comparison.compare(portfolio(bt, "BIST"), "BIST", data=feed())
    assert result["status"] == "available"
    assert result["benchmark_symbol"] == "supplied:BIST"


def test_same_day_open_to_close_can_be_measured(bt):
    held = portfolio(bt)
    held.equity_curve = held.equity_curve[:1]
    held.backtest_metadata["comparison_end"] = pd.Timestamp("2020-01-01")
    result = bt.BenchmarkComparison("2020-01-01").compare(held, "CRYPTO", data=feed())
    assert result["portfolio_return"] == result["benchmark_return"] == 50.0


def test_zero_return_is_available_and_distinct_from_missing(bt):
    frame = feed()
    frame["Open"] = frame["Close"] = 10.0
    result = bt.BenchmarkComparison("2020-01-01").compare(portfolio(bt), "CRYPTO", data=frame)
    assert result["status"] == "available"
    assert result["benchmark_return"] == 0.0


@pytest.mark.parametrize("failure", ["none", "empty", "invalid", "exception"])
def test_failed_refresh_discards_previous_benchmark(bt, monkeypatch, failure):
    comparison = bt.BenchmarkComparison("2020-01-01")
    comparison.fetch_benchmark("CRYPTO", data=feed())

    def provider(*args, **kwargs):
        if failure == "exception":
            raise RuntimeError("provider unavailable")
        if failure == "none":
            return None
        if failure == "empty":
            return feed().iloc[:0]
        result = feed()
        result.iloc[0, 0] = 0.0
        return result

    monkeypatch.setattr(bt, "get_crypto_data", provider)
    if failure in {"invalid", "exception"}:
        with pytest.raises((ValueError, RuntimeError)):
            comparison.fetch_benchmark("CRYPTO")
    else:
        assert comparison.fetch_benchmark("CRYPTO") is None
    assert "CRYPTO" not in comparison.benchmark_data
    assert comparison.calculate_benchmark_return("CRYPTO", *feed().index) is None


def test_provider_read_once_for_compare(bt, monkeypatch):
    reads = []
    monkeypatch.setattr(bt, "get_crypto_data", lambda *a, **k: reads.append(a) or feed())
    bt.BenchmarkComparison("2020-01-01").compare(portfolio(bt), "CRYPTO")
    assert reads == [("BTCUSDT",)]


def test_unknown_portfolio_period_never_invents_baseline_or_fetches(bt, monkeypatch):
    held = portfolio(bt)
    held.backtest_metadata.clear()
    monkeypatch.setattr(bt, "get_crypto_data", lambda *a, **k: pytest.fail("provider"))
    result = bt.BenchmarkComparison("2020-01-01").compare(held, "CRYPTO")
    assert result["reason"] == "missing_portfolio_period"
    assert result["portfolio_return"] is result["benchmark_return"] is result["alpha"] is None


@pytest.mark.parametrize("bad_nav", [float("nan"), float("inf"), -1.0])
def test_invalid_nav_fails_instead_of_reporting_return(bt, bad_nav):
    held = portfolio(bt)
    held.equity_curve[-1]["Toplam Değer"] = bad_nav
    with pytest.raises(ValueError, match="NAV"):
        bt.BenchmarkComparison("2020-01-01").compare(held, "CRYPTO", data=feed())


def test_market_mismatch_and_invalid_period_are_errors(bt):
    comparison = bt.BenchmarkComparison("2020-01-01")
    with pytest.raises(ValueError, match="market_type"):
        comparison.compare(portfolio(bt), "BIST", data=feed())
    with pytest.raises(ValueError, match="interval"):
        comparison.calculate_benchmark_return("CRYPTO", *reversed(feed().index))


def test_same_day_sale_and_repurchase_invalidates_previous_nav(bt):
    held = portfolio(bt)
    last_day = feed().index[-1]
    assert held.sell("AAA", 10.0, last_day, "SELL")
    assert held.buy("BBB", 20.0, last_day, "BUY")
    assert held.cash == 0  # Same day and same cash, but a different position.
    result = bt.BenchmarkComparison("2020-01-01").compare(held, "CRYPTO", data=feed())
    assert result["status"] == "unavailable"
    assert result["reason"] == "stale_portfolio_valuation"
    assert result["portfolio_return"] is result["alpha"] is None


def test_cash_change_invalidates_previous_nav(bt):
    held = portfolio(bt)
    held.cash += 10
    result = bt.BenchmarkComparison("2020-01-01").compare(held, "CRYPTO", data=feed())
    assert result["reason"] == "stale_portfolio_valuation"


def test_complete_engine_period_is_independent_of_sparse_single_equity(bt, monkeypatch):
    dates = pd.date_range("2020-01-01", periods=130)
    frame = pd.DataFrame(
        {"Open": 10.0, "High": 30.0, "Low": 1.0, "Close": 20.0, "Volume": 100.0}, index=dates
    )
    no_signals = {"buy": {"cok_ucuz": False, "beles": False}, "sell": {"pahali": False}}
    engine = bt.BacktestEngine("2020-01-01", as_of="2021-01-01T00:00:00Z")
    monkeypatch.setattr(engine, "check_signals", lambda *a: no_signals)
    held = bt.Portfolio(100.0, "CRYPTO", 100.0, costs=bt.TradingCosts(0, 0, 0, 0))
    engine.run_single_symbol("AAA", "CRYPTO", held, data=frame)
    assert held.equity_curve[0]["Tarih"] == dates[70]
    result = bt.BenchmarkComparison("2020-01-01").compare(held, "CRYPTO", data=frame)
    assert result["start_date"] == dates[61]
    assert result["end_date"] == dates[-1]
    assert result["portfolio_return"] == 0
    assert result["benchmark_return"] == 100
    assert result["alpha"] == -100
