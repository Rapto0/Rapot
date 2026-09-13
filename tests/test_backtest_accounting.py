"""Offline, hand-calculated checks of the backtest's reference-price cost model."""

import importlib
import math
import warnings
from contextlib import nullcontext
from copy import deepcopy
from datetime import datetime, timedelta
from types import ModuleType
from typing import Any

import pandas as pd
import pytest


@pytest.fixture
def accounting() -> ModuleType:
    # The legacy module changes warning filters during import; keep pytest's policy.
    with warnings.catch_warnings():
        return importlib.import_module("backtesting_system")


def _costs(accounting: ModuleType) -> Any:
    return accounting.TradingCosts(
        bist_commission=0.01,
        bist_slippage=0.02,
        crypto_commission=0.02,
        crypto_slippage=0.01,
    )


def _assert_conservation(portfolio: Any) -> None:
    open_basis = math.fsum(lot.invested for queue in portfolio.lots.values() for lot in queue)
    realized = math.fsum(
        stats["Toplam Kar/Zarar"] for stats in portfolio.symbol_performance.values()
    )
    assert portfolio.cash + open_basis == pytest.approx(portfolio.initial_cash + realized)


def _state(portfolio: Any) -> dict[str, Any]:
    """Copy monetary state without including deliberately mutated cost configuration."""
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


def test_entry_basis_includes_both_purchase_costs(accounting: ModuleType) -> None:
    costs = accounting.TradingCosts(bist_commission=0.01, bist_slippage=0.02)
    portfolio = accounting.Portfolio(2060.0, "BIST", 1030.0, costs)
    assert portfolio.buy("AAA", 100.0, datetime(2026, 1, 1), "BUY")

    lot = portfolio.lots["AAA"][0]
    assert lot.shares == pytest.approx(10.0)
    assert portfolio.cash == pytest.approx(1030.0)
    assert lot.invested == pytest.approx(1030.0)
    assert lot.price == 100.0
    assert lot.commission == pytest.approx(10.0)
    assert lot.slippage == pytest.approx(20.0)
    assert portfolio.get_portfolio_value({"AAA": 100.0}) == pytest.approx(2030.0)
    _assert_conservation(portfolio)


def test_same_price_round_trip_realized_pnl_equals_cash_change(accounting: ModuleType) -> None:
    costs = accounting.TradingCosts(bist_commission=0.01, bist_slippage=0.02)
    portfolio = accounting.Portfolio(2060.0, "BIST", 1030.0, costs)
    bought_at = datetime(2026, 1, 1)
    assert portfolio.buy("AAA", 100.0, bought_at, "BUY")
    assert portfolio.sell("AAA", 100.0, bought_at + timedelta(days=3), "SELL")

    assert portfolio.cash == pytest.approx(2000.0)
    assert portfolio.symbol_performance["AAA"]["Toplam Kar/Zarar"] == pytest.approx(-60.0)
    assert portfolio.all_trades[-1]["Kar/Zarar"] == -60.0
    assert not portfolio.lots
    assert portfolio.total_commission_paid == pytest.approx(20.0)
    assert portfolio.total_slippage_cost == pytest.approx(40.0)
    assert portfolio.total_transaction_cost == pytest.approx(60.0)
    assert portfolio.symbol_performance["AAA"]["Toplam Yatırım"] == pytest.approx(1030.0)
    assert portfolio.all_trades[-1]["Kar/Zarar %"] == -5.83
    _assert_conservation(portfolio)


