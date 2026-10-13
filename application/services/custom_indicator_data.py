"""Bounded server-owned data and shared calculations for imported Pine indicators.

HTTP previews and alarm snapshots only read memory / register demand. One fixed
worker owns authenticated native history and pure calculation. Native provider
timestamps are never resampled into invented multi-day or weekly buckets.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from application.services.custom_indicators.core import Bar

MAX_NATIVE_SERIES = 64
MAX_NATIVE_ROWS = 60000
MAX_RESULTS = 4096
MAX_RESULT_POINTS = 128
MAX_RESULT_CELLS = 120000
MAX_PREVIEW_CELLS = 32768
MAX_PREVIEWS = 32
MAX_CONFIGS = 256
MAX_HISTORY_SUMMARIES = 8192
PREVIEW_SECONDS = 120
REFRESH_SECONDS = 30
STALE_SECONDS = 180


def custom_configuration_ids(condition, timeframe):
    """Distinct calculation identities; outputs and visual settings share work."""
    from application.services.advanced_alarm_conditions import condition_fields
    from application.services.custom_indicators.catalog import config_key

    return {
        config_key(ref["indicator"], dict(ref["inputs"]), ref["timeframe"])
        for ref in condition_fields(condition, timeframe)
        if ref["field"] == "custom"
    }


def _iso(value):
    return datetime.fromtimestamp(value, UTC).isoformat().replace("+00:00", "Z") if value else None


def _digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _symbol(symbol, market):
    pattern = r"[A-Z0-9]{1,20}" if market == "BIST" else r"[A-Z0-9]{2,20}USDT"
    if (
        market not in {"BIST", "Kripto"}
        or not isinstance(symbol, str)
        or not re.fullmatch(pattern, symbol)
    ):
        raise ValueError("Özel gösterge sembolü geçersiz.")


def _duration(timeframe):
    match = re.fullmatch(r"([1-9][0-9]*)([SDWM]?)", timeframe)
    if not match:
        raise ValueError("Native zaman dilimi geçersiz.")
    return int(match[1]) * {"S": 1, "": 60, "D": 86400, "W": 604800, "M": 2678400}[match[2]]


def _crypto_end(stamp, timeframe):
    if timeframe.endswith("M"):
        value = datetime.fromtimestamp(stamp, UTC)
        month = value.month - 1 + int(timeframe[:-1])
        return value.replace(year=value.year + month // 12, month=month % 12 + 1, day=1).timestamp()
    return stamp + _duration(timeframe)


def _bist_daily_end(stamp, metadata):
    """Use provider session hours and dated corrections; unsupported syntax is unknown.

    No static Istanbul close hour or holiday calendar is supplied by this module.
    Daily rows already witness a trading day; session metadata supplies its end.
    """
    timezone = metadata.get("timezone")
    if timezone != "Europe/Istanbul":
        return None
    local = datetime.fromtimestamp(stamp, ZoneInfo(timezone))
    date = local.strftime("%Y%m%d")
    holidays = metadata.get("session_holidays", "")
    if holidays and not re.fullmatch(r"\d{8}(?:,\d{8})*", holidays):
        return None
    if date in holidays.split(","):
        return None
    session = metadata.get("session_regular") or metadata.get("session") or ""
    corrections = metadata.get("corrections", "")
    if corrections:
        for correction in corrections.split(";"):
            match = re.fullmatch(r"(\d{4}-\d{4}|F):(\d{8}(?:,\d{8})*)", correction)
            if not match:
                return None
            if date in match[2].split(","):
                session = match[1]
    match = re.fullmatch(r"([0-2]\d[0-5]\d)-([0-2]\d[0-5]\d)(?::([1-7]+))?", session)
    if not match:
        return None
    start, end = (
        int(match[1][:2]) * 60 + int(match[1][2:]),
        int(match[2][:2]) * 60 + int(match[2][2:]),
    )
    if not 0 <= start < end <= 1440:
        return None
    # TradingView session weekdays are Sunday=1, Monday=2, ..., Saturday=7.
    weekday = str((local.weekday() + 1) % 7 + 1)
    if match[3] and weekday not in match[3]:
        return None
    finish = local.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(minutes=end)
    return finish.timestamp() if finish.timestamp() > stamp else None


def native_bars(frame, timeframe, market, now):
    """Validate provider-native OHLC without manufacturing volume or bar boundaries."""
    from infrastructure.providers.custom_indicator_history import MAX_NATIVE_BARS

    if frame.attrs.get("native_timeframe") != timeframe or not 1 < len(frame) <= MAX_NATIVE_BARS:
        raise ValueError("Native mum periyodu veya boyutu uyuşmuyor.")
    index = frame.index
    if (
        index.tz is None
        or index.hasnans
        or not index.is_unique
        or not index.is_monotonic_increasing
    ):
        raise ValueError("Native mum zamanları doğrulanamadı.")
    metadata = frame.attrs.get("session_metadata", {})
    points = []
    for stamp, row in zip(index, frame[["Open", "High", "Low", "Close"]].to_numpy(), strict=True):
        timestamp = stamp.timestamp()
        op, hi, lo, cl = (float(item) for item in row)
        if (
            not all(math.isfinite(item) and item > 0 for item in (op, hi, lo, cl))
            or hi < max(op, lo, cl)
            or lo > min(op, hi, cl)
            or timestamp > now + 5
        ):
            raise ValueError("Native mum fiyat/zaman verisi geçersiz.")
        end = (
            _crypto_end(timestamp, timeframe)
            if market == "Kripto"
            else _bist_daily_end(timestamp, metadata)
            if timeframe == "1D"
            else None
        )
        if market == "BIST" and not timeframe.endswith(("D", "W", "M")):
            session_end = _bist_daily_end(timestamp, metadata)
            end = min(timestamp + _duration(timeframe), session_end) if session_end else None
        points.append(Bar(timestamp, end, op, hi, lo, cl, bool(end and end <= now)))
    if market == "Kripto" and any(
        previous.end != current.time for previous, current in zip(points, points[1:])
    ):
        raise ValueError("Native kripto mum dizisinde boşluk veya örtüşme var.")
    return tuple(points)


def with_native_ends(bars, daily, timeframe, market, now):
    if market != "BIST" or not timeframe.endswith(("D", "W", "M")) or timeframe == "1D":
        return bars
    result = []
    for index, bar in enumerate(bars):
        following = bars[index + 1].time if index + 1 < len(bars) else None
        # Only a following provider bucket witnesses the historical boundary.
        eligible = [day for day in daily if following and bar.time <= day.time < following]
        end = eligible[-1].end if eligible else None
        result.append(replace(bar, end=end, confirmed=bool(following and following <= now)))
    return tuple(result)


@dataclass(frozen=True, slots=True)
class Native:
    bars: tuple[Bar, ...]
    received: float
    requested: int
    digest: str
    epoch: int


_HASH_MODULUS = 2**255 - 19
_HASH_BASE = 65537


def _record_hash(bar):
    return (
        int(_digest([bar.time, bar.end, bar.open, bar.high, bar.low, bar.close]), 16)
        % _HASH_MODULUS
    )


def _rolling_hash(values):
    result = 0
    for value in values:
        result = (result * _HASH_BASE + value) % _HASH_MODULUS
    return result


@dataclass(frozen=True, slots=True)
class HistorySummary:
    """Constant-size historical continuity proof across raw-cache eviction.

    Drop at most three witnessed oldest rows in a normally advancing window.
    Larger gaps, added history or changed older OHLC reset continuity. Hashes
    include native timestamps and session ends but not receipt/finality flags.
    """

    count: int
    first: float
    last: float
    heads: tuple[tuple[float, int], ...]
    historical_digest: int
    received: float

    @classmethod
    def build(cls, bars, now):
        hashes = tuple(_record_hash(bar) for bar in bars)
        return cls(
            len(bars),
            bars[0].time,
            bars[-1].time,
            tuple((bar.time, value) for bar, value in zip(bars[:4], hashes[:4], strict=True)),
            _rolling_hash(hashes[:-1]),
            now,
        )

    def continues(self, bars, now):
        if (
            now - self.received > STALE_SECONDS
            or bars[-1].time < self.last
            or bars[0].time < self.first
        ):
            return False
        positions = [i for i, (stamp, _) in enumerate(self.heads) if stamp == bars[0].time]
        if not positions:
            return False
        removed = positions[0]
        expected = self.historical_digest
        for index, (_, value) in enumerate(self.heads[:removed]):
            expected = (
                expected - value * pow(_HASH_BASE, self.count - 2 - index, _HASH_MODULUS)
            ) % _HASH_MODULUS
        overlap = [bar for bar in bars if bars[0].time <= bar.time < self.last]
        return (
            len(overlap) == self.count - 1 - removed
            and _rolling_hash(_record_hash(bar) for bar in overlap) == expected
        )


class CustomIndicatorData:
    def __init__(self, *, provider=None, clock=None):
        self._provider = provider
        self._clock = clock or time.time
        self._lock = threading.RLock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread = None
        self._configs = {}
        self._blocked_configurations = 0
        self._memberships = []
        self._universe = ()
        self._cursor = (0, 0)
        self._previews = OrderedDict()
        self._native = OrderedDict()
        self._history_summaries = OrderedDict()
        self._results = OrderedDict()
        self._preview_results = OrderedDict()
        self._errors = {}
        self._symbol_epochs = {}
        self._process_epoch = uuid.uuid4().hex
        self._epoch = None
        self._generation = 0
        self._running = False
        self._last_error = None
        self._jobs_requested = 0
        self._turn = 0
        self._last_completed_at = None
        self._last_cycle_seconds = None

    @property
    def provider(self):
        if self._provider is None:
            from application.services.borsapy_gateway import get_borsapy_gateway

            self._provider = get_borsapy_gateway()
        return self._provider

    @staticmethod
    def _config(indicator, inputs, chart_timeframe):
        from application.services.custom_indicators.catalog import (
            canonical_timeframe,
            config_key,
            requirements,
            validate_config,
        )

        timeframe = canonical_timeframe(chart_timeframe)
        inputs = validate_config(indicator, dict(inputs), chart_timeframe=timeframe)
        config = {"indicator": indicator, "inputs": inputs, "chart_timeframe": timeframe}
        identity = config_key(indicator, inputs, timeframe)
        config["requirements"] = requirements(indicator, inputs, timeframe)
        return identity, config

    def configure(self, rules, *, universe=()):
        from application.services.advanced_alarm_conditions import condition_fields

        configs, memberships, blocked = {}, {}, set()
        for rule in rules:
            if not rule.get("enabled", True):
                continue
            for ref in condition_fields(rule["condition"], rule["timeframe"]):
                if ref["field"] != "custom":
                    continue
                identity, config = self._config(ref["indicator"], ref["inputs"], ref["timeframe"])
                if identity not in configs and len(configs) >= MAX_CONFIGS:
                    blocked.add(identity)
                    continue
                configs[identity] = config
                target = memberships.setdefault(identity, {"symbols": set(), "all_bist": False})
                target["all_bist"] |= rule.get("scope") == "all_bist"
                target["symbols"].update(
                    (item["market_type"], item["symbol"]) for item in rule.get("symbols", [])
                )
        with self._lock:
            self._configs = configs
            self._blocked_configurations = len(blocked)
            self._memberships = [
                (identity, tuple(sorted(value["symbols"])), value["all_bist"])
                for identity, value in memberships.items()
            ]
            self._universe = tuple(("BIST", item["symbol"]) for item in universe)
            self._cursor = (0, 0)
            self._generation += 1
            self._refresh_count()
            retained = set(configs) | {key[2] for key in self._previews}
            for key in list(self._results):
                if key[2] not in retained:
                    self._results.pop(key)
            if not self._memberships and not self._previews:
                self._native.clear()
                self._errors.clear()
                self._preview_results.clear()
        self._wake.set()

    def set_universe(self, universe):
        with self._lock:
            self._universe = tuple(("BIST", item["symbol"]) for item in universe)
            self._refresh_count()

    def _refresh_count(self):
        self._jobs_requested = sum(
            len(set(symbols) | (set(self._universe) if all_bist else set()))
            for _, symbols, all_bist in self._memberships
        )

    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._loop, name="custom-indicator-data", daemon=True
            )
            self._thread.start()

    def stop(self):
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join()
        with self._lock:
            self._thread = None
            self._running = False
            self._native.clear()
            self._results.clear()
            self._preview_results.clear()

    def invalidate(self):
        with self._lock:
            self._generation += 1
            self._process_epoch = uuid.uuid4().hex
            self._native.clear()
            self._results.clear()
            self._preview_results.clear()
            self._errors.clear()
            self._symbol_epochs.clear()
            self._history_summaries.clear()
        self._wake.set()

    def _next_job(self):
        now = self._clock()
        with self._lock:
            self._previews = OrderedDict(
                (key, value) for key, value in self._previews.items() if value[0] > now
            )
            for key in list(self._preview_results):
                if key not in self._previews:
                    self._preview_results.pop(key)
            if not self._memberships and not self._previews:
                self._native.clear()
                self._results.clear()
                self._history_summaries.clear()
                self._symbol_epochs.clear()
                return None
            self._turn += 1
            preview_job = None
            for key, (_, config) in self._previews.items():
                cached = self._preview_results.get(key)
                if not cached or now - cached["received"] >= REFRESH_SECONDS:
                    preview_job = key, config, self._generation
                    break
            if preview_job and (not self._memberships or self._turn % 4 == 0):
                return preview_job
            if not self._memberships:
                return preview_job
            ri, si = self._cursor
            for _ in range(len(self._memberships)):
                ri %= len(self._memberships)
                identity, symbols, all_bist = self._memberships[ri]
                selected = tuple(
                    sorted(set(symbols) | (set(self._universe) if all_bist else set()))
                )
                if selected:
                    si %= len(selected)
                    market, symbol = selected[si]
                    self._cursor = (
                        (ri, si + 1)
                        if si + 1 < len(selected)
                        else ((ri + 1) % len(self._memberships), 0)
                    )
                    key = (market, symbol, identity)
                    cached = self._results.get(key)
                    if not cached or now - cached["received"] >= REFRESH_SECONDS:
                        return key, self._configs[identity], self._generation
                    # A worker turn remains bounded even for thousands of symbols.
                    return preview_job
                ri, si = ri + 1, 0
            return preview_job

    def _loop(self):
        while not self._stop.is_set():
            job = self._next_job()
            if job:
                self.process(*job)
                self._stop.wait(0.05)
            else:
                self._wake.wait(0.5)
                self._wake.clear()

    def _native_frame(self, market, symbol, timeframe, bars, epoch):
        key, now = (market, symbol, timeframe), self._clock()
        with self._lock:
            if self._stop.is_set():
                raise ValueError("Özel gösterge veri servisi durduruldu.")
            old = self._native.get(key)
            if (
                old
                and old.epoch == epoch
                and old.requested >= bars
                and now - old.received < REFRESH_SECONDS
            ):
                self._native.move_to_end(key)
                return old
        frame = self.provider.custom_indicator_history(
            symbol,
            exchange="BIST" if market == "BIST" else "BINANCE",
            timeframe=timeframe,
            bars=bars,
        )
        points = native_bars(frame, timeframe, market, self._clock())
        digest = _digest(
            [[bar.time, bar.end, bar.open, bar.high, bar.low, bar.close] for bar in points]
        )
        entry = Native(points, self._clock(), bars, digest, epoch)
        with self._lock:
            if self._stop.is_set() or self.provider.memory_epoch() != epoch:
                raise ValueError("Hesap değişti; yeni native geçmiş bekleniyor.")
            summary = self._history_summaries.get(key)
            revision = bool(summary and not summary.continues(points, entry.received))
            if summary and market == "BIST" and not timeframe.endswith(("D", "W", "M")):
                revision |= any(
                    right.time > summary.last
                    and datetime.fromtimestamp(left.time, ZoneInfo("Europe/Istanbul")).date()
                    == datetime.fromtimestamp(right.time, ZoneInfo("Europe/Istanbul")).date()
                    and right.time - left.time != _duration(timeframe)
                    for left, right in zip(points, points[1:])
                )
            if revision:
                member = (market, symbol)
                self._symbol_epochs[member] = self._symbol_epochs.get(member, 0) + 1
                for result_key in list(self._results):
                    if result_key[:2] == member:
                        self._results.pop(result_key)
            self._native[key] = entry
            self._history_summaries[key] = HistorySummary.build(points, entry.received)
            self._history_summaries.move_to_end(key)
            while len(self._history_summaries) > MAX_HISTORY_SUMMARIES:
                forgotten, _ = self._history_summaries.popitem(last=False)
                self._symbol_epochs[forgotten[:2]] = self._symbol_epochs.get(forgotten[:2], 0) + 1
                for result_key in list(self._results):
                    if result_key[:2] == forgotten[:2]:
                        self._results.pop(result_key)
            if len(self._symbol_epochs) > MAX_HISTORY_SUMMARIES:
                self._symbol_epochs.clear()
                self._process_epoch = uuid.uuid4().hex
                self._results.clear()
                self._preview_results.clear()
            self._native.move_to_end(key)
            while (
                len(self._native) > MAX_NATIVE_SERIES
                or sum(len(item.bars) for item in self._native.values()) > MAX_NATIVE_ROWS
            ):
                self._native.popitem(last=False)
        return entry

    def process(self, key, config, generation):
        """Worker seam used by isolated tests; never called from a request/snapshot."""
        from application.services.custom_indicators.catalog import evaluate

        market, symbol, _ = key
        now = self._clock()
        try:
            with self._lock:
                if self._stop.is_set() or generation != self._generation:
                    return
            epoch = self.provider.data_epoch()
            with self._lock:
                if self._epoch is not None and epoch != self._epoch:
                    self.invalidate()
                    generation = self._generation
                self._epoch = epoch
            demand = {row["timeframe"]: row["bars"] for row in config["requirements"]}
            primary_tf = config["chart_timeframe"]
            demand[primary_tf] = max(demand.get(primary_tf, 0), 500)
            if market == "BIST":
                demand["1D"] = max(demand.get("1D", 0), 500)
            entries = {
                tf: self._native_frame(market, symbol, tf, count, epoch)
                for tf, count in demand.items()
            }
            if self.provider.memory_epoch() != epoch:
                raise ValueError("Hesap değişti; yeni native geçmiş bekleniyor.")
            daily = entries["1D"].bars if market == "BIST" else ()
            frames = {
                tf: with_native_ends(entry.bars, daily, tf, market, self._clock())
                for tf, entry in entries.items()
            }
            primary = frames[primary_tf]
            values = evaluate(
                config["indicator"],
                config["inputs"],
                primary,
                frames,
                chart_timeframe=primary_tf,
                as_of=self._clock(),
            )
            if len(values) != len(primary):
                raise ValueError("Gösterge sonucu native mumlarla eşleşmiyor.")
            points = [
                {"time": bar.time, "end": bar.end, "confirmed": bar.confirmed, **value}
                for bar, value in zip(primary, values, strict=True)
            ][-MAX_RESULT_POINTS:]
            result = {
                "points": points,
                "received": self._clock(),
                "source_time": primary[-1].time,
                "freshness_time": daily[-1].time if market == "BIST" else primary[-1].time,
                "freshness_duration": 86400 if market == "BIST" else _duration(primary_tf),
                "native_received": min(entry.received for entry in entries.values()),
                "digest": _digest(
                    {
                        "native": [(tf, entry.digest) for tf, entry in sorted(entries.items())],
                        "latest": points[-3:],
                    }
                ),
                "epoch": epoch,
                "config": config,
                "error": None,
            }
        except Exception:
            result = {
                "points": [],
                "received": self._clock(),
                "source_time": None,
                "native_received": now,
                "digest": None,
                "epoch": self._epoch,
                "config": config,
                "error": "Native gösterge geçmişi alınamadı veya gerekli seans/kapanış bilgisi doğrulanamadı.",
            }
        with self._lock:
            if generation != self._generation or self._stop.is_set():
                return
            if key in self._previews:
                self._preview_results[key] = {
                    **result,
                    "continuity": f"{self._process_epoch}:{self._symbol_epochs.get(key[:2], 0)}",
                }
                self._preview_results.move_to_end(key)
                while (
                    len(self._preview_results) > MAX_PREVIEWS
                    or sum(self._result_cells(item) for item in self._preview_results.values())
                    > MAX_PREVIEW_CELLS
                ):
                    self._preview_results.popitem(last=False)
            result["points"] = [{**point, "rows": []} for point in result["points"][-4:]]
            previous = self._results.get(key)
            result["changed"] = (
                previous["changed"]
                if previous and previous.get("digest") == result["digest"]
                else result["received"]
            )
            result["previous"] = (
                previous
                if previous and previous.get("digest") != result["digest"]
                else (previous or {}).get("previous")
            )
            if result["previous"]:
                # Only retain the preceding observation, never a linked history chain.
                result["previous"] = {
                    name: value for name, value in result["previous"].items() if name != "previous"
                }
            result["continuity"] = f"{self._process_epoch}:{self._symbol_epochs.get(key[:2], 0)}"
            self._results[key] = result
            self._results.move_to_end(key)
            self._last_error = result["error"]
            self._last_completed_at = result["received"]
            self._last_cycle_seconds = max(0, result["received"] - now)
            while (
                len(self._results) > MAX_RESULTS
                or sum(self._result_cells(item) for item in self._results.values())
                > MAX_RESULT_CELLS
            ):
                self._results.popitem(last=False)

    @staticmethod
    def _result_cells(result):
        return sum(
            len(point.get("outputs", {})) + sum(len(row) for row in point.get("rows", []))
            for point in result["points"]
        ) * (2 if result.get("previous") else 1)

    def _read(self, key, now, *, require_latest=True):
        result = self._results.get(key)
        if result is None:
            return None, "waiting", "Gösterge için native mum verisi sırada."
        memory_epoch = self.provider.memory_epoch()
        if self._stop.is_set() or result["epoch"] != memory_epoch:
            return result, "unknown", "TradingView bağlantısı değişti; yeni veri bekleniyor."
        if result["error"]:
            return result, "unknown", result["error"]
        if (
            require_latest
            and key[0] == "BIST"
            and result["points"]
            and result["points"][-1]["end"] is None
        ):
            return (
                result,
                "unknown",
                "Seçili BIST ana periyodunun kapanış sınırı doğrulanamadı; 1D veya doğrulanmış seans içi ana periyot gerekir.",
            )
        if (
            now - result["native_received"] > STALE_SECONDS
            or now - result["freshness_time"] > result["freshness_duration"] + 120
        ):
            return result, "stale", "Native mum verisi eski; taze gösterge gözlemi bekleniyor."
        latest = result["points"][-1] if result["points"] else None
        if require_latest and (not latest or not latest.get("ready")):
            return (
                result,
                "unknown",
                (latest or {}).get("reason")
                or "Gösterge geçmişi veya kapanış bilgisi yeterli değil.",
            )
        return result, "ready", None

    def preview(self, indicator, inputs, symbol, market_type="BIST", chart_timeframe="1D"):
        _symbol(symbol, market_type)
        identity, config = self._config(indicator, inputs, chart_timeframe)
        key, now = (market_type, symbol, identity), self._clock()
        with self._lock:
            self._previews[key] = (now + PREVIEW_SECONDS, config)
            self._previews.move_to_end(key)
            while len(self._previews) > MAX_PREVIEWS:
                self._previews.popitem(last=False)
            result, state, reason = self._read(key, now)
            preview = self._preview_results.get(key)
            points = (
                preview["points"]
                if preview and result and preview["digest"] == result["digest"]
                else result["points"]
                if result
                else []
            )
            response = {
                **config,
                "symbol": symbol,
                "market_type": market_type,
                "state": state,
                "reason": reason,
                "source": f"borsapy_tradingview:{'BIST' if market_type == 'BIST' else 'BINANCE'}",
                "received_at": _iso(result["received"]) if result else None,
                "source_timestamp": _iso(result["source_time"]) if result else None,
                "continuity_id": result.get("continuity") if result else None,
                "observation_id": result.get("digest") if result else None,
                "points": points,
                "latest": points[-1] if points else None,
                "limits": self.status()["limits"],
            }
        self._wake.set()
        return response

    def observation(self, ref, symbol, trigger, now):
        from application.services.custom_indicators.catalog import config_key

        identity = config_key(ref["indicator"], dict(ref["inputs"]), ref["timeframe"])
        key = (symbol["market_type"], symbol["symbol"], identity)
        with self._lock:
            if self._blocked_configurations and identity not in self._configs:
                # Preview work has its own lease. It must never let a rule
                # bypass the bounded active-configuration scheduler.
                return {
                    "ready": False,
                    "reason": f"Özel gösterge için {MAX_CONFIGS} farklı etkin ayar sınırı aşıldı; bu ayar hesaplanmıyor. Diğer ayarları duraklatın veya aynı ayarları paylaşın.",
                    "current": None,
                    "previous": None,
                }
            result, state, reason = self._read(key, now, require_latest=False)
            if state != "ready":
                return {"ready": False, "reason": reason, "current": None, "previous": None}
            closed = trigger == "bar_close"
            points = [point for point in result["points"] if point["confirmed"] or not closed]
            point = points[-1] if points else None
            previous = points[-2] if closed and len(points) > 1 else None
            if not closed and result.get("previous"):
                old = result["previous"]
                if old.get("continuity") == result["continuity"] and old["points"]:
                    previous = old["points"][-1]
            output = ref["output"]
            current_value = (
                point.get("outputs", {}).get(output) if point and point.get("ready") else None
            )
            if closed and point and point["end"] is None:
                current_value = None
            previous_value = (
                previous.get("outputs", {}).get(output)
                if previous and previous.get("ready")
                else None
            )
            if isinstance(current_value, bool):
                current_value = float(current_value)
            if isinstance(previous_value, bool):
                previous_value = float(previous_value)
            return {
                "ready": current_value is not None,
                "reason": None
                if current_value is not None
                else "Gösterge çıktısı için doğrulanmış kapanış veya geçmiş bekleniyor.",
                "current": current_value,
                "previous": previous_value,
                "continuity_id": result["continuity"],
                "observation_id": f"{point['time']}:{output}"
                if closed and point
                else result["digest"],
                "bar_time": point["time"] if point else None,
                "bar_end": point["end"] if point else None,
                "previous_bar_time": previous["time"] if previous else None,
                "previous_bar_end": previous["end"] if previous else None,
                "observed_at": result["received"] if closed else result["changed"],
                "source_timestamp": result["source_time"],
            }

    def status(self):
        with self._lock:
            memberships = {
                identity: (set(symbols), all_bist)
                for identity, symbols, all_bist in self._memberships
            }
            universe = set(self._universe)
            fresh_configured = sum(
                self._clock() - result["native_received"] <= STALE_SECONDS
                and not result["error"]
                and key[2] in memberships
                and (
                    key[:2] in memberships[key[2]][0]
                    or (memberships[key[2]][1] and key[:2] in universe)
                )
                for key, result in self._results.items()
            )
            return {
                "running": self._running,
                "configured": len(self._configs),
                "blocked_configurations": self._blocked_configurations,
                "requested_rule_symbols": self._jobs_requested,
                "preview_leases": len(self._previews),
                "native_series": len(self._native),
                "native_rows": sum(len(row.bars) for row in self._native.values()),
                "history_continuity_summaries": len(self._history_summaries),
                "results": len(self._results),
                "preview_results": len(self._preview_results),
                "last_completed_at": _iso(self._last_completed_at),
                "last_cycle_seconds": self._last_cycle_seconds,
                "oldest_result_age_seconds": max(
                    (self._clock() - result["received"] for result in self._results.values()),
                    default=None,
                ),
                "refresh_target_seconds": REFRESH_SECONDS,
                "pending_or_stale_rule_symbols": max(
                    0,
                    self._jobs_requested - fresh_configured,
                ),
                "last_error": self._last_error,
                "worker_count": 1,
                "source": "borsapy_tradingview native BIST/BINANCE",
                "limits": {
                    "native_series": MAX_NATIVE_SERIES,
                    "native_rows": MAX_NATIVE_ROWS,
                    "results": MAX_RESULTS,
                    "result_cells": MAX_RESULT_CELLS,
                    "configurations": MAX_CONFIGS,
                    "preview_leases": MAX_PREVIEWS,
                },
                "one_second_coverage_guaranteed": False,
            }
