"""Offline catalog/dispatch contracts checked against installed borsapy signatures."""

import inspect
import json
from functools import cached_property
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def research():
    from application.services import borsapy_research

    return borsapy_research


@pytest.fixture
def catalog():
    from application.services.borsapy_catalog import get_catalog

    return get_catalog()


@pytest.fixture
def frame():
    close = np.linspace(100, 150, 80) + np.sin(np.arange(80))
    return pd.DataFrame(
        {
            "Open": close - 0.5,
            "High": close + 1,
            "Low": close - 1,
            "Close": close,
            "Volume": 1000.0,
        },
        index=pd.date_range("2025-01-01", periods=80, name="Date", tz="Europe/Istanbul"),
    )


class SignatureCheckedProvider:
    """Inspect real public signatures; replace every network-bearing method body.

    A misspelled export, method, property, keyword or missing required argument
    fails rather than being silently accepted by a MagicMock. Only pure local
    calculate_* functions execute their actual package implementation.
    """

    def __init__(self, module, frame):
        self.module = module
        self.frame = frame
        self.calls = []

    def __getattr__(self, name):
        function = getattr(self.module, name)

        def call(*args, **kwargs):
            inspect.signature(function).bind(*args, **kwargs)
            self.calls.append((name, args, kwargs))
            if inspect.isclass(function):
                return SignatureCheckedInstance(self, function)
            if name.startswith("calculate_"):
                return function(*args, **kwargs)
            if name == "backtest":
                return SignatureCheckedInstance(self, self.module.BacktestResult)
            if name == "withholding_tax_rate":
                return 0.175
            return self.frame.copy()

        return call


class SignatureCheckedInstance:
    def __init__(self, owner, actual_class):
        self.owner = owner
        self.actual_class = actual_class

    def __getattr__(self, name):
        if name in {"equity_curve", "drawdown_curve", "buy_hold_curve"}:
            assert name in self.actual_class.__dataclass_fields__
            return self.owner.frame["Close"]
        descriptor = inspect.getattr_static(self.actual_class, name)

        def value():
            if name == "info" and self.actual_class.__name__ == "Ticker":
                return SimpleNamespace(todict=lambda: {"symbol": "THYAO", "price": 150.0})
            if name == "holdings":
                return pd.DataFrame([{"symbol": "THYAO", "value": 1500, "pnl": 100}])
            if name in {
                "to_dict",
                "risk_metrics",
                "current",
                "info",
                "detail",
                "performance",
                "recommendations",
                "analyst_price_targets",
                "rates",
                "ta_signals",
            }:
                return {"test_value": 1.0}
            if name == "management_fee":
                return 1.5
            return self.owner.frame.copy()

        if isinstance(descriptor, (property, cached_property)):
            self.owner.calls.append((f"{self.actual_class.__name__}.{name}", (), {}))
            return value()

        def call(*args, **kwargs):
            inspect.signature(descriptor).bind(None, *args, **kwargs)
            self.owner.calls.append((f"{self.actual_class.__name__}.{name}", args, kwargs))
            return value()

        return call


@pytest.fixture
def provider(frame):
    import borsapy

    return SignatureCheckedProvider(borsapy, frame)


def _defaults(operation):
    params = {
        field["name"]: field["default"] for field in operation["fields"] if "default" in field
    }
    if operation["id"] == "fund.tax":
        params["purchase_date"] = "2025-01-01"
    if operation["id"] == "stream.study":
        params["study"] = "STD;RSI"
    return params


def test_every_nonstream_operation_binds_real_package_signatures(research, catalog, provider):
    visited = set()
    for operation in catalog["operations"]:
        if operation["transport"] == "stream":
            continue
        result = research.run_operation(provider, operation["id"], _defaults(operation))
        assert result["operation"] == operation["id"]
        assert result["as_of"].endswith("Z")
        assert result["source"] == operation["source"]
        assert result["tables"] or result["summary"], operation["id"]
        json.dumps(result, allow_nan=False)
        visited.add(operation["id"])
    assert len(visited) >= 48


def test_all_dispatch_select_variants_bind_real_signatures(research, catalog, provider):
    for operation in catalog["operations"]:
        if operation["transport"] != "query":
            continue
        for field in operation["fields"]:
            if field["type"] != "select":
                continue
            for option in field["options"]:
                params = {**_defaults(operation), field["name"]: option["value"]}
                if field["name"] == "interval" and "period" in params:
                    params["period"] = "1d"
                result = research.run_operation(provider, operation["id"], params)
                json.dumps(result, allow_nan=False)