def test_fifo_closes_one_whole_lot_and_retains_other_entry_costs(accounting: ModuleType) -> None:
    portfolio = accounting.Portfolio(4000.0, "BIST", 1030.0, _costs(accounting))
    start = datetime(2026, 1, 1)
    assert portfolio.buy("AAA", 100.0, start, "FIRST")
    _assert_conservation(portfolio)
    assert portfolio.buy("AAA", 200.0, start + timedelta(days=1), "SECOND")
    second_lot = portfolio.lots["AAA"][1]
    second_state = deepcopy(vars(second_lot))
    _assert_conservation(portfolio)

    assert portfolio.sell("AAA", 110.0, start + timedelta(days=2), "SELL FIRST")
    assert list(portfolio.lots["AAA"]) == [second_lot]
    assert vars(second_lot) == second_state
    assert portfolio.cash == pytest.approx(3007.0)
    assert portfolio.symbol_performance["AAA"]["Toplam Kar/Zarar"] == pytest.approx(37.0)
    assert portfolio.all_trades[-1]["Alış Tarihi"] == start
    assert portfolio.all_trades[-1]["Miktar"] == 10.0
    assert portfolio.all_trades[-1]["Maliyet Tabanı"] == 1030.0
    _assert_conservation(portfolio)

    assert portfolio.sell("AAA", 180.0, start + timedelta(days=3), "SELL SECOND")
    assert not portfolio.lots
    assert portfolio.cash == pytest.approx(3880.0)
    stats = portfolio.symbol_performance["AAA"]
    assert stats["Toplam Kar/Zarar"] == pytest.approx(-120.0)
    assert stats["Toplam Yatırım"] == pytest.approx(2060.0)
    assert (stats["Tamamlanan İşlem"], stats["Kazanan"], stats["Kaybeden"]) == (2, 1, 1)
    assert portfolio.total_commission_paid == pytest.approx(40.0)
    assert portfolio.total_slippage_cost == pytest.approx(80.0)
    _assert_conservation(portfolio)


def test_symbol_inventories_and_average_reference_price_remain_distinct(
    accounting: ModuleType,
) -> None:
    portfolio = accounting.Portfolio(5000.0, "BIST", 1030.0, _costs(accounting))
    date = datetime(2026, 1, 1)
    assert portfolio.buy("AAA", 100.0, date, "BUY")
    assert portfolio.buy("AAA", 200.0, date, "BUY")
    assert portfolio.buy("BBB", 80.0, date, "BUY")
    summary = {row["Sembol"]: row for row in portfolio.get_open_positions_summary()}
    assert summary["AAA"]["Toplam Miktar"] == 15.0
    assert summary["AAA"]["Toplam Yatırım"] == 2060.0
    assert summary["AAA"]["Ortalama Fiyat"] == 133.3333
    assert summary["AAA"]["Ortalama Maliyet"] == 137.3333
    assert summary["BBB"]["Ortalama Fiyat"] == 80.0
    assert summary["BBB"]["Ortalama Maliyet"] == 82.4
    bbb_state = deepcopy(vars(portfolio.lots["BBB"][0]))
    assert portfolio.sell("AAA", 100.0, date + timedelta(days=1), "SELL")
    assert vars(portfolio.lots["BBB"][0]) == bbb_state
    _assert_conservation(portfolio)


@pytest.mark.parametrize(
    ("commission", "slippage", "budget", "net_revenue", "fees", "slip_cost"),
    [
        (0.0, 0.0, 1000.0, 1000.0, 0.0, 0.0),
        (0.01, 0.0, 1010.0, 990.0, 20.0, 0.0),
        (0.0, 0.02, 1020.0, 980.0, 0.0, 40.0),
    ],
)
def test_zero_and_separate_cost_components(
    accounting: ModuleType,
    commission: float,
    slippage: float,
    budget: float,
    net_revenue: float,
    fees: float,
    slip_cost: float,
) -> None:
    costs = accounting.TradingCosts(bist_commission=commission, bist_slippage=slippage)
    portfolio = accounting.Portfolio(budget, "BIST", budget, costs)
    date = datetime(2026, 1, 1)
    assert portfolio.buy("AAA", 100.0, date, "BUY")
    assert portfolio.lots["AAA"][0].shares == pytest.approx(10.0)
    assert portfolio.sell("AAA", 100.0, date + timedelta(days=1), "SELL")
    assert portfolio.cash == pytest.approx(net_revenue)
    assert portfolio.total_commission_paid == pytest.approx(fees)
    assert portfolio.total_slippage_cost == pytest.approx(slip_cost)
    assert portfolio.total_transaction_cost == pytest.approx(budget - net_revenue)
    _assert_conservation(portfolio)


