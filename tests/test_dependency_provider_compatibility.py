"""Exercise real SDK parsing and tabular export after dependency changes, offline."""

from io import BytesIO, StringIO
from types import SimpleNamespace

import pandas as pd
import pytest
from yfinance.data import YfData

import data_loader


def test_real_yahoo_history_parser_preserves_bist_ohlcv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mock only Yahoo transport; keep Ticker, curl session and download parsing real."""
    monkeypatch.setattr(data_loader, "_bist_yf_failure_cooldown_until", {})
    monkeypatch.setattr(data_loader, "_bist_yf_failure_logged_reason", {})
    dates = pd.date_range("2026-01-05 10:00", periods=2, tz="Europe/Istanbul")
    payload = {
        "chart": {
            "error": None,
            "result": [
                {
                    "meta": {
                        "symbol": "THYAO.IS",
                        "exchangeTimezoneName": "Europe/Istanbul",
                        "instrumentType": "EQUITY",
                        "currency": "TRY",
                        "validRanges": ["1d", "1mo"],
                    },
                    "timestamp": [int(date.timestamp()) for date in dates],
                    "indicators": {
                        "quote": [
                            {
                                "open": [100.0, 102.0],
                                "high": [103.0, 105.0],
                                "low": [99.0, 101.0],
                                "close": [102.0, 104.0],
                                "volume": [1000, 2000],
                            }
                        ],
                        "adjclose": [{"adjclose": [102.0, 104.0]}],
                    },
                }
            ],
        }
    }
    requests = []

    def get(_self, *, url: str, params: dict, timeout: int):
        assert url.endswith("/v8/finance/chart/THYAO.IS")
        assert timeout == 10
        requests.append(params)
        return SimpleNamespace(text="offline Yahoo chart response", json=lambda: payload)

    monkeypatch.setattr(YfData, "get", get)
    monkeypatch.setattr(YfData, "cache_get", get)
    frame = data_loader._fetch_bist_data_yfinance("THYAO", "01-01-2026")

    assert frame is not None
    assert frame[["Open", "High", "Low", "Close", "Volume"]].values.tolist() == [
        [100, 103, 99, 102, 1000],
        [102, 105, 101, 104, 2000],
    ]
    assert frame.index.strftime("%Y-%m-%d").tolist() == ["2026-01-05", "2026-01-06"]
    assert frame.attrs["source_hint"] == "yfinance_bist"
    assert data_loader.is_dataframe_fresh(frame, 90)
    assert any("period1" in params and params["interval"] == "1d" for params in requests)


def test_plain_excel_export_round_trip_without_optional_image_or_arrow_packages() -> None:
    frame = pd.DataFrame({"symbol": ["THYAO", "BTCUSDT"], "close": [100.5, 60000.25]})
    buffer = BytesIO()
    frame.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)
    pd.testing.assert_frame_equal(pd.read_excel(buffer, engine="openpyxl"), frame)


def test_html_table_parser_remains_available_for_optional_yahoo_tables() -> None:
    tables = pd.read_html(
        StringIO(
            "<table><tr><th>Symbol</th><th>Close</th></tr>"
            "<tr><td>THYAO</td><td>100.5</td></tr></table>"
        ),
        flavor="lxml",
    )
    assert len(tables) == 1
    assert tables[0].to_dict("records") == [{"Symbol": "THYAO", "Close": 100.5}]
