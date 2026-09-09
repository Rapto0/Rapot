"""Local source-contract checks, not a Pine compiler or TradingView runtime test."""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from middleware.domain.constants import SIGNAL_SIDE_MAP

PINE = (Path(__file__).resolve().parents[1] / "pine/combo_hunter_binance.pine").read_text(
    encoding="utf-8"
)


def assignment(name: str) -> str:
    match = re.search(rf"^{name}\s*=\s*(.+)$", PINE, flags=re.MULTILINE)
    assert match is not None, f"Missing Pine assignment: {name}"
    return match.group(1).strip()


def function_body(name: str) -> str:
    match = re.search(rf"^{name}\([^\n]*\) =>\n((?:    [^\n]*\n|\n)+)", PINE, re.MULTILINE)
    assert match is not None, f"Missing Pine function: {name}"
    return match.group(1)


class StringFunctions:
    """Only the documented string operations used in the simple chart guard."""

    upper = staticmethod(str.upper)
    length = staticmethod(len)

    @staticmethod
    def match(value: str, pattern: str) -> str:
        result = re.search(pattern, value)
        return result.group(0) if result is not None else ""


@pytest.mark.parametrize(
    "prefix,ticker,kind,base,quote,standard,allowed",
    [
        ("BINANCE", "BTCUSDT", "crypto", "BTC", "USDT", True, True),
        ("BINANCE", "1INCHUSDT", "crypto", "1INCH", "USDT", True, True),
        ("BINANCE", "btcusdt", "crypto", "BTC", "USDT", True, True),
        ("BINANCE", "BTCUSDT.P", "crypto", "BTC", "USDT", True, False),
        ("BINANCE", "BTCUSDT", "futures", "BTC", "USDT", True, False),
        ("BINANCE", "BTCUSDT240927", "crypto", "BTC", "USDT", True, False),
        ("BINANCEUS", "BTCUSDT", "crypto", "BTC", "USDT", True, False),
        ("BYBIT", "BTCUSDT", "crypto", "BTC", "USDT", True, False),
        ("BIST", "THYAO", "stock", "", "TRY", True, False),
        ("BINANCE", "BTCUSDT", "crypto", "BTC", "USDT", False, False),
        ("BINANCE", "BTCUSDT", "crypto", "", "USDT", True, False),
        ("BINANCE", "BTC-USDT", "crypto", "BTC-", "USDT", True, False),
        ("BINANCE", "BİTCUSDT", "crypto", "BİTC", "USDT", True, False),
        ("BINANCE", "btcuſdt", "crypto", "BTC", "USDT", True, False),
        ("BINANCE", "ßUSDT", "crypto", "SS", "USDT", True, False),
        ("BINANCE", "btcusdı", "crypto", "BTC", "USDI", True, False),
        ("BINANCE", "A" * 21 + "USDT", "crypto", "A" * 21, "USDT", True, False),
    ],
)
def test_chart_guard_source_rejects_other_instruments(
    prefix: str, ticker: str, kind: str, base: str, quote: str, standard: bool, allowed: bool
) -> None:
    # These expressions use syntax shared by Pine and Python. Evaluate the actual
    # source with mock metadata; this does not validate Pine types or runtime behavior.
    context = {
        "syminfo": SimpleNamespace(
            prefix=prefix, ticker=ticker, type=kind, basecurrency=base, currency=quote
        ),
        "chart": SimpleNamespace(is_standard=standard),
        "str": StringFunctions,
    }
    for name in ("middlewareSymbol", "binanceSpotSymbol", "middlewareChartOk"):
        context[name] = eval(assignment(name), {"__builtins__": {}}, context)

    assert context["middlewareSymbol"] == ticker.upper()
    assert context["middlewareChartOk"] is allowed


def test_every_alert_path_uses_the_chart_guard() -> None:
    assert "middlewareChartOk" in assignment("allowOrderNow").split(" and ")
    body = function_body("sendMiddlewareAlert")
    assert body.strip() == (
        "if middlewareChartOk\n"
        "        alert(buildPayload(signalCode, signalText, side), alert.freq_all)"
    )
    assert len(re.findall(r"^\s*alert\(", PINE, re.MULTILINE)) == 1
    assert "normalizeTicker(" not in PINE