def test_crypto_selects_its_own_component_rates(accounting: ModuleType) -> None:
    portfolio = accounting.Portfolio(1030.0, "CRYPTO", 1030.0, _costs(accounting))
    date = datetime(2026, 1, 1)
    assert portfolio.buy("AAA", 100.0, date, "BUY")
    assert portfolio.sell("AAA", 100.0, date + timedelta(days=1), "SELL")
    assert portfolio.cash == pytest.approx(970.0)
    assert portfolio.total_commission_paid == pytest.approx(40.0)
    assert portfolio.total_slippage_cost == pytest.approx(20.0)
    _assert_conservation(portfolio)


def test_later_rate_changes_do_not_reprice_the_saved_purchase_costs(accounting: ModuleType) -> None:
    costs = _costs(accounting)
    portfolio = accounting.Portfolio(1030.0, "BIST", 1030.0, costs)
    date = datetime(2026, 1, 1)
    assert portfolio.buy("AAA", 100.0, date, "BUY")
    costs.bist_commission, costs.bist_slippage = 0.02, 0.01
    assert portfolio.sell("AAA", 100.0, date + timedelta(days=1), "SELL")
    sale = portfolio.all_trades[-1]
    assert sale["Alış Komisyonu"] == 10.0
    assert sale["Alış Kayma Maliyeti"] == 20.0
    assert sale["Komisyon"] == 20.0
    assert sale["Kayma Maliyeti"] == 10.0
    assert sale["Maliyet Tabanı"] == 1030.0
    assert portfolio.total_commission_paid == pytest.approx(30.0)
    assert portfolio.total_slippage_cost == pytest.approx(30.0)
    assert portfolio.cash == pytest.approx(970.0)
    _assert_conservation(portfolio)


def test_raw_quantities_and_profits_are_not_rounded_to_report_precision(
    accounting: ModuleType,
) -> None:
    portfolio = accounting.Portfolio(1030.0, "BIST", 1030.0, _costs(accounting))
    date = datetime(2026, 1, 1)
    assert portfolio.buy("AAA", 3.0, date, "BUY")
    assert portfolio.lots["AAA"][0].shares == pytest.approx(1000.0 / 3.0, abs=1e-11)
    assert portfolio.lots["AAA"][0].shares != portfolio.all_trades[-1]["Miktar"]
    assert portfolio.sell("AAA", 4.0, date + timedelta(days=1), "SELL")
    assert portfolio.cash == pytest.approx(3880.0 / 3.0, abs=1e-10)
    assert portfolio.symbol_performance["AAA"]["Toplam Kar/Zarar"] == pytest.approx(790.0 / 3.0)
    assert portfolio.all_trades[-1]["Kar/Zarar"] == 263.33
    _assert_conservation(portfolio)


def test_cash_flow_and_entry_basis_columns_describe_the_whole_cost(accounting: ModuleType) -> None:
    portfolio = accounting.Portfolio(2060.0, "BIST", 1030.0, _costs(accounting))
    date = datetime(2026, 1, 1)
    assert portfolio.buy("AAA", 100.0, date, "BUY")
    assert portfolio.sell("AAA", 100.0, date + timedelta(days=1), "SELL")
    purchase, sale = portfolio.all_trades
    assert purchase["Nakit Akışı"] == -1030.0
    assert sale["Nakit Akışı"] == 970.0
    for trade in (purchase, sale):
        assert trade["Tutar"] == 1000.0
        assert trade["Komisyon"] == 10.0
        assert trade["Kayma Maliyeti"] == 20.0
        assert trade["Toplam İşlem Maliyeti"] == 30.0
        assert trade["Maliyet Tabanı"] == 1030.0


