"""Provider HTTP boundaries used by the shared scanner enrichment phase."""

from types import SimpleNamespace

import pandas as pd
import pytest
import requests
import yfinance

import data_loader
import news_manager


def test_bist_rss_uses_explicit_timeout_and_parses_only_response_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = b'<?xml version="1.0"?><rss version="2.0"><channel><title>Test</title><item><title>Offline headline</title><pubDate>Thu, 01 Jan 2026 10:00:00 GMT</pubDate></item></channel></rss>'
    events = []
    parse = news_manager.feedparser.parse

    def get(url: str, *, timeout: int) -> SimpleNamespace:
        assert "THYAO+hisse" in url and timeout == 10
        events.append("get")
        return SimpleNamespace(content=body, raise_for_status=lambda: events.append("status"))

    def parse_bytes(content: bytes):
        assert content is body and isinstance(content, bytes)
        assert events == ["get", "status"]
        events.append("parse")
        return parse(content)

    monkeypatch.setattr(news_manager.requests, "get", get)
    monkeypatch.setattr(news_manager.feedparser, "parse", parse_bytes)
    result = news_manager.get_bist_news("THYAO")
    assert "Offline headline" in result
    assert events == ["get", "status", "parse"]


@pytest.mark.parametrize("failure", ["timeout", "http_error"])
def test_bist_rss_errors_use_existing_fallback_without_parsing(
    monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    def http_error() -> None:
        raise requests.HTTPError("offline HTTP failure")

    def get(_url: str, *, timeout: int) -> SimpleNamespace:
        assert timeout == 10
        if failure == "timeout":
            raise requests.Timeout("offline timeout")
        return SimpleNamespace(content=b"not a successful feed", raise_for_status=http_error)

    def unexpected_parse(*_args, **_kwargs) -> None:
        pytest.fail("failed HTTP responses must never reach the RSS parser")

    monkeypatch.setattr(news_manager.requests, "get", get)
    monkeypatch.setattr(news_manager.feedparser, "parse", unexpected_parse)
    assert news_manager.get_bist_news("THYAO") == "Haber servisine şu anda ulaşılamıyor."


@pytest.mark.parametrize("failure", [None, "timeout", "empty"])
def test_secondary_yfinance_explicit_timeout_keeps_data_or_existing_fallback(
    monkeypatch: pytest.MonkeyPatch, failure: str | None
) -> None:
    monkeypatch.setattr(data_loader, "_bist_yf_failure_cooldown_until", {})
    monkeypatch.setattr(data_loader, "_bist_yf_failure_logged_reason", {})

    def download(*, timeout: int, **kwargs) -> pd.DataFrame:
        assert timeout == 10
        assert kwargs["tickers"] == "THYAO.IS" and kwargs["threads"] is False
        if failure == "timeout":
            raise TimeoutError("offline SDK timeout")
        if failure == "empty":
            return pd.DataFrame()
        return pd.DataFrame(
            {"Open": [10.0], "High": [11.0], "Low": [9.0], "Close": [10.5], "Volume": [1000]},
            index=pd.date_range("2026-01-01", periods=1),
        )

    monkeypatch.setattr(yfinance, "download", download)
    frame = data_loader._fetch_bist_data_yfinance("THYAO")
    if failure:
        assert frame is None
        assert "THYAO" in data_loader._bist_yf_failure_cooldown_until
    else:
        assert frame is not None and frame.iloc[0]["Close"] == 10.5
        assert frame.attrs["source_hint"] == "yfinance_bist"
        assert data_loader.is_dataframe_fresh(frame, 90)
