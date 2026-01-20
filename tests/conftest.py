"""
Test fixtures ve paylaşılan test yardımcıları.
"""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_ohlcv_data() -> pd.DataFrame:
    """
    Test için örnek OHLCV verisi oluşturur.
    60 günlük rastgele veri.
    """
    np.random.seed(42)  # Tekrarlanabilirlik için
    dates = pd.date_range(end=datetime.now(), periods=60, freq="D")

    base_price = 100
    returns = np.random.randn(60) * 0.02  # %2 volatilite
    prices = base_price * np.exp(np.cumsum(returns))

    df = pd.DataFrame(
        {
            "Open": prices * (1 + np.random.randn(60) * 0.005),
            "High": prices * (1 + np.abs(np.random.randn(60) * 0.01)),
            "Low": prices * (1 - np.abs(np.random.randn(60) * 0.01)),
            "Close": prices,
            "Volume": np.random.randint(100000, 1000000, 60),
        },
        index=dates,
    )

    return df


@pytest.fixture
def bullish_ohlcv_data() -> pd.DataFrame:
    """
    Yükseliş trendinde örnek OHLCV verisi.
    RSI düşük, MACD negatiften pozitife geçiyor.
    """
    dates = pd.date_range(end=datetime.now(), periods=60, freq="D")

    # Sürekli yükselen fiyat
    base_price = 100
    trend = np.linspace(0, 0.3, 60)  # %30 yükseliş
    prices = base_price * (1 + trend)

    df = pd.DataFrame(
        {
            "Open": prices * 0.99,
            "High": prices * 1.01,
            "Low": prices * 0.98,
            "Close": prices,
            "Volume": np.random.randint(100000, 1000000, 60),
        },
        index=dates,
    )

    return df


@pytest.fixture
def bearish_ohlcv_data() -> pd.DataFrame:
    """
    Düşüş trendinde örnek OHLCV verisi.
    RSI yüksek, MACD pozitiften negatife geçiyor.
    """
    dates = pd.date_range(end=datetime.now(), periods=60, freq="D")

    # Sürekli düşen fiyat
    base_price = 100
    trend = np.linspace(0, -0.3, 60)  # %30 düşüş
    prices = base_price * (1 + trend)

    df = pd.DataFrame(
        {
            "Open": prices * 1.01,
            "High": prices * 1.02,
            "Low": prices * 0.99,
            "Close": prices,
            "Volume": np.random.randint(100000, 1000000, 60),
        },
        index=dates,
    )

    return df


@pytest.fixture
def insufficient_data() -> pd.DataFrame:
    """Yetersiz veri (10 gün) - sinyal hesaplanamaz."""
    dates = pd.date_range(end=datetime.now(), periods=10, freq="D")

    df = pd.DataFrame(
        {
            "Open": [100] * 10,
            "High": [101] * 10,
            "Low": [99] * 10,
            "Close": [100] * 10,
            "Volume": [100000] * 10,
        },
        index=dates,
    )

    return df


@pytest.fixture
def empty_dataframe() -> pd.DataFrame:
    """Boş DataFrame."""
    return pd.DataFrame()
