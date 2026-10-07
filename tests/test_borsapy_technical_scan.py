"""Real pinned native parser/Query with a bounded, offline scanner transport."""

import pandas as pd
import pytest

from application.services.borsapy_research import _technical_scan

PRESETS = [
    ("rsi < 30", "RSI", "less", 30.0),
    ("rsi > 70", "RSI", "greater", 70.0),
    ("close > sma_50", "close", "greater", "SMA50"),
    ("sma_20 crosses_above sma_50", "SMA20", "crosses_above", "SMA50"),
    ("macd > signal", "MACD.macd", "greater", "MACD.signal"),
]
INTERVALS = [
    ("1m", "|1"),
    ("5m", "|5"),
    ("15m", "|15"),
    ("30m", "|30"),
    ("1h", "|60"),
    ("4h", "|240"),
    ("1d", ""),
    ("1W", "|1W"),
]


@pytest.fixture
def transport(monkeypatch):
    from borsapy._providers.tradingview_screener_native import TVScreenerProvider
    from tradingview_screener import Query

    cookies = object()
    monkeypatch.setattr(TVScreenerProvider, "_get_auth_cookies", lambda self: cookies)

    def install(callback):
        def get(query, **kwargs):
            assert kwargs == {"cookies": cookies, "timeout": 10}
            assert query.query["markets"] == ["turkey"]
            return callback(query.query)

        monkeypatch.setattr(Query, "get_scanner_data", get)

    return install


def response(query, names):
    return pd.DataFrame(
        [
            {
                "ticker": f"BIST:{name}",
                "name": name,
                **{column: 100.0 for column in query["columns"] if column != "name"},
            }
            for name in names
        ],
        columns=["ticker", *query["columns"]],
    )


@pytest.mark.parametrize("interval,suffix", INTERVALS)
@pytest.mark.parametrize("condition,left,operator,right", PRESETS)
def test_native_conditions_and_selected_values_use_the_same_interval(
    transport, interval, suffix, condition, left, operator, right
):
    def get(query):
        assert query["filter"] == [
            {"left": "name", "operation": "in_range", "right": ["THYAO", "GARAN"]},
            {
                "left": left + suffix,
                "operation": operator,
                "right": right + suffix if isinstance(right, str) else right,
            },
        ]
        expected = {"name", "close" + suffix, left + suffix}
        if isinstance(right, str):
            expected.add(right + suffix)
        assert set(query["columns"]) == expected
        assert query["range"] == [0, 3]
        return 1, response(query, ["THYAO"])

    transport(get)
    result = _technical_scan(["THYAO", "GARAN"], condition, interval=interval)
    assert result["symbol"].tolist() == ["THYAO"]
    assert result["close"].tolist() == [100.0]
    assert all("|" not in column for column in result.columns)


def test_matching_requested_symbol_beyond_200_global_matches_is_not_lost(transport):
    global_matches = [f"OTHER{i}" for i in range(250)] + ["THYAO"]

    def get(query):
        # Simulate server filtering BEFORE its range. The former global top-200
        # query would not contain THYAO, despite its condition matching.
        scope = next(item["right"] for item in query["filter"] if item["left"] == "name")
        matching = [name for name in global_matches if name in scope]
        visible = matching[query["range"][0] : query["range"][1]]
        return len(matching), response(query, visible)

    transport(get)
    result = _technical_scan(["THYAO"], "close > sma_50", interval="1d")
    assert result["symbol"].tolist() == ["THYAO"]


def test_genuine_no_match_remains_successful_empty_result(transport):
    transport(lambda query: (0, response(query, [])))
    result = _technical_scan(["THYAO"], "close > sma_50", interval="1d")
    assert result.empty


@pytest.mark.parametrize("fault", ["partial", "excess", "outside", "duplicate", "schema", "market"])
def test_incomplete_or_out_of_scope_results_are_errors_not_false_empty(transport, fault):
    def get(query):
        frame = response(query, ["THYAO"])
        count = 1
        if fault == "partial":
            count = 2
        elif fault == "excess":
            frame = pd.concat([frame] * 3, ignore_index=True)
            count = 3
        elif fault == "outside":
            frame.loc[0, "name"] = "OTHER"
        elif fault == "duplicate":
            frame = pd.concat([frame] * 2, ignore_index=True)
            count = 2
        elif fault == "schema":
            frame = frame.drop(columns=["SMA50"])
        elif fault == "market":
            frame.loc[0, "ticker"] = "NASDAQ:THYAO"
        return count, frame

    transport(get)
    with pytest.raises(RuntimeError, match="sonuç doğrulanamadı"):
        _technical_scan(["THYAO", "GARAN"], "close > sma_50", interval="1d")


def test_transport_exception_is_sanitized_and_not_converted_to_no_matches(transport):
    def get(query):
        raise RuntimeError("private-cookie-marker")

    transport(get)
    with pytest.raises(RuntimeError) as caught:
        _technical_scan(["THYAO"], "rsi < 30", interval="1d")
    assert "private-cookie-marker" not in str(caught.value)
    assert caught.value.__suppress_context__
