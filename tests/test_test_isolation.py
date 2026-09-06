"""Regression checks for the offline test boundary (never use real endpoints or data)."""

import socket
import sqlite3
from contextlib import closing
from pathlib import Path

import httpx
import pytest
import requests
from curl_cffi import Curl, CurlOpt


def test_settings_do_not_load_checkout_dotenv(test_sandbox: Path) -> None:
    from middleware.infra.settings import MiddlewareSettings
    from settings import Settings

    core = Settings()
    middleware = MiddlewareSettings()
    assert core.telegram_token == "test-token"
    assert core.binance_api_key == ""
    assert not core.gemini_api_key
    assert not core.ai_enabled
    assert Path(core.database_path).parent == test_sandbox
    assert not middleware.trading_enabled
    assert not middleware.binance_api_key
    assert middleware.execution_mode.value == "DRY_RUN"


def test_checkout_database_access_is_rejected() -> None:
    checkout_db = Path(__file__).resolve().parents[1] / "trading_bot.db"
    with pytest.raises(pytest.fail.Exception, match="outside the test sandbox"):
        sqlite3.connect(checkout_db)


@pytest.mark.parametrize("case", ["first", "second"])
def test_database_and_price_cache_start_empty(case: str, test_sandbox: Path) -> None:
    import database
    import price_cache
    from db_session import get_engine

    assert database.DB_PATH.parent == test_sandbox
    assert price_cache.CACHE_DB_PATH.parent == test_sandbox
    assert Path(get_engine().url.database).parent == test_sandbox
    with database.db.get_cursor() as cursor:
        assert cursor.execute("SELECT COUNT(*) FROM signals").fetchone()[0] == 0
        cursor.execute(
            "INSERT INTO signals (symbol, market_type, strategy, signal_type, timeframe) "
            "VALUES (?, 'BIST', 'COMBO', 'AL', '1D')",
            (case,),
        )
    with price_cache.price_cache._get_cursor() as cursor:
        assert cursor.execute("SELECT COUNT(*) FROM price_cache").fetchone()[0] == 0
        cursor.execute(
            "INSERT INTO price_cache (symbol, market_type, data_json, expires_at) "
            "VALUES (?, 'BIST', '[]', '2100-01-01')",
            (case,),
        )


@pytest.mark.parametrize("client", ["requests", "httpx", "curl", "socket", "dns"])
def test_unmocked_network_fails_before_io(client: str) -> None:
    with pytest.raises(pytest.fail.Exception, match="External network access"):
        if client == "requests":
            requests.get("https://example.invalid")
        elif client == "httpx":
            with httpx.Client() as http:
                http.get("https://example.invalid")
        elif client == "curl":
            with closing(Curl()) as curl:
                curl.setopt(CurlOpt.URL, b"https://example.invalid")
                curl.perform()
        elif client == "socket":
            with socket.socket() as sock:
                sock.connect(("127.0.0.1", 1))
        else:
            socket.getaddrinfo("example.invalid", 443)


@pytest.mark.asyncio
async def test_async_network_is_blocked() -> None:
    import aiohttp

    async with httpx.AsyncClient() as http:
        with pytest.raises(pytest.fail.Exception, match="External network access"):
            await http.get("https://example.invalid")
    async with aiohttp.ClientSession() as http:
        with pytest.raises(pytest.fail.Exception, match="External network access"):
            await http.get("https://example.invalid")


def test_mock_transport_remains_usable() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json={"offline": True}))
    with httpx.Client(transport=transport) as http:
        assert http.get("https://example.invalid").json() == {"offline": True}
