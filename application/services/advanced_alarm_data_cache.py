"""Bounded, separate market cache. Never opens the application's trading database."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import threading
from pathlib import Path

MAX_BARS = 500
MAX_CACHE_BYTES = 128 * 1024 * 1024
DISK_RESERVE = 530 * 1024 * 1024


class MarketCache:
    def __init__(self, path: Path, *, reserve: int = DISK_RESERVE):
        self.path = path
        self.reserve = reserve
        self._lock = threading.RLock()
        self._connection: sqlite3.Connection | None = None

    def _open(self) -> sqlite3.Connection:
        if self._connection is not None:
            return self._connection
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.path.is_symlink() or any(parent.is_symlink() for parent in self.path.parents):
            raise ValueError("Veri önbelleği sembolik bağlantı olamaz.")
        if shutil.disk_usage(self.path.parent).free < self.reserve:
            raise OSError("Veri önbelleği için disk rezervi yetersiz.")
        connection = sqlite3.connect(self.path, timeout=2, check_same_thread=False)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA journal_size_limit=2097152")
        connection.execute("PRAGMA wal_autocheckpoint=128")
        page_size = connection.execute("PRAGMA page_size").fetchone()[0]
        connection.execute(f"PRAGMA max_page_count={MAX_CACHE_BYTES // page_size}")
        connection.executescript(
            "CREATE TABLE IF NOT EXISTS market_series ("
            "key TEXT PRIMARY KEY, payload TEXT NOT NULL, received REAL NOT NULL);"
            "CREATE TABLE IF NOT EXISTS market_universe ("
            "id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL);"
        )
        connection.commit()
        if os.name != "nt":
            self.path.chmod(0o600)
        self._connection = connection
        return connection

    def load_universe(self) -> list[str]:
        with self._lock:
            row = self._open().execute("SELECT payload FROM market_universe WHERE id=1").fetchone()
            return json.loads(row[0]) if row else []

    def save_universe(self, symbols: list[str]) -> None:
        with self._lock:
            connection = self._open()
            connection.execute(
                "INSERT OR REPLACE INTO market_universe VALUES(1,?)", (json.dumps(symbols),)
            )
            connection.commit()

    def save(self, key: str, candles: list[dict], received: float) -> None:
        # Column names are stored once. Avoid repeating six JSON keys for every
        # minute of every security; this remains provider OHLCV, not quote bars.
        columns = ["time", "open", "high", "low", "close", "volume"]
        packed = {
            "columns": columns,
            "rows": [[row.get(column) for column in columns] for row in candles[-MAX_BARS:]],
        }
        payload = json.dumps(packed, allow_nan=False, separators=(",", ":"))
        with self._lock:
            connection = self._open()
            if shutil.disk_usage(self.path.parent).free < self.reserve:
                raise OSError("Veri önbelleği disk rezervine ulaştı.")
            # 2000 all-market minute series plus bounded active native timeframes.
            count = connection.execute("SELECT COUNT(*) FROM market_series").fetchone()[0]
            if (
                count >= 4096
                and not connection.execute(
                    "SELECT 1 FROM market_series WHERE key=?", (key,)
                ).fetchone()
            ):
                raise OSError("Kalıcı seri kapasitesine ulaşıldı.")
            try:
                connection.execute(
                    "INSERT OR REPLACE INTO market_series VALUES(?,?,?)", (key, payload, received)
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def load(self, key: str) -> tuple[list[dict], float] | None:
        with self._lock:
            row = (
                self._open()
                .execute("SELECT payload,received FROM market_series WHERE key=?", (key,))
                .fetchone()
            )
            if not row:
                return None
            payload = json.loads(row[0])
            candles = [
                dict(zip(payload["columns"], values, strict=True)) for values in payload["rows"]
            ]
            return candles, row[1]

    def size(self) -> int:
        return sum(
            path.stat().st_size
            for path in (self.path, Path(f"{self.path}-wal"), Path(f"{self.path}-shm"))
            if path.exists()
        )

    def close(self) -> None:
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None
