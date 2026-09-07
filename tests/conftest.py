"""
Test fixtures ve paylaşılan test yardımcıları.
"""

import sys
import threading
from collections.abc import Iterator
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def isolated_core_databases(test_sandbox: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Reset core DB/cache singletons so tests never share persisted application state."""
    import database
    import db_session
    import price_cache
    from api.rate_limit import limiter
    from settings import get_settings, settings

    limiter.reset()

    db_path = test_sandbox / "trading_bot.sqlite3"
    cache_path = test_sandbox / "price_cache.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("CACHE_DATABASE_PATH", str(cache_path))
    monkeypatch.setattr(settings, "database_path", str(db_path))
    monkeypatch.setattr(settings, "database_url", None)
    monkeypatch.setattr(settings, "cache_database_path", str(cache_path))
    monkeypatch.setattr(db_session, "_engine", None)
    monkeypatch.setattr(db_session, "_SessionFactory", None)
    monkeypatch.setattr(db_session, "_ScopedSession", None)
    monkeypatch.setattr(database, "DB_PATH", db_path)
    monkeypatch.setattr(database.db, "_local", threading.local())
    monkeypatch.setattr(price_cache, "CACHE_DB_PATH", cache_path)
    monkeypatch.setattr(price_cache.price_cache, "_stats", {"hits": 0, "misses": 0})
    api_module = sys.modules.get("api.main")
    if api_module is not None:
        monkeypatch.setattr(api_module, "_market_data_provider", None)
        monkeypatch.setattr(api_module, "_market_overview_cache", None)
        monkeypatch.setattr(api_module, "_market_ticker_cache", None)
        monkeypatch.setattr(api_module, "_market_index_cache", {})
        monkeypatch.setattr(api_module, "_RUNTIME_STATE", deepcopy(api_module._RUNTIME_STATE))
    db_session.init_db()
    database.db._init_database()
    price_cache.price_cache._init_database()
    try:
        yield
    finally:
        if db_session._ScopedSession is not None:
            db_session._ScopedSession.remove()
        if db_session._engine is not None:
            db_session._engine.dispose()
        get_settings.cache_clear()


@pytest.fixture
def api_auth_users(monkeypatch: pytest.MonkeyPatch):
    """Use the auth module captured by the routes, even after auth reload tests."""
    import hashlib

    from api.routes import auth_routes

    users = {
        name: {
            "username": name,
            "hashed_password": hashlib.sha256(b"test-password").hexdigest(),
            "is_admin": name == "admin",
            "disabled": name == "disabled",
        }
        for name in ("admin", "user", "disabled")
    }
    monkeypatch.setitem(auth_routes.authenticate_user.__globals__, "USERS_DB", users)
    return auth_routes


@pytest.fixture
def authenticated_api_client(api_auth_users) -> Iterator:
    from fastapi.testclient import TestClient

    import api.main as api_main

    token = api_auth_users.create_access_token({"sub": "user"})
    client = TestClient(api_main.app, headers={"Authorization": f"Bearer {token}"})
    try:
        yield client
    finally:
        client.close()


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