def test_insufficient_cash_and_missing_inventory_have_no_side_effects(
    accounting: ModuleType,
) -> None:
    portfolio = accounting.Portfolio(1030.0, "BIST", 1030.0, _costs(accounting))
    date = datetime(2026, 1, 1)
    assert portfolio.buy("AAA", 100.0, date, "BUY")
    assert portfolio.cash == pytest.approx(0.0)
    before = _state(portfolio)
    assert portfolio.buy("AAA", 100.0, date, "NO CASH") is False
    assert portfolio.sell("MISSING", 100.0, date, "NO LOT") is False
    assert _state(portfolio) == before


@pytest.mark.parametrize("price", [0.0, -1.0, math.nan, math.inf, -math.inf])
def test_invalid_prices_reject_both_sides_without_mutation(
    accounting: ModuleType, price: float
) -> None:
    portfolio = accounting.Portfolio(2060.0, "BIST", 1030.0, _costs(accounting))
    date = datetime(2026, 1, 1)
    assert portfolio.buy("AAA", 100.0, date, "BUY")
    before = _state(portfolio)
    assert portfolio.buy("AAA", price, date, "INVALID") is False
    assert portfolio.sell("AAA", price, date, "INVALID") is False
    assert _state(portfolio) == before


@pytest.mark.parametrize("date", [None, "2026-01-02", pd.NaT])
def test_invalid_dates_preserve_inventory_and_money(accounting: ModuleType, date: Any) -> None:
    portfolio = accounting.Portfolio(2060.0, "BIST", 1030.0, _costs(accounting))
    assert portfolio.buy("AAA", 100.0, datetime(2026, 1, 1), "BUY")
    before = _state(portfolio)
    assert portfolio.buy("AAA", 100.0, date, "INVALID") is False
    assert portfolio.sell("AAA", 100.0, date, "INVALID") is False
    assert _state(portfolio) == before


def test_sale_before_purchase_does_not_pop_fifo_lot(accounting: ModuleType) -> None:
    portfolio = accounting.Portfolio(2060.0, "BIST", 1030.0, _costs(accounting))
    date = datetime(2026, 1, 2)
    assert portfolio.buy("AAA", 100.0, date, "BUY")
    before = _state(portfolio)
    assert portfolio.sell("AAA", 100.0, date - timedelta(days=1), "INVALID") is False
    assert _state(portfolio) == before


@pytest.mark.parametrize(
    "kwargs",
    [
        {"bist_commission": -0.01},
        {"bist_slippage": math.nan},
        {"crypto_commission": math.inf},
        {"crypto_slippage": -math.inf},
        {"bist_commission": 0.5, "bist_slippage": 0.5},
        {"crypto_commission": 0.9, "crypto_slippage": 0.2},
    ],
)
def test_invalid_cost_configuration_is_rejected(
    accounting: ModuleType, kwargs: dict[str, float]
) -> None:
    with pytest.raises(ValueError):
        accounting.TradingCosts(**kwargs)


@pytest.mark.parametrize("field", ["initial_cash", "trade_amount"])
@pytest.mark.parametrize("value", [0.0, -1.0, math.nan, math.inf])
def test_invalid_capital_or_budget_is_rejected(
    accounting: ModuleType, field: str, value: float
) -> None:
    kwargs = {"initial_cash": 2060.0, "trade_amount": 1030.0, "market_type": "BIST"}
    kwargs[field] = value
    with pytest.raises(ValueError):
        accounting.Portfolio(**kwargs)


def test_unknown_market_does_not_silently_use_crypto_costs(accounting: ModuleType) -> None:
    with pytest.raises(ValueError):
        accounting.Portfolio(2060.0, "UNKNOWN", 1030.0, _costs(accounting))
    with pytest.raises(ValueError):
        _costs(accounting).get_components("UNKNOWN")


@pytest.mark.parametrize("value", [-0.01, math.nan, 1.0])
def test_mutated_invalid_costs_fail_before_either_side_changes_state(
    accounting: ModuleType, value: float
) -> None:
    costs = _costs(accounting)
    portfolio = accounting.Portfolio(2060.0, "BIST", 1030.0, costs)
    date = datetime(2026, 1, 1)
    assert portfolio.buy("AAA", 100.0, date, "BUY")
    before = _state(portfolio)
    costs.bist_commission = value
    with pytest.raises(ValueError):
        portfolio.buy("AAA", 100.0, date, "INVALID")
    with pytest.raises(ValueError):
        portfolio.sell("AAA", 100.0, date + timedelta(days=1), "INVALID")
    assert _state(portfolio) == before


