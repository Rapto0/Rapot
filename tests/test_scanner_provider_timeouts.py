"""Explicit legacy data-provider HTTP timeout contract, independent of bot scans."""

import pandas as pd
import pytest
import yfinance

import data_loader


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
