"""Materialize authorized closed-candle batches for tracker display."""

from __future__ import annotations

import logging
import math
import os
import re
import sqlite3
from contextlib import closing, suppress
from pathlib import Path
from time import time
from typing import Literal
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field

from application.services.bist_share_universe import share_universe
from application.services.custom_indicators.core import pine_rsi
from application.services.rsi_tracker import (
    HISTORY_BARS,
    MAX_TRACKER_SYMBOLS,
    NATIVE_TIMEFRAMES,
    RSI_LENGTH,
    WilderRsi,
)

logger = logging.getLogger(__name__)
SCHEMA_VERSION = 1
FORMULA = "wilder-14-closed-v1"
MAX_SERIES = MAX_TRACKER_SYMBOLS * len(NATIVE_TIMEFRAMES)
MAX_LINE = 16 * 1024
MAX_INPUT = 6 * 1024 * 1024
DISPLAY_SECONDS = 7 * 86400


class HistoryHeader(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    version: Literal[1]
    source: str
    revision: int = Field(gt=0, le=2**63 - 1)


class ClosedSeries(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    market: Literal["BIST", "Kripto"]
    symbol: str
    period: str
    adjustment: Literal["raw", "split", "total_return"]
    complete: Literal[True]
    bars: list[tuple[int, int, float]] = Field(min_length=1, max_length=HISTORY_BARS)

    def summarize(self, now):
        if self.period not in NATIVE_TIMEFRAMES:
            raise ValueError("Unsupported closed-candle period")
        state = WilderRsi(self.bars[0][2])
        previous_end = None
        for start, end, close in self.bars:
            if not (0 < start < end <= now and math.isfinite(close) and close > 0):
                raise ValueError("Invalid closed candle")
            if previous_end is not None:
                if start < previous_end or (self.market == "Kripto" and start != previous_end):
                    raise ValueError("Closed candles overlap or contain a crypto interval gap")
                state = state.add(close)
            previous_end = end
        rsi = pine_rsi(state.gain, state.loss) if state.count == RSI_LENGTH else None
        if rsi is not None and not math.isfinite(rsi):
            raise ValueError("Invalid derived RSI")
        start, end, close = self.bars[-1]
        return (self.market, self.symbol, self.period, self.adjustment, start, end, close, rsi)


def pilot_members(raw: str) -> frozenset[tuple[str, str]]:
    entries = [tuple(value.strip().split(":")) for value in raw.split(",")]
    if not 1 <= len(entries) <= MAX_TRACKER_SYMBOLS or len(set(entries)) != len(entries):
        raise ValueError("Tracker history pilot requires 1–25 unique market/symbol entries")
    bist = set(share_universe().symbols) if any(entry[0] == "BIST" for entry in entries) else set()
    for entry in entries:
        if len(entry) != 2:
            raise ValueError("Invalid tracker history pilot entry")
        market, symbol = entry
        if market == "BIST" and symbol in bist:
            continue
        if market == "Kripto" and re.fullmatch(r"[A-Z0-9]{2,20}USDT", symbol):
            continue
        raise ValueError("Invalid tracker history pilot market or symbol")
    return frozenset(entries)


class TrackerHistory:
    """One bounded, display-only sidecar with an in-memory HTTP read path."""

    def __init__(self, directory: Path, source: str, members: frozenset[tuple[str, str]]):
        if not re.fullmatch(r"[a-z][a-z0-9_-]{1,47}", source):
            raise ValueError("Invalid tracker history source identifier")
        self.path = directory / "rsi-tracker-closed.sqlite3"
        self.inbox = directory / "rsi-tracker-input.jsonl"
        self.source = source
        self.members = members
        self._records = {}
        self._file_version = None
        self._revision = 0

    def _read(self, db):
        meta = db.execute("SELECT source, revision, formula FROM feed WHERE id = 1").fetchone()
        if meta is None or (meta[0], meta[2]) != (self.source, FORMULA):
            return 0, {}
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM closed LIMIT ?", (MAX_SERIES + 1,)).fetchall()
        if len(rows) > MAX_SERIES:
            raise ValueError("Tracker history sidecar exceeds pilot bounds")
        return meta[1], {
            (row["market"], row["symbol"], row["period"]): row
            for row in rows
            if (row["market"], row["symbol"]) in self.members
        }

    def load(self):
        if not self.path.exists():
            return
        location = quote(self.path.resolve().as_posix(), safe="/:")
        with closing(
            sqlite3.connect(
                f"file:{location}?mode=ro", uri=True, timeout=1, check_same_thread=False
            )
        ) as db:
            db.execute("BEGIN")
            if db.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
                raise ValueError("Unsupported tracker history sidecar version")
            self._revision, self._records = self._read(db)

    def refresh(self):
        if not self.inbox.is_file():
            return
        stat = self.inbox.stat()
        file_version = (stat.st_ino, stat.st_size, stat.st_mtime_ns)
        if file_version == self._file_version:
            return
        try:
            self._import_file()
        except ValueError:
            logger.warning(
                "Tracker history batch rejected; last committed close is still available"
            )
        self._file_version = file_version

    def _import_file(self):
        now = int(time())
        records = {}
        with self.inbox.open("rb") as stream:
            if not 0 < os.fstat(stream.fileno()).st_size <= MAX_INPUT:
                raise ValueError("Tracker history input exceeds byte bounds")
            header_line = stream.readline(MAX_LINE + 1)
            if len(header_line) > MAX_LINE:
                raise ValueError("Tracker history header exceeds byte bounds")
            header = HistoryHeader.model_validate_json(header_line)
            if header.source != self.source:
                raise ValueError("Tracker history source differs")
            if header.revision <= self._revision:
                return
            for index in range(MAX_SERIES + 1):
                line = stream.readline(MAX_LINE + 1)
                if not line:
                    break
                if len(line) > MAX_LINE or index == MAX_SERIES:
                    raise ValueError("Tracker history input exceeds series bounds")
                series = ClosedSeries.model_validate_json(line)
                key = (series.market, series.symbol, series.period)
                if key[:2] not in self.members or key in records:
                    raise ValueError("Duplicate or out-of-scope closed series")
                records[key] = series.summarize(now)
        if not records:
            raise ValueError("Tracker history batch contains no series")
        self._commit(header.revision, records, now)

    def _commit(self, revision, records, now):
        with suppress(FileExistsError):
            self.path.touch(mode=0o600, exist_ok=False)
        with closing(sqlite3.connect(self.path, timeout=1, check_same_thread=False)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version == 0:
                db.execute(
                    "CREATE TABLE feed (id INTEGER PRIMARY KEY, source TEXT, revision INTEGER, formula TEXT)"
                )
                db.execute("""CREATE TABLE closed (
                    market TEXT, symbol TEXT, period TEXT, adjustment TEXT, bar_time INTEGER,
                    bar_end INTEGER, price REAL, rsi REAL, received_at INTEGER,
                    PRIMARY KEY (market, symbol, period)
                ) WITHOUT ROWID""")
                db.execute("PRAGMA user_version = 1")
            elif version != SCHEMA_VERSION:
                raise ValueError("Unsupported tracker history sidecar version")
            current, previous = self._read(db)
            if revision > current:
                effective = {key: tuple(row) for key, row in previous.items()}
                for key, item in records.items():
                    prior = previous.get(key)
                    adjustment, _, end, _, rsi = item[3:]
                    if prior and (
                        end < prior["bar_end"]
                        or (
                            rsi is None
                            and prior["rsi"] is not None
                            and adjustment == prior["adjustment"]
                        )
                    ):
                        continue
                    effective[key] = (*item, now)
                db.execute("DELETE FROM closed")
                db.executemany(
                    "INSERT INTO closed VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", effective.values()
                )
                db.execute(
                    "INSERT OR REPLACE INTO feed VALUES (1, ?, ?, ?)",
                    (self.source, revision, FORMULA),
                )
            published = self._read(db)
        self._revision, self._records = published

    def enrich(self, snapshot, market):
        now = snapshot["observed_at"]
        records = self._records
        for symbol, row in snapshot["rows"].items():
            for period, cell in row["cells"].items():
                record = records.get((market, symbol, period))
                if record is None or not 0 <= now - record["received_at"] <= DISPLAY_SECONDS:
                    continue
                last = cell.get("last")
                if (
                    cell["value"] is None
                    and record["rsi"] is not None
                    and (last is None or last["bar_time"] <= record["bar_time"])
                ):
                    cell["last"] = {
                        "value": record["rsi"],
                        "kind": "closed",
                        "bar_time": record["bar_time"],
                        "bar_end": record["bar_end"],
                        "received_at": record["received_at"],
                        "source": self.source,
                        "formula": FORMULA,
                        "adjustment": record["adjustment"],
                    }
                    snapshot["closed_source"] = self.source
                elif cell["value"] is None and last is None and record["rsi"] is None:
                    cell["closed_status"] = "insufficient"
                    cell["closed_source"] = self.source
                price = row.get("last_price")
                if (
                    row["price"] is None
                    and record["adjustment"] == "raw"
                    and (price is None or price["source_time"] < record["bar_end"])
                ):
                    row["last_price"] = {
                        "value": record["price"],
                        "source_time": record["bar_end"],
                        "received_at": record["received_at"],
                        "source": self.source,
                        "kind": "closed",
                    }
                    snapshot["closed_source"] = self.source
        return snapshot