def test_catalog_covers_all_22_readme_features_and_is_independent(catalog):
    from application.services.borsapy_catalog import get_catalog

    required = {
        "stream.quote",
        "backtest",
        "replay",
        "search",
        "ta.signals",
        "heikin_ashi",
        "etf_holders",
        "portfolio",
        "fx.current",
        "crypto.current",
        "fund.info",
        "inflation",
        "evds.series",
        "viop",
        "bonds",
        "tcmb.rates",
        "eurobonds",
        "calendar",
        "screener.fundamental",
        "ta.indicators",
        "twitter.search",
        "kap.news",
    }
    ids = [operation["id"] for operation in catalog["operations"]]
    assert len(ids) == len(set(ids))
    assert required.issubset(ids)
    assert {"company.financials", "company.actions", "fund.allocation", "fund.tax"}.issubset(ids)
    assert all(
        op["group"] in {group["id"] for group in catalog["groups"]} for op in catalog["operations"]
    )
    catalog["operations"][0]["fields"][0]["default"] = "changed"
    assert get_catalog()["operations"][0]["fields"][0]["default"] == "THYAO"


@pytest.mark.parametrize(
    "operation,params",
    [
        ("__import__('os').system", {}),
        ("company.__dict__", {}),
        ("history", {"symbol": "https://example.test"}),
        ("history", {"symbol": "THYAO", "start": "1900-01-01"}),
        ("backtest", {"strategy": "exec('x')"}),
        ("backtest", {"capital": float("inf")}),
        ("backtest", {"capital": 10**1000}),
        ("backtest", {"capital": True}),
        ("backtest", {"commission": -0.1}),
        ("search", {"limit": 1.5}),
        ("search", {"limit": 101}),
        ("search", {"query": "x" * 241}),
        ("evds.series", {"api_key": "do-not-read"}),
        ("evds.series", {"codes": "https://example.test"}),
        ("evds.series", {"codes": ["TP.TEST"] * 6}),
        ("screener.technical", {"condition": "exec('x')"}),
        ("screener.technical", {"symbols": ",".join(f"A{i}" for i in range(21))}),
        ("fund.compare", {"fund_codes": "YAY,YAY"}),
        ("inflation.calculate", {"start": "2025-13"}),
        ("inflation.calculate", {"start": "2025-01", "end": "2024-01"}),
        ("fund.tax", {"purchase_date": "2025-02-31"}),
        ("fund.tax", {"purchase_date": "2099-01-01"}),
        ("history", {"period": "1mo", "interval": "1m"}),
        ("history", {"period": "1y", "interval": "1h"}),
    ],
)
def test_invalid_inputs_fail_before_any_provider_access(research, operation, params):
    class Bomb:
        def __getattr__(self, name):
            raise AssertionError("Provider must not be reached")

    with pytest.raises(research.ResearchInputError):
        research.run_operation(Bomb(), operation, params)


@pytest.mark.parametrize(
    "positions",
    [
        [],
        "not json",
        [{"symbol": "THYAO", "shares": 1, "cost": 1, "asset_type": "stock"}] * 11,
        [{"symbol": "THYAO", "shares": 1, "cost": 1, "asset_type": "stock", "path": "x"}],
        [{"symbol": "THYAO", "shares": 0, "cost": 1, "asset_type": "stock"}],
        [{"symbol": "THYAO", "shares": 1, "cost": -1, "asset_type": "stock"}],
        [{"symbol": "THYAO", "shares": True, "cost": 1, "asset_type": "stock"}],
        [{"symbol": "THYAO", "shares": 1, "cost": 1, "asset_type": "__dict__"}],
    ],
)
def test_portfolio_has_finite_explicit_bounded_positions(research, positions):
    with pytest.raises(research.ResearchInputError):
        research.validate_params("portfolio", {"positions": positions})


def test_normalized_params_are_idempotent_and_accept_row_editor(research):
    params = {"positions": [{"symbol": "thyao", "shares": 2, "cost": 0, "asset_type": "stock"}]}
    parsed = research.validate_params("portfolio", params)
    assert parsed["positions"][0]["symbol"] == "THYAO"
    assert research.validate_params("portfolio", parsed) == parsed
    for operation, parameters in (
        ("fund.compare", {"fund_codes": "YAY,AFT"}),
        ("evds.series", {"codes": "TP.TEST"}),
    ):
        parsed = research.validate_params(operation, parameters)
        assert research.validate_params(operation, parsed) == parsed


def test_ha_real_local_calculation_produces_synthetic_chart(research, provider, frame):
    result = research.run_operation(provider, "heikin_ashi", {})
    assert len(result["candles"]) == len(frame)
    expected = (frame.iloc[0]["Open"] + frame.iloc[0]["Close"]) / 2
    assert result["candles"][0]["open"] == pytest.approx(expected)
    assert any("sentetik" in warning for warning in result["warnings"])