def test_payload_preserves_v1_clock_symbol_and_fields() -> None:
    body = function_body("buildPayload")
    assert "string symbol = middlewareSymbol" in body
    assert r'payload += "\"schemaVersion\":1,"' in body
    assert r'payload += "\"barTime\":" + str.tostring(timenow) + ","' in body
    assert r'payload += "\"barIndex\":" + str.tostring(bar_index) + ","' in body
    assert r'payload += "\"timeframe\":\"" + timeframe.period + "\","' in body
    assert r'payload += "\"price\":" + str.tostring(close, format.mintick) + ","' in body
    fields = re.findall(r'payload \+= "\\"(\w+)\\":', body)
    assert set(fields) == {
        "schemaVersion",
        "source",
        "symbol",
        "ticker",
        "signalCode",
        "signalText",
        "side",
        "price",
        "timeframe",
        "barTime",
        "barIndex",
        "isRealtime",
    }


def test_preset_daily_and_session_source_contract() -> None:
    assert assignment("presetMode").startswith('input.string("Manuel",')
    assert assignment("requireDailyChart").startswith("input.bool(true,")
    assert assignment("isDailyChart") == "timeframe.isdaily and timeframe.multiplier == 1"
    assert assignment("timeframeOk") == "not requireDailyChart or isDailyChart"
    assert assignment("useOrderSessionFilterInput").startswith("input.bool(true,")
    assert assignment("useOrderSessionFilter") == (
        'presetMode == "BIST Algo" ? true : presetMode == "Kripto 24/7" ? false : '
        "useOrderSessionFilterInput"
    )
    assert assignment("nowTotalMin") == (
        "hour(timenow, syminfo.timezone) * 60 + minute(timenow, syminfo.timezone)"
    )
    for name, value in (
        ("orderStartHour", 17),
        ("orderStartMinute", 45),
        ("orderEndHour", 17),
        ("orderEndMinute", 57),
    ):
        assert assignment(name).startswith(f"input.int({value},")
    assert assignment("orderSessionNowOk") == (
        "not useOrderSessionFilter or (orderStartTotalMin <= orderEndTotalMin ? "
        "(nowTotalMin >= orderStartTotalMin and nowTotalMin <= orderEndTotalMin) : "
        "(nowTotalMin >= orderStartTotalMin or nowTotalMin <= orderEndTotalMin))"
    )


def test_intrabar_and_bar_close_gates_remain_explicit() -> None:
    assert "calc_on_every_tick=true" in PINE
    assert assignment("confirmClose").startswith("input.bool(false,")
    assert assignment("realtimeOnly").startswith("input.bool(true,")
    assert assignment("watchlistIntrabar").startswith("input.bool(true,")
    assert assignment("allowRealtime") == "realtimeOnly ? barstate.isrealtime : true"
    assert assignment("canSignal") == (
        "timeframeOk and (confirmClose ? barstate.isconfirmed : true)"
    )
    assert assignment("allowOrderNow") == (
        "enableStrategyOrders and middlewareChartOk and allowRealtime and orderSessionNowOk "
        "and (watchlistIntrabar ? true : barstate.isconfirmed)"
    )


def test_all_first_modes_preserve_codes_order_and_per_bar_latches() -> None:
    assert assignment("multiSignalMode").startswith('input.string("ALL",')
    assert assignment("allMode") == 'multiSignalMode == "ALL"'
    all_block = PINE.split("if allMode\n", 1)[1].split("// FIRST MODE:", 1)[0]
    first_block = PINE.split("if not allMode and allowOrderNow and not sent_any\n", 1)[1]
    expected = [
        ("h_ucuz", "H_UCZ"),
        ("h_beles", "H_BLS"),
        ("c_ucuz", "C_UCZ"),
        ("c_beles", "C_BLS"),
        ("h_pahali", "H_PAH"),
        ("c_pahali", "C_PAH"),
    ]
    for block in (all_block, first_block):
        calls = re.findall(r'sendMiddlewareAlert\("([A-Z_]+)", "[^\"]+", "(BUY|SELL)"\)', block)
        assert calls == [(code, SIGNAL_SIDE_MAP[code].value) for _, code in expected]
    assert "else if" not in all_block
    assert first_block.count("else if") == 5
    assert first_block.count("sent_any := true") == 6
    reset = PINE.split("if barstate.isnew\n", 1)[1].split("allowRealtime =", 1)[0]
    for condition, _ in expected:
        flag = f"sent_{condition}"
        assert re.search(rf"^varip bool {flag}\s*= false$", PINE, re.MULTILINE)
        assert re.search(rf"^    {flag}\s*:= false$", reset, re.MULTILINE)
        assert f"if allowOrderNow and {condition} and not {flag}" in all_block
        assert f"{flag} := true" in all_block
        assert f"if {condition} and not {flag}" in first_block
    assert re.search(r"^    sent_any\s*:= false$", reset, re.MULTILINE)