def test_lot_positional_constructor_keeps_zero_cost_compatibility(accounting: ModuleType) -> None:
    date = datetime(2026, 1, 1)
    legacy = accounting.Lot("AAA", 10.0, 100.0, date, "BUY")
    with_costs = accounting.Lot("AAA", 10.0, 100.0, date, "BUY", commission=10.0, slippage=20.0)
    assert (legacy.commission, legacy.slippage, legacy.invested) == (0.0, 0.0, 1000.0)
    assert with_costs.invested == 1030.0


def test_excel_and_console_use_corrected_realized_basis_without_writing_files(
    accounting: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    portfolio = accounting.Portfolio(2060.0, "BIST", 1030.0, _costs(accounting))
    empty_crypto = accounting.Portfolio(2060.0, "CRYPTO", 1030.0, _costs(accounting))
    date = datetime(2026, 1, 1)
    assert portfolio.buy("AAA", 100.0, date, "FIRST")
    assert portfolio.buy("AAA", 100.0, date, "SECOND")
    assert portfolio.sell("AAA", 100.0, date + timedelta(days=1), "SELL FIRST")
    captured: dict[str, pd.DataFrame] = {}

    def capture_sheet(frame: pd.DataFrame, writer: Any, *, sheet_name: str, index: bool) -> None:
        assert index is False
        captured[sheet_name] = frame.copy(deep=True)

    monkeypatch.setattr(accounting.pd, "ExcelWriter", lambda *args, **kwargs: nullcontext())
    monkeypatch.setattr(accounting.pd.DataFrame, "to_excel", capture_sheet)
    engine = accounting.BacktestEngine()
    engine.generate_excel_report(portfolio, empty_crypto)
    general = captured["Genel Özet"].set_index("Metrik")
    assert general.loc["Gerçekleşen Kar/Zarar", "BIST"] == "-60.00 TL"
    assert general.loc["Güncel Nakit", "BIST"] == "970.00 TL"
    assert general.loc["Ödenen Komisyon", "BIST"] == "30.00 TL"
    assert general.loc["Kayma Maliyeti", "BIST"] == "60.00 TL"
    assert general.loc["Toplam İşlem Maliyeti", "BIST"] == "90.00 TL"
    closed = captured["BIST Sembol Performans"].iloc[0]
    assert closed["Toplam Yatırım (TL)"] == 1030.0
    assert closed["Toplam Kar/Zarar (TL)"] == -60.0
    assert closed["Getiri %"] == -5.83
    assert captured["BIST Açık Pozisyonlar"].iloc[0]["Toplam Yatırım"] == 1030.0
    assert engine._calculate_stats(portfolio)["profit"] == pytest.approx(-60.0)
    engine.print_summary(portfolio, empty_crypto)
    text = capsys.readouterr().out
    assert "Gerçekleşen Kar/Zarar: -60.00 TL" in text
    assert "Ödenen Komisyon: 30.00 TL" in text
    assert "Kayma Maliyeti: 60.00 TL" in text
    assert "Toplam İşlem Maliyeti: 90.00 TL" in text


def test_worker_result_keeps_fee_and_slippage_separate_with_synthetic_inputs(
    accounting: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise only result assembly; provider and signal engine are explicit stubs."""
    frame = pd.DataFrame({"Close": [100.0] * 120})
    monkeypatch.setattr(accounting, "get_bist_data_isyatirim_only", lambda *args, **kwargs: frame)
    monkeypatch.setattr(accounting, "trading_costs", _costs(accounting))

    def synthetic_round_trip(engine: Any, symbol: str, market: str, portfolio: Any) -> bool:
        assert market == "BIST"
        date = datetime(2026, 1, 1)
        assert portfolio.buy(symbol, 100.0, date, "BUY")
        assert portfolio.sell(symbol, 100.0, date + timedelta(days=1), "SELL")
        return True

    monkeypatch.setattr(accounting.BacktestEngine, "run_single_symbol", synthetic_round_trip)
    result = accounting._run_symbol_backtest(("AAA", "BIST", "2026-01-01", 1030.0))
    assert result == {
        "symbol": "AAA",
        "success": True,
        "profit": pytest.approx(-60.0),
        "trades": 2,
        "commission_paid": pytest.approx(20.0),
        "slippage_cost": pytest.approx(40.0),
        "transaction_cost": pytest.approx(60.0),
    }


@pytest.mark.parametrize(
    ("initial_cash", "budget", "purchases"),
    [(1000.8, 100.08, 10), (0.3, 0.1, 3), (10.5, 1.05, 10), (100.0, 0.1, 1000)],
)
def test_repeated_fractional_budgets_spend_available_capital_without_roundoff_rejection(
    accounting: ModuleType, initial_cash: float, budget: float, purchases: int
) -> None:
    """The listed decimal capital funds exactly this many equal, zero-fee lots."""
    costs = accounting.TradingCosts(bist_commission=0.0, bist_slippage=0.0)
    portfolio = accounting.Portfolio(initial_cash, "BIST", budget, costs)
    date = datetime(2026, 1, 1)
    for _ in range(purchases):
        assert portfolio.buy("AAA", 1.0, date, "BUY")
        assert portfolio.cash >= 0.0
        _assert_conservation(portfolio)

    assert len(portfolio.lots["AAA"]) == purchases
    assert portfolio.cash == pytest.approx(0.0, abs=4 * math.ulp(initial_cash))
    assert math.fsum(lot.invested for lot in portfolio.lots["AAA"]) == pytest.approx(
        initial_cash, rel=0.0, abs=4 * math.ulp(initial_cash)
    )
    before = _state(portfolio)
    assert portfolio.buy("AAA", 1.0, date, "NO CAPITAL LEFT") is False
    assert _state(portfolio) == before


@pytest.mark.parametrize(("initial_cash", "budget"), [(100.079999, 100.08), (5e-13, 1e-12)])
def test_roundoff_allowance_does_not_fund_a_real_shortfall(
    accounting: ModuleType, initial_cash: float, budget: float
) -> None:
    """Neither a small nominal deficit nor sub-penny units imply free capital."""
    costs = accounting.TradingCosts(bist_commission=0.0, bist_slippage=0.0)
    portfolio = accounting.Portfolio(initial_cash, "BIST", budget, costs)
    before = _state(portfolio)
    assert portfolio.buy("AAA", 1.0, datetime(2026, 1, 1), "INSUFFICIENT") is False
    assert _state(portfolio) == before


def test_large_initial_capital_does_not_expand_later_spending_allowance(
    accounting: ModuleType,
) -> None:
    costs = accounting.TradingCosts(bist_commission=0.0, bist_slippage=0.0)
    portfolio = accounting.Portfolio(1e16, "BIST", 1e16 - 2.0, costs)
    date = datetime(2026, 1, 1)
    assert portfolio.buy("AAA", 1.0, date, "FIRST")
    assert portfolio.cash == 2.0
    portfolio.trade_amount = 3.0
    before = _state(portfolio)
    assert portfolio.buy("AAA", 1.0, date, "INSUFFICIENT") is False
    assert _state(portfolio) == before


@pytest.mark.parametrize("side", ["buy", "sell"])
@pytest.mark.parametrize("symbol", [[], None, "", " \t"])
def test_invalid_symbols_reject_without_changing_money_or_inventory(
    accounting: ModuleType, side: str, symbol: Any
) -> None:
    portfolio = accounting.Portfolio(2060.0, "BIST", 1030.0, _costs(accounting))
    date = datetime(2026, 1, 1)
    assert portfolio.buy("AAA", 100.0, date, "BUY")
    before = _state(portfolio)
    assert getattr(portfolio, side)(symbol, 100.0, date, "INVALID") is False
    assert _state(portfolio) == before
