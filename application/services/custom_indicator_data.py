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
from bisect import bisect_left
from collections import OrderedDict, deque
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from application.services.custom_indicators.core import Bar
from infrastructure.providers.custom_indicator_leases import is_leased_timeframe

MAX_NATIVE_SERIES = 64
MAX_NATIVE_ROWS = 60000
MAX_RESULTS = 4096
MAX_RESULT_POINTS = 128
MAX_RESULT_CELLS = 262144
MAX_PREVIEW_CELLS = 32768
MAX_PREVIEWS = 32
MAX_CONFIGS = 256
MAX_HISTORY_SUMMARIES = 8192
PREVIEW_SECONDS = 120
REFRESH_SECONDS = 21600  # History reconciliation only; live prices are event driven.
STALE_SECONDS = 180
HISTORY_RETRY_SECONDS = 30
MAX_HISTORY_RETRY_SECONDS = 1800
MAX_SEED_CHECKS_PER_TURN = 64
MAX_COVERAGE_SYMBOLS = 4000
MAX_COVERAGE_PAIRS = 4096


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
    """BINANCE 24x7 native periods restart at each TradingView year anchor.

    The next supplied native start must still equal this end in native_bars;
    a shorter year-boundary bar is not permission to accept arbitrary gaps.
    https://www.tradingview.com/charting-library-docs/latest/ui_elements/Resolution/#bar-alignment
    """
    if timeframe.endswith("M"):
        value = datetime.fromtimestamp(stamp, UTC)
        month = value.month - 1 + int(timeframe[:-1])
        end = value.replace(year=value.year + month // 12, month=month % 12 + 1, day=1)
        # Non-divisors such as 5M also restart in January, not in April.
        return min(end, datetime(value.year + 1, 1, 1, tzinfo=UTC)).timestamp()
    end = stamp + _duration(timeframe)
    if timeframe.endswith(("D", "W")) and timeframe not in {"1D", "1W"}:
        value = datetime.fromtimestamp(stamp, UTC)
        boundary = datetime(value.year + 1, 1, 1, tzinfo=UTC)
        if timeframe.endswith("W"):
            # The partial week before the first Monday remains in the old bar.
            boundary += timedelta(days=(-boundary.weekday()) % 7)
        end = min(end, boundary.timestamp())
    return end


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
    daily_times = tuple(day.time for day in daily)
    for index, bar in enumerate(bars):
        following = bars[index + 1].time if index + 1 < len(bars) else None
        # Only a following provider bucket witnesses the historical boundary.
        # Both native inputs are already sorted. Find the last supplied daily
        # candle inside this bucket without rescanning the full daily history.
        last = bisect_left(daily_times, following) - 1 if following else -1
        end = daily[last].end if last >= 0 and daily[last].time >= bar.time else None
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
    requested: int

    @classmethod
    def build(cls, bars, now, *, requested=None):
        hashes = tuple(_record_hash(bar) for bar in bars)
        return cls(
            len(bars),
            bars[0].time,
            bars[-1].time,
            tuple((bar.time, value) for bar, value in zip(bars[:4], hashes[:4], strict=True)),
            _rolling_hash(hashes[:-1]),
            now,
            len(bars) if requested is None else requested,
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
        self._publication_lock = threading.RLock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread = None
        self._configs = {}
        self._blocked_configurations = 0
        self._memberships = []
        self._coverage_scopes = ()
        self._coverage_demands = {}
        self._coverage_truncated_configs = frozenset()
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
        from application.services.custom_indicator_live import LiveIndicatorData

        self.live = LiveIndicatorData(self)
        self._seed_due = set()
        self._live_signature = None
        self._publication_epoch = 0
        self._publication_members = {}
        self._live_cells = 0
        self._job_order = ()
        self._job_cursor = 0
        self._seed_queue = deque()
        self._seed_queued = set()
        self._closed_configs = set()
        self._history_last_error = None
        self._history_failures = {}
        self._history_retries = {}

    def _sync_live(self):
        with self._lock:
            # Preview reads renew their LRU position, but unchanged membership
            # must not rebuild the whole universe or reset the history cursor.
            active_previews = frozenset(
                key for key, (expires, _) in self._previews.items() if expires > self._clock()
            )
            signature = self._generation, id(self._universe), active_previews
            if signature == self._live_signature:
                return
            self._live_signature = signature
            jobs = {}
            from application.services.custom_indicator_live import MAX_LIVE_JOBS

            for identity, symbols, all_bist in self._memberships:
                for member in sorted(set(symbols) | (set(self._universe) if all_bist else set())):
                    jobs[(*member, identity)] = self._configs[identity]
                    if len(jobs) >= MAX_LIVE_JOBS:
                        break
                if len(jobs) >= MAX_LIVE_JOBS:
                    break
            rule_job_keys = frozenset(jobs)
            for key, (expires, config) in self._previews.items():
                if expires > self._clock() and len(jobs) < MAX_LIVE_JOBS:
                    jobs[key] = config
        self.live.configure(jobs.items(), rule_job_keys=rule_job_keys)
        with self._lock:
            self._job_order = tuple(sorted(key for key in jobs if self.live.admitted(key)))
            retained_jobs = set(self._job_order)
            self._history_failures = {
                key: value for key, value in self._history_failures.items() if key in retained_jobs
            }
            self._history_retries = {
                key: value for key, value in self._history_retries.items() if key in retained_jobs
            }
            self._seed_due.intersection_update(retained_jobs)
            self._seed_queue = deque(key for key in self._seed_queue if key in retained_jobs)
            self._seed_queued = set(self._seed_queue)
            members = {key[:2] for key in retained_jobs}
            self._publication_members = {
                key: value for key, value in self._publication_members.items() if key in members
            }
            self._job_cursor = 0
            for key in self._job_order:
                if key not in self._results or not self.live.has_seed(
                    key, self.provider.memory_epoch()
                ):
                    self._queue_seed(key)

    def _queue_seed(self, key):
        if self.live.admitted(key) and key not in self._seed_queued:
            self._seed_queue.append(key)
            self._seed_queued.add(key)

    def _remove_result(self, key):
        result = self._results.pop(key, None)
        if result and result.get("live"):
            self._live_cells -= self._result_cells(result)

    def publication_token(self, member):
        return self._publication_epoch, self._publication_members.get(member, 0)

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

        configs, memberships, blocked, closed_configs = {}, {}, set(), set()
        scopes, demands, truncated = {}, {}, set()
        scope_cells = demand_count = 0
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
                # Share membership sets between every output/trigger that uses
                # the same list. Diagnostic metadata has its own finite budget.
                scope = (
                    frozenset(
                        (item["market_type"], item["symbol"]) for item in rule.get("symbols", [])
                    ),
                    rule.get("scope") == "all_bist",
                )
                if scope not in scopes:
                    if scope_cells + len(scope[0]) > MAX_COVERAGE_PAIRS:
                        truncated.add(identity)
                    else:
                        scopes[scope] = len(scopes)
                        scope_cells += len(scope[0])
                if scope in scopes:
                    demand = (rule.get("trigger", "bar_close"), ref["output"], scopes[scope])
                    selected = demands.setdefault(identity, set())
                    if demand not in selected:
                        if demand_count >= MAX_COVERAGE_PAIRS:
                            truncated.add(identity)
                        else:
                            selected.add(demand)
                            demand_count += 1
                if rule.get("trigger") == "bar_close":
                    closed_configs.add(identity)
                target = memberships.setdefault(identity, {"symbols": set(), "all_bist": False})
                target["all_bist"] |= rule.get("scope") == "all_bist"
                target["symbols"].update(
                    (item["market_type"], item["symbol"]) for item in rule.get("symbols", [])
                )
        with self._lock:
            newly_closed = closed_configs - self._closed_configs
            self._configs = configs
            self._coverage_scopes = tuple(scopes)
            self._coverage_demands = {
                identity: tuple(sorted(values)) for identity, values in demands.items()
            }
            self._coverage_truncated_configs = frozenset(truncated)
            self._closed_configs = closed_configs
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
                    self._remove_result(key)
            if not self._memberships and not self._previews:
                self._native.clear()
                self._errors.clear()
                self._preview_results.clear()
        self._wake.set()
        self._sync_live()
        with self._lock:
            # An existing intrabar seed has no historical signal replay. A
            # newly added close-only rule must not wait for the six-hour
            # reconciliation to obtain its confirmed observations.
            for key in self._job_order:
                if key[2] in newly_closed:
                    self._seed_due.add(key)
                    self._queue_seed(key)

    def set_universe(self, universe):
        with self._lock:
            self._universe = tuple(("BIST", item["symbol"]) for item in universe)
            self._refresh_count()
        self._sync_live()

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
        self.live.start()

    def stop(self):
        self._stop.set()
        self._wake.set()
        self.live.stop()
        if self._thread:
            self._thread.join()
        with self._lock:
            self._thread = None
            self._running = False
            self._native.clear()
            self._results.clear()
            self._live_cells = 0
            self._preview_results.clear()
            self._history_failures.clear()
            self._history_retries.clear()

    def invalidate(self):
        with self._lock:
            self._publication_epoch += 1
            self._generation += 1
            self._process_epoch = uuid.uuid4().hex
            self._native.clear()
            self._results.clear()
            self._preview_results.clear()
            self._errors.clear()
            self._symbol_epochs.clear()
            self._history_summaries.clear()
            self._history_failures.clear()
            self._history_retries.clear()
            self._live_cells = 0
        self.live.invalidate()
        self._wake.set()

    def _history_transport_ready(self, key, config):
        # Historical/closed-bar replay does not depend on a live transport.
        # Running intrabar jobs first require actual native witnesses: a socket
        # being open alone does not prove an unavailable list symbol resolved.
        if not self._running or key[2] in self._closed_configs:
            return True
        needed = {row["timeframe"] for row in config["requirements"]} | {config["chart_timeframe"]}
        if key[0] == "BIST" or any(is_leased_timeframe(tf) for tf in needed):
            needed.add("1D")
        return self.live.history_ready(key[:2], needed)

    def _history_job_ready(self, key, config, now):
        return now >= self._history_retries.get(key, 0) and self._history_transport_ready(
            key, config
        )

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
                self._live_cells = 0
                self._history_summaries.clear()
                self._symbol_epochs.clear()
                self._history_failures.clear()
                self._history_retries.clear()
                return None
            self._turn += 1
            preview_job = None
            for key, (_, config) in self._previews.items():
                cached = self._preview_results.get(key)
                if not self.live.admitted(key):
                    continue
                if not self._history_job_ready(key, config, now):
                    continue
                if cached and now < cached.get("history_retry_at", 0):
                    continue
                if (
                    key in self._seed_due
                    or not cached
                    or not self.live.has_seed(key, self.provider.memory_epoch())
                    or not cached.get("history_replayed")
                    or bool(cached.get("history_retry_at"))
                    or cached.get("error")
                    and not cached.get("native_witness_wait")
                    and now - cached["received"] >= 30
                    or now - cached.get("seed_received", cached["received"]) >= REFRESH_SECONDS
                ):
                    preview_job = key, config, self._generation
                    break
            if preview_job and (not self._memberships or self._turn % 4 == 0):
                # Preserve the preview share during a large initial bootstrap,
                # not only after its entire seed queue has drained.
                key = preview_job[0]
                if key in self._seed_queued:
                    self._seed_queue.remove(key)
                    self._seed_queued.discard(key)
                return preview_job
            # Native packets can wake this worker repeatedly during bootstrap.
            # Bound each turn instead of rescanning every deferred member on
            # every packet. Rotation preserves eventual service, while the
            # separate bounded fallback below still recovers missing seeds and
            # due refreshes even if unavailable members remain queued forever.
            for _ in range(min(MAX_SEED_CHECKS_PER_TURN, len(self._seed_queue))):
                key = self._seed_queue.popleft()
                self._seed_queued.discard(key)
                if self.live.admitted(key):
                    config = self.live._configs[key]
                    if self._history_job_ready(key, config, now):
                        return key, config, self._generation
                    self._queue_seed(key)
            if not self._memberships:
                return preview_job
            for _ in range(min(64, len(self._job_order))):
                self._job_cursor %= len(self._job_order)
                key = self._job_order[self._job_cursor]
                self._job_cursor += 1
                if not self.live.admitted(key):
                    continue
                if not self._history_job_ready(key, self.live._configs[key], now):
                    continue
                cached = self._results.get(key)
                if cached and now < cached.get("history_retry_at", 0):
                    continue
                if (
                    key in self._seed_due
                    or not cached
                    # A quote can publish a fresh unknown observation before
                    # bootstrap, or after a preparation loses its publication
                    # token. That result must not hide an absent compact seed
                    # until the periodic history reconciliation six hours later.
                    or not self.live.has_seed(key, self.provider.memory_epoch())
                    or bool(cached.get("history_retry_at"))
                    or cached.get("error")
                    and not cached.get("native_witness_wait")
                    and now - cached["received"] >= 30
                    or now - cached.get("seed_received", cached["received"]) >= REFRESH_SECONDS
                ):
                    # The fallback cursor can reach a deferred key before the
                    # bounded queue cursor. Consume its queued demand too, so
                    # successful preparation is not repeated on queue rotation.
                    if key in self._seed_queued:
                        self._seed_queue.remove(key)
                        self._seed_queued.discard(key)
                    return key, self.live._configs[key], self._generation
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
        publication_epoch = self.publication_token(key[:2])
        with self._lock:
            if self._stop.is_set():
                raise ValueError("Özel gösterge veri servisi durduruldu.")
            old = self._native.get(key)
            summary = self._history_summaries.get(key)
            # Configuration changes may need a longer prefix once. Preserve
            # that request size even after raw-cache eviction, so smaller
            # configurations cannot oscillate the shared continuity window.
            # Requested count matters: young listings may return fewer rows.
            bars = max(bars, summary.requested if summary else 0)
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
        with self._publication_lock, self._lock:
            if self._stop.is_set() or self.provider.memory_epoch() != epoch:
                raise ValueError("Hesap değişti; yeni native geçmiş bekleniyor.")
            if publication_epoch != self.publication_token(key[:2]):
                raise ValueError("Geçmiş isteği sırasında native kaynak değişti.")
            summary = self._history_summaries.get(key)
            comparison_time = (
                summary.received
                if summary and self.live.native_continuity(key, epoch)
                else entry.received
            )
            revision = bool(summary and not summary.continues(points, comparison_time))
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
                self.live.invalidate_witnesses(member)
                self.live_gap(
                    "Native geçmiş düzeltildi; canlı gösterge yeniden hazırlanıyor.", member
                )
            self._native[key] = entry
            self._history_summaries[key] = HistorySummary.build(
                points, entry.received, requested=entry.requested
            )
            self._history_summaries.move_to_end(key)
            while len(self._history_summaries) > MAX_HISTORY_SUMMARIES:
                forgotten, _ = self._history_summaries.popitem(last=False)
                self.live_gap("Native geçmiş karşılaştırma belleği yenileniyor.", forgotten[:2])
            if len(self._symbol_epochs) > MAX_HISTORY_SUMMARIES:
                self._symbol_epochs.clear()
                self._process_epoch = uuid.uuid4().hex
                self._results.clear()
                self._live_cells = 0
                self._preview_results.clear()
            self._native.move_to_end(key)
            while (
                len(self._native) > MAX_NATIVE_SERIES
                or sum(len(item.bars) for item in self._native.values()) > MAX_NATIVE_ROWS
            ):
                self._native.popitem(last=False)
        return entry

    @staticmethod
    def _native_demand(config, market):
        demand = {row["timeframe"]: row["bars"] for row in config["requirements"]}
        primary_tf = config["chart_timeframe"]
        demand[primary_tf] = max(demand.get(primary_tf, 0), 500)
        if market == "BIST" or any(is_leased_timeframe(tf) for tf in demand):
            demand["1D"] = max(demand.get("1D", 0), 500)
        return demand

    def process(self, key, config, generation):
        """Worker seam used by isolated tests; never called from a request/snapshot."""
        from application.services.custom_indicators.catalog import evaluate

        market, symbol, _ = key
        now = self._clock()
        publication_epoch = self.publication_token(key[:2])
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
            demand = self._native_demand(config, market)
            primary_tf = config["chart_timeframe"]
            # One indexed pass over this member's admitted configurations,
            # never an all-universe scan for each native frame.
            with self.live._lock:
                sibling_configs = tuple(
                    self.live._configs[item] for item in self.live._members.get(key[:2], ())
                )
            for sibling in sibling_configs:
                for tf, count in self._native_demand(sibling, market).items():
                    if tf in demand:
                        demand[tf] = max(demand[tf], count)
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
            with self._lock:
                preview_active = self._previews.get(key, (0, None))[0] > self._clock()
                replay = (
                    key[2] in self._closed_configs or preview_active or key[2] not in self._configs
                )
            # Live rule bootstrap needs only closed recursive seeds. Replaying
            # every primary candle is reserved for charts and close-only rules;
            # no historical observation can stand in for the first real quote.
            points = []
            if replay:
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
            prepared_seed = self.live.prepare_seed(config, frames, epoch)
            result = {
                "points": points,
                "history_replayed": replay,
                "received": self._clock(),
                "seed_received": self._clock(),
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
        with self._publication_lock, self._lock:
            if (
                generation != self._generation
                or self._stop.is_set()
                or publication_epoch != self.publication_token(key[:2])
            ):
                return
            self._seed_due.discard(key)
            if result["error"]:
                failures = min(self._history_failures.get(key, 0) + 1, 7)
                self._history_failures[key] = failures
                retry_at = self._clock() + min(
                    MAX_HISTORY_RETRY_SECONDS, HISTORY_RETRY_SECONDS * 2 ** (failures - 1)
                )
                self._history_retries[key] = result["history_retry_at"] = retry_at
            else:
                self._history_failures.pop(key, None)
                self._history_retries.pop(key, None)
            live_result = self._results.get(key)
            if (
                result["error"]
                and live_result
                and live_result.get("live")
                and self.live.has_seed(key, self.provider.memory_epoch())
            ):
                # A history HTTP failure is not a live transport gap. Retain
                # current quote/range/edge state and retry history at a bound.
                self._history_last_error = result["error"]
                live_result["history_retry_at"] = retry_at
                if key in self._preview_results:
                    self._preview_results[key]["history_retry_at"] = live_result["history_retry_at"]
                return
            self._history_last_error = result["error"]
            if (
                not result["error"]
                and live_result
                and live_result.get("live")
                and self.live.retains_seed(key, prepared_seed)
            ):
                # Periodic history and explicit closed-bar replay must not roll
                # back a newer live price, SMI range or signal-edge baseline.
                # Native rollover already advances the compact closed seeds;
                # genuine revisions clear them before reaching this branch.
                before = self._result_cells(live_result)
                if replay:
                    live_result["closed_points"] = [
                        {**point, "rows": []} for point in result["points"] if point["confirmed"]
                    ][-4:]
                live_result["seed_received"] = result["received"]
                live_result.pop("history_retry_at", None)
                live_result.pop("native_wait", None)
                self._live_cells += self._result_cells(live_result) - before
                if replay and self._previews.get(key, (0, None))[0] > self._clock():
                    current = self._preview_results.get(key, live_result)["points"][-1:]
                    history = [
                        point
                        for point in result["points"]
                        if current and point["time"] < current[0]["time"]
                    ]
                    self._preview_results[key] = {
                        **live_result,
                        "points": [*history[-MAX_RESULT_POINTS + 1 :], *current],
                        "history_replayed": True,
                    }
                self._last_error = None
                self._last_completed_at = result["received"]
                self._last_cycle_seconds = max(0, result["received"] - now)
                return
            if (
                result.get("history_replayed")
                and self._previews.get(key, (0, None))[0] > self._clock()
            ):
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
            self._remove_result(key)
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
                self._remove_result(next(iter(self._results)))
            if not result["error"]:
                self.live.install_seed(key, prepared_seed, generation=generation)

    @staticmethod
    def _result_cells(result):
        def count(points):
            return sum(
                len(point.get("outputs", {})) + sum(len(row) for row in point.get("rows", []))
                for point in points
            )

        previous = result.get("previous") or {}
        return (
            count(result["points"])
            + count(result.get("closed_points", ()))
            + count(previous.get("points", ()))
            + count(previous.get("closed_points", ()))
        )

    def live_gap(self, reason, member=None, native_key=None):
        """Invalidate comparison state after a provider gap; never invent a crossing."""
        with self._publication_lock, self._lock:
            self.live.clear_comparisons(member)
            if member is None:
                self._publication_epoch += 1
            else:
                self._publication_members[member] = self._publication_members.get(member, 0) + 1
            for key, result in list(self._results.items()):
                if member is None or key[:2] == member:
                    before = self._result_cells(result) if result.get("live") else 0
                    result["error"] = reason
                    result.pop("previous", None)
                    if result.get("live"):
                        self._live_cells += self._result_cells(result) - before
                    self._seed_due.add(key)
                    self._queue_seed(key)
            for key in list(self._native):
                if (
                    native_key == key
                    or native_key is None
                    and (member is None or key[:2] == member)
                ):
                    self._native.pop(key)
            if member is None:
                self._process_epoch = uuid.uuid4().hex
            else:
                self._symbol_epochs[member] = self._symbol_epochs.get(member, 0) + 1
            self._last_error = reason
        self._wake.set()

    def native_witness_wait(self, member, reason):
        """Break observation continuity while retaining a proven rollover's seeds."""
        with self._publication_lock, self._lock:
            self._publication_members[member] = self._publication_members.get(member, 0) + 1
            self._symbol_epochs[member] = self._symbol_epochs.get(member, 0) + 1
            for key, result in self._results.items():
                if key[:2] == member:
                    before = self._result_cells(result) if result.get("live") else 0
                    result["error"] = reason
                    result["native_witness_wait"] = True
                    result.pop("previous", None)
                    if result.get("live"):
                        self._live_cells += self._result_cells(result) - before
            for key, result in self._preview_results.items():
                if key[:2] == member:
                    result["error"] = reason
                    result["native_witness_wait"] = True
                    result.pop("previous", None)
            self._last_error = reason
        self._wake.set()

    def native_refresh(self, native_key, *, jobs=None, invalidate_native=True):
        """A witnessed next native bar refreshes seeds without fabricating a data gap."""
        with self._publication_lock, self._lock:
            member = native_key[:2]
            self._publication_members[member] = self._publication_members.get(member, 0) + 1
            if invalidate_native:
                self._native.pop(native_key, None)
            for key, result in self._results.items():
                if key[:2] == native_key[:2] and (jobs is None or key in jobs):
                    self._seed_due.add(key)
                    self._queue_seed(key)
                    result["native_wait"] = True
        self._wake.set()

    def native_advanced(self, native_key, closed, current):
        """Retain a witnessed rollover in the bounded shared bootstrap cache."""
        with self._publication_lock, self._lock:
            member = native_key[:2]
            self._publication_members[member] = self._publication_members.get(member, 0) + 1
            old = self._native.get(native_key)
            if old is not None and old.bars[-1].time == closed.time:
                points = (*old.bars[:-1], closed, current)[-len(old.bars) :]
                digest = _digest(
                    [
                        old.digest,
                        closed.time,
                        closed.high,
                        closed.low,
                        closed.close,
                        current.time,
                        current.open,
                    ]
                )
                self._native[native_key] = replace(old, bars=points, digest=digest)
                self._history_summaries[native_key] = HistorySummary.build(
                    points, self._clock(), requested=old.requested
                )

    def publish_live(
        self,
        updates,
        *,
        source,
        received,
        serial,
        price,
        publication_epoch,
        live_generation,
        expected_epoch,
    ):
        """Publish every configured operand for one price as an atomic observation."""
        now = self._clock()
        with self._lock:
            if (
                publication_epoch != self.publication_token(updates[0][0][:2])
                or live_generation != self.live._generation
                or self._stop.is_set()
                or expected_epoch != self.provider.memory_epoch()
            ):
                return False
            epoch = self.provider.memory_epoch()
            for key, config, point in updates:
                prior = self._results.get(key)
                continuity = f"{self._process_epoch}:{self._symbol_epochs.get(key[:2], 0)}"
                result = {
                    "points": [{**point, "rows": []}],
                    "received": now,
                    "seed_received": (prior or {}).get("seed_received", now),
                    "source_time": source,
                    "freshness_time": source,
                    "freshness_duration": 30,
                    "native_received": received,
                    "digest": f"live:{continuity}:{serial}",
                    "epoch": epoch,
                    "config": config,
                    "error": None,
                    "changed": now,
                    "continuity": continuity,
                    "live": True,
                    "live_price": price,
                    "history_retry_at": (prior or {}).get("history_retry_at", 0),
                    "previous": {name: value for name, value in prior.items() if name != "previous"}
                    if prior and prior.get("live") and prior.get("continuity") == continuity
                    else None,
                }
                result["closed_points"] = (prior or {}).get(
                    "closed_points", [p for p in (prior or {}).get("points", ()) if p["confirmed"]]
                )
                if prior and prior.get("live"):
                    self._live_cells -= self._result_cells(prior)
                self._live_cells += self._result_cells(result)
                self._results[key] = result
                self._results.move_to_end(key)
                if key in self._previews:
                    old_preview = self._preview_results.get(key)
                    history = [
                        item
                        for item in (old_preview or {}).get("points", ())
                        if item["time"] is not None
                        and point["time"] is not None
                        and item["time"] < point["time"]
                    ]
                    self._preview_results[key] = {
                        **result,
                        "points": [*history[-MAX_RESULT_POINTS + 1 :], point],
                        "history_replayed": bool((old_preview or {}).get("history_replayed")),
                    }
                    self._preview_results.move_to_end(key)
            while len(self._results) > MAX_RESULTS or self._live_cells > MAX_RESULT_CELLS:
                _, forgotten = self._results.popitem(last=False)
                if forgotten.get("live"):
                    self._live_cells -= self._result_cells(forgotten)
            while len(self._preview_results) > MAX_PREVIEWS:
                self._preview_results.popitem(last=False)
            return True

    def _read(self, key, now, *, require_latest=True):
        result = self._results.get(key)
        config = self.live._configs.get(key)
        needed = (
            {row["timeframe"] for row in config["requirements"]}
            | {config["chart_timeframe"]}
            | ({"1D"} if key[0] == "BIST" else set())
            if config
            else set()
        )
        leased = any(is_leased_timeframe(tf) for tf in needed)
        if leased:
            needed.add("1D")
        if require_latest or result is None:
            with self.live._lock:
                refused = any((*key[:2], timeframe) in self.live._refused for timeframe in needed)
            if refused:
                return (
                    result,
                    "unknown",
                    "Sağlayıcı bu sembolün gerekli native mum verisini reddetti.",
                )
        if result is None:
            return None, "waiting", "Gösterge için native mum verisi sırada."
        memory_epoch = self.provider.memory_epoch()
        if self._stop.is_set() or result["epoch"] != memory_epoch:
            return result, "unknown", "TradingView bağlantısı değişti; yeni veri bekleniyor."
        if result["error"]:
            return result, "unknown", result["error"]
        if (
            result.get("live")
            and self.live._enabled
            and leased
            and callable(getattr(self.live._connection, "witness_valid", None))
            and not self.live.history_ready(key[:2], needed)
        ):
            return (
                result,
                "unknown",
                "Native zaman dilimlerinin güncel günlük mumla doğrulanması bekleniyor.",
            )
        if require_latest and self.live._enabled and not result.get("live"):
            return (
                result,
                "waiting",
                "Native geçmiş hazır; canlı fiyat akışının ilk gözlemi bekleniyor.",
            )
        if (
            result.get("live")
            and max(now - result["source_time"], now - result["native_received"]) > 30
        ):
            return (
                result,
                "stale",
                "Canlı gösterge fiyatı eski; yeni fiyat güncellemesi bekleniyor.",
            )
        if (
            require_latest
            and not result.get("live")
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
                "observation_price": result.get("live_price") if result else None,
                "continuity_id": result.get("continuity") if result else None,
                "observation_id": result.get("digest") if result else None,
                "points": points,
                "latest": points[-1] if points else None,
                "limits": self.status()["limits"],
            }
        self._wake.set()
        self._sync_live()
        return response

    def observation(self, ref, symbol, trigger, now):
        from application.services.custom_indicators.catalog import config_key

        identity = config_key(ref["indicator"], dict(ref["inputs"]), ref["timeframe"])
        key = (symbol["market_type"], symbol["symbol"], identity)
        return self._observation(key, ref, trigger, now)

    def _observation(self, key, ref, trigger, now):
        """Read an already identified operand; diagnostic reads reuse the same guards."""
        identity = key[2]
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
            if identity in self._configs and not self.live.admitted(key):
                return {
                    "ready": False,
                    "reason": "Canlı gösterge sembol/ayar veya native seri kapasitesi doldu; bu hesap kabul edilmedi.",
                    "current": None,
                    "previous": None,
                }
            result, state, reason = self._read(key, now, require_latest=False)
            if trigger != "bar_close" and result and result.get("native_wait"):
                state, reason = "waiting", "Yeni native mum başlangıcı hazırlanıyor."
            if self.live._enabled and trigger != "bar_close" and result and not result.get("live"):
                state, reason = "waiting", "İlk canlı fiyat gözlemi bekleniyor."
            if state != "ready":
                return {"ready": False, "reason": reason, "current": None, "previous": None}
            closed = trigger == "bar_close"
            points = (
                [
                    point
                    for point in result.get("closed_points", result["points"])
                    if point["confirmed"]
                ]
                if closed
                else result["points"]
            )
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
                "live_price": result.get("live_price"),
                "previous_live_price": (result.get("previous") or {}).get("live_price"),
            }

    def coverage(self):
        """Read bounded, configured-rule operand readiness without registering work.

        This reports selected inputs, not condition matches or notification
        delivery. Preview-only members are excluded. Missing metadata/budget
        never turns an uninspected operand into a ready result.
        """
        with self._lock:
            now = self._clock()
            universe = set(self._universe)
            members = set()
            symbol_truncated = False
            for _, explicit, all_bist in self._memberships:
                for source in (explicit, self._universe if all_bist else ()):
                    for member in source:
                        if member not in members and len(members) >= MAX_COVERAGE_SYMBOLS:
                            symbol_truncated = True
                            break
                        members.add(member)
                    if symbol_truncated:
                        break
                if symbol_truncated:
                    break
            rows = {
                member: {
                    "market_type": member[0],
                    "symbol": member[1],
                    "configured": True,
                    "ready": False,
                    "state": "not_inspected",
                    "inspected_configurations": 0,
                    "ready_configurations": 0,
                    "pending_configurations": 0,
                    "reasons": set(),
                    "requested_timeframes": set(),
                    "refused_timeframes": set(),
                    "source_timestamp": None,
                    "received_at": None,
                }
                for member in sorted(members)
            }
            pairs = 0
            pairs_truncated = False
            for identity, explicit, all_bist in self._memberships:
                config = self._configs[identity]
                needed_by_market = {
                    market: set(self._native_demand(config, market))
                    for market in ("BIST", "Kripto")
                }
                for member in sorted(set(explicit) | (universe if all_bist else set())):
                    if member not in rows:
                        continue
                    if pairs >= MAX_COVERAGE_PAIRS:
                        pairs_truncated = True
                        break
                    pairs += 1
                    row = rows[member]
                    row["inspected_configurations"] += 1
                    key = (*member, identity)
                    needed = needed_by_market[member[0]]
                    row["requested_timeframes"].update(needed)
                    with self.live._lock:
                        refused = {tf for tf in needed if (*member, tf) in self.live._refused}
                    row["refused_timeframes"].update(refused)
                    selected = {
                        (trigger, output)
                        for trigger, output, index in self._coverage_demands.get(identity, ())
                        if member in self._coverage_scopes[index][0]
                        or self._coverage_scopes[index][1]
                        and member in universe
                    }
                    result = self._results.get(key)
                    reason = None
                    if identity in self._coverage_truncated_configs or not selected:
                        reason = "metadata_capacity"
                    elif not self.live.admitted(key):
                        reason = "runtime_capacity"
                    else:
                        for trigger, output in sorted(selected):
                            if (
                                self.live._enabled
                                and trigger != "bar_close"
                                and not self.live.has_seed(key, self.provider.memory_epoch())
                            ):
                                reason = "native_refused" if refused else "seed_wait"
                                break
                            observed = self._observation(key, {"output": output}, trigger, now)
                            value = observed.get("current")
                            finite = isinstance(value, (int, float)) and math.isfinite(value)
                            if not observed.get("ready") or not finite:
                                reason = self._coverage_reason(key, result, refused, now)
                                if observed.get("ready") and not finite:
                                    reason = "output_unavailable"
                                break
                    row["ready_configurations" if reason is None else "pending_configurations"] += 1
                    if reason is not None:
                        row["reasons"].add(reason)
                    if result:
                        # Oldest contributing configuration is conservative;
                        # no average hides a stale operand in a mixed rule.
                        for target, source in (
                            ("source_timestamp", "source_time"),
                            ("received_at", "native_received"),
                        ):
                            value = result.get(source)
                            if isinstance(value, (int, float)) and math.isfinite(value):
                                previous = row[target]
                                row[target] = value if previous is None else min(previous, value)
                if pairs_truncated:
                    break
            incomplete = symbol_truncated or pairs_truncated or bool(self._blocked_configurations)
            for row in rows.values():
                inspected = row["inspected_configurations"]
                if incomplete:
                    row["reasons"].add("inspection_capacity")
                complete = not incomplete and "metadata_capacity" not in row["reasons"]
                row["configured_configurations"] = inspected if complete else None
                row["ready"] = complete and inspected > 0 and row["pending_configurations"] == 0
                row["state"] = (
                    "ready"
                    if row["ready"]
                    else "pending"
                    if complete and inspected
                    else "not_inspected"
                )
                for field in ("reasons", "requested_timeframes", "refused_timeframes"):
                    row[field] = sorted(row[field])
                for field in ("source_timestamp", "received_at"):
                    row[field] = _iso(row[field])
            return {
                "observed_at": _iso(now),
                "scope": "configured_rule_selected_outputs",
                "provider_calls": False,
                "work_registered": False,
                "values_included": False,
                "intrabar_source_and_receipt_stale_seconds": 30,
                "condition_matches_or_delivery_verified": False,
                "rows": list(rows.values()),
                "row_count": len(rows),
                "ready_members": sum(row["ready"] for row in rows.values()),
                "pending_members": sum(row["state"] == "pending" for row in rows.values()),
                "uninspected_members": sum(
                    row["state"] == "not_inspected" for row in rows.values()
                ),
                "inspected_config_member_pairs": pairs,
                "requested_config_member_pairs": self._jobs_requested,
                "rows_truncated": symbol_truncated,
                "pairs_truncated": pairs_truncated,
                "metadata_truncated": bool(self._coverage_truncated_configs),
                "blocked_configurations": self._blocked_configurations,
                "limits": {
                    "symbols": MAX_COVERAGE_SYMBOLS,
                    "config_member_pairs": MAX_COVERAGE_PAIRS,
                },
            }

    def _coverage_reason(self, key, result, refused, now):
        if refused:
            return "native_refused"
        if result is None:
            return "seed_wait"
        if self._stop.is_set() or result["epoch"] != self.provider.memory_epoch():
            return "account_or_transport_changed"
        if result.get("error"):
            return "history_or_continuity_error"
        if result.get("native_wait") or result.get("native_witness_wait"):
            return "native_witness_wait"
        if self.live._enabled and not result.get("live"):
            return "live_quote_wait"
        if (
            result.get("live")
            and max(now - result["source_time"], now - result["native_received"]) > 30
        ):
            return "quote_stale"
        if now - result["native_received"] > STALE_SECONDS:
            return "history_stale"
        return "output_or_native_witness_unavailable"

    def status(self):
        with self._lock:
            now = self._clock()
            memberships = {
                identity: (set(symbols), all_bist)
                for identity, symbols, all_bist in self._memberships
            }
            universe = set(self._universe)
            fresh_configured = sum(
                key[2] in memberships
                and (
                    key[:2] in memberships[key[2]][0]
                    or (memberships[key[2]][1] and key[:2] in universe)
                )
                and self.live.admitted(key)
                and (not self.live._enabled or self.live.has_seed(key, result["epoch"]))
                and self._read(key, now)[1] == "ready"
                for key, result in self._results.items()
            )
            workers = {thread.name: thread.is_alive() for thread in tuple(self.live._threads)}
            history_alive = bool(self._thread and self._thread.is_alive())
            calculation_alive = workers.get("custom-live-events", False)
            connection_alive = workers.get("custom-native-stream", False)
            return {
                "running": self._running
                and history_alive
                and calculation_alive
                and connection_alive,
                "requested_running": self._running,
                "history_worker_alive": history_alive,
                "calculation_worker_alive": calculation_alive,
                "connection_worker_alive": connection_alive,
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
                "refresh_target_seconds": None,
                **self.live.status(),
                "pending_or_stale_rule_symbols": max(
                    0,
                    self._jobs_requested - fresh_configured,
                ),
                "last_error": self._last_error,
                "history_last_error": self._history_last_error,
                "history_retry_waiting": sum(
                    due > self._clock() for due in self._history_retries.values()
                ),
                "worker_count": 3,
                "history_worker_count": 1,
                "calculation_worker_count": 1,
                "connection_worker_count": 1,
                "source": "borsapy_tradingview native BIST/BINANCE",
                "limits": {
                    "native_series": MAX_NATIVE_SERIES,
                    "native_rows": MAX_NATIVE_ROWS,
                    "results": MAX_RESULTS,
                    "result_cells": MAX_RESULT_CELLS,
                    "configurations": MAX_CONFIGS,
                    "preview_leases": MAX_PREVIEWS,
                    "history_retry_seconds": HISTORY_RETRY_SECONDS,
                    "history_retry_max_seconds": MAX_HISTORY_RETRY_SECONDS,
                },
                "one_second_coverage_guaranteed": False,
            }
