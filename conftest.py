"""Offline test bootstrap, installed before application modules are collected.

Real dotenv files, account settings and SQLite files must never become test inputs.
Missing mocks fail immediately, including requests swallowed by application handlers.
"""

import ast
import gc
import logging
import os
import socket
import sqlite3
import tempfile
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import pytest

REPO_ROOT = Path(__file__).resolve().parent
_sandbox = tempfile.TemporaryDirectory(prefix="rapot-tests-", ignore_cleanup_errors=True)
TEST_ROOT = Path(_sandbox.name).resolve()
_patch = pytest.MonkeyPatch()
_connections: list[sqlite3.Connection] = []
_socketpair_state = threading.local()


def _deny_network(*args: Any, **kwargs: Any) -> Any:
    pytest.fail("External network access is blocked in tests; mock the provider.")


async def _deny_async_network(*args: Any, **kwargs: Any) -> Any:
    _deny_network()


def _isolate_environment() -> None:
    # Inspect field names without importing either settings singleton or reading .env.
    for relative_path, class_name, prefix in (
        ("settings.py", "Settings", ""),
        ("middleware/infra/settings.py", "MiddlewareSettings", "MW_"),
    ):
        tree = ast.parse((REPO_ROOT / relative_path).read_text(encoding="utf-8"))
        fields = {
            prefix + item.target.id.upper()
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == class_name
            for item in node.body
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
        }
        for key in list(os.environ):
            if key.upper() in fields:
                _patch.delenv(key)

    environment = {
        "TELEGRAM_TOKEN": "test-token",
        "TELEGRAM_CHAT_ID": "test-chat",
        "JWT_SECRET_KEY": "test-only-jwt-secret-at-least-32-characters",
        "DATABASE_PATH": str(TEST_ROOT / "collection.sqlite3"),
        "CACHE_DATABASE_PATH": str(TEST_ROOT / "collection-cache.sqlite3"),
        "APP_ENV": "test",
        "AI_ENABLED": "0",
        "RUN_EMBEDDED_BOT": "0",
        "MW_DATABASE_URL": f"sqlite+pysqlite:///{(TEST_ROOT / 'middleware.sqlite3').as_posix()}",
        "MW_WEBHOOK_AUTH_TOKEN": "test-token",
        "MW_APP_ENV": "development",
        "MW_EXECUTION_MODE": "DRY_RUN",
        "MW_TRADING_ENABLED": "false",
        "MW_BINANCE_LIVE_ENABLED": "false",
        "XDG_CACHE_HOME": str(TEST_ROOT / "cache"),
        "TEMP": str(TEST_ROOT),
        "TMP": str(TEST_ROOT),
    }
    for key, value in environment.items():
        _patch.setenv(key, value)
    _patch.setattr(tempfile, "tempdir", str(TEST_ROOT))
    _patch.chdir(TEST_ROOT)


def _block_network() -> None:
    import aiohttp
    import httpx
    import requests
    from curl_cffi import AsyncCurl, Curl

    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_socketpair = socket.socketpair

    def connect(sock: socket.socket, *args: Any, **kwargs: Any) -> Any:
        if getattr(_socketpair_state, "active", False):
            return original_connect(sock, *args, **kwargs)
        return _deny_network()

    def connect_ex(sock: socket.socket, *args: Any, **kwargs: Any) -> Any:
        if getattr(_socketpair_state, "active", False):
            return original_connect_ex(sock, *args, **kwargs)
        return _deny_network()

    def socketpair(*args: Any, **kwargs: Any) -> tuple[socket.socket, socket.socket]:
        # Windows implements asyncio's internal socketpair with loopback TCP.
        _socketpair_state.active = True
        try:
            return original_socketpair(*args, **kwargs)
        finally:
            _socketpair_state.active = False

    _patch.setattr(socket.socket, "connect", connect)
    _patch.setattr(socket.socket, "connect_ex", connect_ex)
    _patch.setattr(socket.socket, "sendto", _deny_network)
    _patch.setattr(socket, "getaddrinfo", _deny_network)
    _patch.setattr(socket, "gethostbyname", _deny_network)
    _patch.setattr(socket, "gethostbyname_ex", _deny_network)
    _patch.setattr(socket, "gethostbyaddr", _deny_network)
    _patch.setattr(socket, "socketpair", socketpair)
    _patch.setattr(requests.sessions.Session, "request", _deny_network)
    _patch.setattr(aiohttp.ClientSession, "_request", _deny_async_network)
    # Custom ASGI/Mock transports still work; only actual HTTP transports are denied.
    _patch.setattr(httpx.HTTPTransport, "handle_request", _deny_network)
    _patch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", _deny_async_network)
    # libcurl bypasses Python sockets (used by yfinance).
    _patch.setattr(Curl, "perform", _deny_network)
    _patch.setattr(AsyncCurl, "add_handle", _deny_network)


def _protect_sqlite() -> None:
    original_connect = sqlite3.connect

    def connect(database: Any, *args: Any, **kwargs: Any) -> sqlite3.Connection:
        name = os.fsdecode(database)
        is_memory = name == ":memory:"
        if name.startswith("file:"):
            name = unquote(name[5:].split("?", 1)[0])
            is_memory = name == ":memory:"
        path = Path(name).resolve()
        # pytest-cov stores its own report database in the repository.
        is_coverage = path.parent == REPO_ROOT and (
            path.name == ".coverage" or path.name.startswith(".coverage.")
        )
        if not is_memory and not path.is_relative_to(TEST_ROOT) and not is_coverage:
            pytest.fail("SQLite access outside the test sandbox is blocked.", pytrace=False)
        connection = original_connect(database, *args, **kwargs)
        _connections.append(connection)
        return connection

    _patch.setattr(sqlite3, "connect", connect)
    _patch.setattr(sqlite3.dbapi2, "connect", connect)


def pytest_configure(config: pytest.Config) -> None:
    # Collection resolves CLI paths against invocation_params.dir, not this temporary cwd.
    # Override basetemp so pytest cannot recursively clear a user-supplied real directory.
    config.option.basetemp = str(TEST_ROOT / "pytest")
    _isolate_environment()
    _block_network()
    _protect_sqlite()
    # yfinance uses platformdirs (including AppData on Windows), independent of cwd.
    import yfinance as yf

    yf.set_tz_cache_location(str(TEST_ROOT / "yfinance"))


@pytest.fixture(autouse=True)
def test_sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Each test gets a separate cwd; collection-time log files stay in TEST_ROOT."""
    monkeypatch.chdir(tmp_path)
    start = len(_connections)
    yield tmp_path
    for connection in _connections[start:]:
        connection.close()
    del _connections[start:]


def pytest_unconfigure(config: pytest.Config) -> None:
    logging.shutdown()
    for connection in _connections:
        connection.close()
    _connections.clear()
    _patch.undo()
    gc.collect()
    _sandbox.cleanup()