def test_weekly_scanner_mapping_and_fixed_condition(research, provider):
    research.run_operation(provider, "screener.technical", {"interval": "1wk"})
    call = next(call for call in provider.calls if call[0] == "scan")
    assert call[2]["interval"] == "1W"
    assert call[1][1] == "rsi < 30"


def test_bank_request_does_not_fetch_metal_only_endpoint_for_usd(research, provider):
    research.run_operation(provider, "fx.banks", {"asset": "USD"})
    assert "FX.institution_rates" not in [call[0] for call in provider.calls]
    research.run_operation(provider, "fx.banks", {"asset": "gram-altin"})
    assert "FX.institution_rates" in [call[0] for call in provider.calls]


def test_fx_intraday_passes_interval_and_enforces_finite_history(research, provider):
    research.run_operation(provider, "fx.history", {"period": "5d", "interval": "1m"})
    call = next(call for call in provider.calls if call[0] == "FX.history")
    assert call[2] == {"period": "5d", "interval": "1m"}
    with pytest.raises(research.ResearchInputError):
        research.validate_params("fx.history", {"period": "1y", "interval": "1m"})


def test_backtest_is_named_fixed_cross_and_clearly_separate(research, provider):
    result = research.run_operation(provider, "backtest", {})
    call = next(call for call in provider.calls if call[0] == "backtest")
    strategy = call[1][1]
    assert strategy.__name__ == "sma_20_50_cross"
    assert strategy({}, None, {"sma_20": np.nan, "sma_50": 50}) == "HOLD"
    assert strategy({}, None, {"sma_20": 49, "sma_50": 50}) == "HOLD"
    assert strategy({}, None, {"sma_20": 51, "sma_50": 50}) == "BUY"
    assert strategy({}, "long", {"sma_20": 52, "sma_50": 50}) == "HOLD"
    assert strategy({}, "long", {"sma_20": 49, "sma_50": 50}) == "SELL"
    assert any("aynı mum kapanışında" in warning for warning in result["warnings"])
    assert any("Rapot" in warning for warning in result["warnings"])


def test_normalizer_preserves_index_and_nulls_without_serialization_hooks(research):
    class Poison:
        def __repr__(self):
            raise AssertionError("Must not serialize arbitrary objects")

    data = pd.DataFrame(
        [[np.nan, np.inf, Poison(), "secret"]],
        columns=["index", "index", "object", "api_key"],
        index=pd.Index(["Revenue"], name="index"),
    )
    result = research.normalize_result("company.financials", {"table": data, "token": "secret"})
    table = result["tables"][0]
    assert table["columns"] == ["index", "index_2", "index_3", "object"]
    assert table["rows"] == [{"index": "Revenue", "index_2": None, "index_3": None, "object": None}]
    assert "secret" not in json.dumps(result, allow_nan=False)


def test_normalizer_enforces_global_table_cell_text_budget(research):
    data = pd.DataFrame({f"col{i}": ["ü" * 4000] * 1000 for i in range(40)})
    result = research.normalize_result("company.financials", {f"table{i}": data for i in range(25)})
    assert (
        sum(len(table["rows"]) * len(table["columns"]) for table in result["tables"])
        <= research.MAX_CELLS
    )
    assert len(json.dumps(result, ensure_ascii=False)) < 1500000
    assert any("sınır" in warning or "en fazla" in warning for warning in result["warnings"])


def test_overflow_list_does_not_change_previous_table_metadata(research):
    raw = {f"table{i}": pd.DataFrame({"value": [i]}) for i in range(research.MAX_TABLES)}
    raw["extra"] = [{"value": 1}] * 100
    result = research.normalize_result("search", raw)
    assert len(result["tables"]) == research.MAX_TABLES
    assert result["tables"][-1]["total_rows"] == 1
    assert result["tables"][-1]["truncated"] is False


def test_candles_are_sorted_bounded_finite_and_timezone_explicit(research, frame):
    frame = frame.iloc[::-1].copy()
    frame.iloc[0, frame.columns.get_loc("Close")] = np.inf
    result = research.normalize_result("history", {}, candles=frame)
    assert len(result["candles"]) == len(frame) - 1
    times = [candle["time"] for candle in result["candles"]]
    assert times == sorted(times)
    assert times[0] == int(pd.Timestamp("2025-01-01", tz="Europe/Istanbul").timestamp())
    json.dumps(result, allow_nan=False)


def test_stream_transport_does_not_execute_as_query(research):
    with pytest.raises(research.ResearchInputError, match="akış"):
        research.run_operation(None, "stream.quote", {})
