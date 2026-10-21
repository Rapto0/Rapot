"""Autonomous, bounded market input for private advanced alarms.

Snapshot/status are memory-only. Fixed workers own provider I/O; history may read
the bounded disk cache without authenticating it for alarms. The browser never
keeps this service alive. Quotes cannot manufacture OHLCV.
No unverified real-time entitlement or holiday calendar is implied.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import random
import re
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from application.services.advanced_alarm_conditions import (
    TIMEFRAMES,
    PreparedCondition,
    evaluate_prepared_condition,
    field_key,
    prepare_condition,
)
from application.services.advanced_alarm_data_cache import MAX_BARS, MarketCache
from application.services.advanced_alarm_data_provider import NativeMarketProvider
from application.services.advanced_alarm_series import (
    SECONDS,
    Series,
    SeriesError,
    calculate_series,
    candles,
    utc,
    validate_frame,
)
from settings import get_settings

MAX_HOT_SERIES = 128
MAX_SERIES = 4096
MAX_REFS = 128
MAX_VALUE_CELLS = 120000
MAX_REQUESTS = 18000
MAX_CHART_REQUESTS = 128
CHART_LEASE_SECONDS = 120
DURATIONS = {**SECONDS, "1d": 86400, "1wk": 604800, "1mo": 2678400}
Key = tuple[str, str, str]  # market, symbol, native timeframe


@dataclass(frozen=True, slots=True)
class Quote:
    price: float
    source: float
    received: float
    sequence: int


@dataclass(slots=True)
class Work:
    due: float = 0
    failures: int = 0
    busy: bool = False
    reason: str | None = None


class AdvancedMarketData:
    def __init__(self, settings=None, *, provider=None, cache=None, clock=None, jitter=None):
        self.settings = settings or get_settings()
        self._provider = provider  # Production adapter is lazy; import/start has no provider I/O.
        path = self.settings.advanced_alarm_cache_path
        self._cache = cache or MarketCache(
            Path(path)
            if path
            else Path(self.settings.database_path).parent / "advanced-market.sqlite3"
        )
        self._clock = clock or time.time
        self._jitter = jitter or random.random
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._threads: list[threading.Thread] = []
        self._running = False
        self._epoch = None
        self._generation = uuid.uuid4().hex
        self._reset_count = 0
        self._symbol_resets: dict[tuple[str, str], int] = {}
        self._rules: dict[str, tuple[dict, ...] | None] = {}
        self._plans: dict[tuple, tuple[dict, list[dict], PreparedCondition]] = {}
        self._universe: tuple[dict, ...] = ()
        self._universe_due = 0.0
        self._global_refs: dict[str, dict[str, dict]] = {}
        self._local_refs: dict[Key, dict[str, dict]] = {}
        self._explicit_bist: set[str] = set()
        self._crypto: set[str] = set()
        self._requests: OrderedDict[Key, Work] = OrderedDict()
        self._chart_leases: OrderedDict[Key, float] = OrderedDict()
        self._calculation_inputs: dict[Key, tuple] = {}
        self._active: set[Key] = set()
        self._requested_total = 0
        self._series: OrderedDict[Key, tuple[Series, Series | None]] = OrderedDict()
        self._series_sizes: dict[Key, int] = {}
        self._value_cells = 0
        self._hot: OrderedDict[Key, pd.DataFrame] = OrderedDict()
        self._quotes: dict[tuple[str, str], tuple[Quote, Quote | None]] = {}
        self._pending: dict[tuple[str, str], list[dict]] = {}
        self._connection = None
        self._subscriptions: tuple[str, ...] = ()
        self._retry_at = 0.0
        self._attempts = self._disconnects = self._coalesced = self._quote_sequence = 0
        self._crypto_due = 0.0
        self._crypto_cursor = 0
        self._work_turn = 0
        self._storage_error = False
        self._cache_bytes = 0
        self._state, self._message = "warming", "Sunucu piyasa verisi hazırlanıyor."
        self._custom = None
        self._update_listener = None

    def set_update_listener(self, callback):
        self._update_listener = callback
        if self._custom is not None:
            self._custom.live.set_listener(callback)

    @property
    def custom(self):
        with self._lock:
            if self._custom is None:
                from application.services.custom_indicator_data import CustomIndicatorData

                self._custom = CustomIndicatorData(clock=self._clock)
                self._custom.live.set_listener(self._update_listener)
                if self._running:
                    self._custom.start()
            return self._custom

    @property
    def enabled(self) -> bool:
        return bool(self.settings.advanced_alarm_market_enabled)

    def _continuity(self, market: str, symbol: str) -> str:
        return (
            f"{self._generation}:{self._reset_count}:{self._symbol_resets.get((market, symbol), 0)}"
        )

    def configure(self, rules: list[dict]) -> None:
        """Deduplicate all-universe references BEFORE expanding provider jobs."""
        memberships, global_refs, local_refs, plans = {}, {}, {}, {}
        explicit, crypto = set(), set()
        intern: dict[tuple, tuple[dict, ...]] = {}
        intern_refs: dict[tuple, list[dict]] = {}
        prepared_plans = {}
        for rule in rules:
            if not rule.get("enabled", True):
                continue
            condition_id = (rule["timeframe"], json.dumps(rule["condition"], sort_keys=True))
            if condition_id not in prepared_plans:
                prepared_plans[condition_id] = prepare_condition(
                    rule["condition"], rule["timeframe"]
                )
            prepared = prepared_plans[condition_id]
            refs = [dict(ref) for ref in prepared.fields]
            signature = tuple(field_key(ref, rule["timeframe"]) for ref in refs)
            intern_refs.setdefault(signature, refs.copy())
            plans[(str(rule["id"]), rule.get("revision", 0))] = (
                rule["condition"],
                intern_refs[signature],
                prepared,
            )
            # Bar-close price also requires the real primary candle series.
            refs = [ref for ref in refs if ref["field"] != "custom"]
            if refs and (rule.get("trigger") == "bar_close" or rule.get("mode") == "once_per_bar"):
                refs.append({"field": "close", "timeframe": rule["timeframe"]})
            all_bist = rule.get("scope") == "all_bist"
            members = tuple(
                sorted(
                    {
                        (item["market_type"], item["symbol"])
                        for item in rule.get("symbols", [])
                        if item.get("market_type") in {"BIST", "Kripto"}
                        and re.fullmatch(
                            r"[A-Z0-9]{1,20}"
                            if item.get("market_type") == "BIST"
                            else r"[A-Z0-9]{2,20}USDT",
                            item.get("symbol", ""),
                        )
                    }
                )
            )
            if all_bist:
                memberships[str(rule["id"])] = None
            else:
                if members not in intern:
                    intern[members] = tuple(
                        {"market_type": market, "symbol": symbol} for market, symbol in members
                    )
                memberships[str(rule["id"])] = intern[members]
            for market, symbol in members:
                target = explicit if market == "BIST" else crypto
                if len(target) < 2000:
                    target.add(symbol)
            for ref in refs:
                if ref["field"] == "price" and rule.get("trigger") != "bar_close":
                    continue
                tf, identity = ref["timeframe"], field_key(ref, rule["timeframe"])
                if all_bist:
                    target_refs = global_refs.setdefault(tf, {})
                    if len(target_refs) < MAX_REFS:
                        target_refs[identity] = ref
                else:
                    for market, symbol in members:
                        if symbol not in (explicit if market == "BIST" else crypto):
                            continue
                        key = (market, symbol, tf)
                        if key not in local_refs and len(local_refs) >= MAX_REQUESTS:
                            continue
                        target_refs = local_refs.setdefault(key, {})
                        if len(target_refs) < MAX_REFS:
                            target_refs[identity] = ref
        with self._lock:
            old_global, old_local = self._global_refs, self._local_refs
            self._rules, self._global_refs, self._local_refs = memberships, global_refs, local_refs
            self._plans = plans
            self._explicit_bist, self._crypto = explicit, crypto
            desired_symbols = (
                {("BIST", symbol) for symbol in explicit}
                | {("Kripto", symbol) for symbol in crypto}
                | {("BIST", item["symbol"]) for item in self._universe}
            )
            self._quotes = {
                key: value for key, value in self._quotes.items() if key in desired_symbols
            }
            self._pending = {
                key: value for key, value in self._pending.items() if key in desired_symbols
            }
            self._symbol_resets = {
                key: value for key, value in self._symbol_resets.items() if key in desired_symbols
            }
            self._rebuild_requests()
            # New field requirements must never reuse old calculations under a new identity.
            for key, work in self._requests.items():
                changed = old_local.get(key) != local_refs.get(key)
                if key[0] == "BIST":
                    changed |= old_global.get(key[2]) != global_refs.get(key[2])
                if changed:
                    work.due = min(work.due, self._clock())
        self._wake.set()
        if self._custom is not None or any(
            ref["field"] == "custom" for _, refs, _ in plans.values() for ref in refs
        ):
            self.custom.configure(rules, universe=self._universe)

    def _rebuild_requests(self) -> None:
        now = self._clock()
        self._chart_leases = OrderedDict(
            (key, expires) for key, expires in self._chart_leases.items() if expires > now
        )
        active = set(self._local_refs)
        for member in self._universe:
            for tf in self._global_refs:
                active.add(("BIST", member["symbol"], tf))
        # Universe quotes remain continuous. Native candles are needed only by
        # actual conditions and recently viewed charts, not by every price rule.
        desired = active | set(self._chart_leases)
        self._active = active
        self._requested_total = len(desired)
        ordered = sorted(active)[:MAX_REQUESTS]
        ordered.extend(sorted(desired - active)[: max(0, MAX_REQUESTS - len(ordered))])
        self._requests = OrderedDict(
            (key, self._requests[key] if key in self._requests else Work(due=now))
            for key in ordered
        )
        for key in list(self._series):
            if key not in self._requests:
                self._forget_series(key)
        for store in (self._hot, self._calculation_inputs):
            for key in list(store):
                if key not in self._requests:
                    store.pop(key, None)

    def _forget_series(self, key: Key) -> None:
        self._series.pop(key, None)
        self._calculation_inputs.pop(key, None)
        self._value_cells -= self._series_sizes.pop(key, 0)

    def _store_series(self, key: Key, pair: tuple[Series, Series | None]) -> None:
        self._forget_series(key)
        cells = sum(len(point.values) for series in pair if series for point in series.points)
        self._series[key] = pair
        self._series_sizes[key] = cells
        self._value_cells += cells
        while len(self._series) > MAX_SERIES or self._value_cells > MAX_VALUE_CELLS:
            self._forget_series(next(iter(self._series)))

    def symbols(self, rule_id) -> tuple[dict, ...]:
        with self._lock:
            members = self._rules.get(str(rule_id), ())
            return self._universe if members is None else members

    def symbol_count(self, rule_id) -> int:
        return len(self.symbols(rule_id))

    async def start(self) -> None:
        if not self.enabled:
            self._state, self._message = "disabled", "Sunucu veri servisi ayarlardan kapalı."
            return
        with self._lock:
            if self._running:
                return
            if self._provider is None:
                try:
                    self._provider = NativeMarketProvider()
                except Exception:
                    self._state, self._message = "error", "Piyasa veri servisi başlatılamadı."
                    raise RuntimeError(self._message) from None
            self._running = True
            self._stop.clear()
            workers = [self._connection_loop, self._poll_loop] + [
                self._history_loop
            ] * self.settings.advanced_alarm_history_workers
            self._threads = [
                threading.Thread(target=worker, name=f"alarm-market-{i}", daemon=True)
                for i, worker in enumerate(workers)
            ]
            for thread in self._threads:
                thread.start()
            if self._custom is not None:
                self._custom.start()

    async def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        with self._lock:
            connection, self._connection = self._connection, None
            self._invalidate("stopped", "Sunucu piyasa veri servisi durduruldu.")

        def finish():
            if self._custom is not None:
                self._custom.stop()
            if connection:
                connection.close()
            # Fixed workers use native provider timeouts. Do not abandon an in-flight thread.
            for thread in self._threads:
                thread.join()
            close_provider = getattr(self._provider, "close", None)
            if close_provider is not None:
                close_provider()
            self._cache.close()
            with self._lock:
                self._threads.clear()
                self._running = False

        completion = asyncio.create_task(asyncio.to_thread(finish))
        try:
            await asyncio.shield(completion)
        except asyncio.CancelledError:
            await completion
            raise

    def _invalidate(self, state: str, message: str) -> None:
        self._reset_count += 1
        self._quotes.clear()
        self._pending.clear()
        self._series.clear()
        self._series_sizes.clear()
        self._value_cells = 0
        self._hot.clear()
        self._calculation_inputs.clear()
        self._state, self._message = state, message
        if self._custom is not None:
            self._custom.invalidate()
        for work in self._requests.values():
            work.due = self._clock()

    def _connection_loop(self) -> None:
        try:
            saved = self._cache.load_universe()
            self._set_universe(saved)
        except Exception:
            self._storage_error = True
        while not self._stop.is_set():
            try:
                self.connection_step()
            except Exception:
                with self._lock:
                    connection, self._connection = self._connection, None
                    self._invalidate("error", "Piyasa bağlantısı yeniden denenecek.")
                    self._retry_at = self._clock() + 30
                if connection:
                    connection.close()
            self._stop.wait(1)

    def _set_universe(self, symbols: list[str]) -> None:
        normalize = getattr(self._provider, "filter_universe", None)
        if normalize is not None:
            symbols = normalize(symbols)
        symbols = sorted(
            {
                value
                for value in symbols
                if isinstance(value, str) and re.fullmatch(r"[A-Z0-9]{1,20}", value)
            }
        )[: self.settings.advanced_alarm_max_symbols]
        with self._lock:
            self._universe = tuple({"symbol": symbol, "market_type": "BIST"} for symbol in symbols)
            self._rebuild_requests()
            if self._custom is not None:
                self._custom.set_universe(self._universe)

    def connection_step(self) -> None:
        """One deterministic I/O step; called only by the connection worker in production."""
        now = self._clock()
        epoch = self._provider.epoch()
        with self._lock:
            if epoch != self._epoch:
                previous, self._connection = self._connection, None
                self._epoch = epoch
                self._invalidate("warming", "Hesap değişti; taze piyasa verisi bekleniyor.")
                self._retry_at = 0
            else:
                previous = None
        if previous:
            previous.close()
        if self._stop.is_set():
            return
        needs_universe = self.settings.advanced_alarm_all_bist_enabled or any(
            members is None for members in self._rules.values()
        )
        if needs_universe and now >= self._universe_due:
            self._universe_due = now + 300  # Failure retry is bounded too.
            try:
                symbols = self._provider.universe()
                if not symbols:
                    raise ValueError
                self._set_universe(symbols)
                self._universe_due = now + 21600
                try:
                    self._cache.save_universe([item["symbol"] for item in self._universe])
                except Exception:
                    self._storage_error = True
            except Exception:
                self._state, self._message = "warming", "BIST sembol evreni yenilenemedi."
        with self._lock:
            wanted = tuple(
                sorted(self._explicit_bist)
                + sorted(
                    ({item["symbol"] for item in self._universe} - self._explicit_bist)
                    if needs_universe
                    else ()
                )
            )[: self.settings.advanced_alarm_max_symbols]
            connection = self._connection
        if connection and (not connection.connected or wanted != self._subscriptions):
            rejected = connection.auth_failed
            connection.close()
            if rejected:
                self._provider.reset_auth(epoch)
                epoch = self._provider.epoch()
            with self._lock:
                self._epoch = epoch
                self._connection = None
                self._disconnects += 1
                self._attempts += 1
                self._invalidate("reconnecting", "Fiyat bağlantısı kesildi; yeniden bağlanıyor.")
                self._retry_at = now + min(60, 2 ** min(self._attempts, 5)) + self._jitter()
            connection = None
        if wanted and connection is None and now >= self._retry_at:
            with self._lock:
                generation = self._reset_count
            try:
                candidate = self._provider.open_quotes(
                    list(wanted),
                    lambda symbol, raw: self.enqueue_quote(symbol, raw, generation=generation),
                )
                if self._stop.is_set() or self._provider.epoch() != epoch:
                    candidate.close()
                    return
                with self._lock:
                    self._connection, self._subscriptions = candidate, wanted
                    self._state, self._message = "waiting", "Sağlayıcıdan taze fiyat bekleniyor."
            except Exception as exc:
                with self._lock:
                    self._attempts += 1
                    self._retry_at = now + min(60, 2 ** min(self._attempts, 6)) + self._jitter()
                    auth = getattr(exc, "status_code", None) in {401, 403, 409}
                    self._state = "auth_required" if auth else "reconnecting"
                    self._message = (
                        "TradingView hesabı doğrulanmalı; otomatik yeniden deneme bekleniyor."
                        if auth
                        else "Fiyat sağlayıcısına yeniden bağlanılacak."
                    )
        if self._crypto and now >= self._crypto_due and not self._stop.is_set():
            self._crypto_due = now + 5
            symbols = sorted(self._crypto)
            start = self._crypto_cursor % len(symbols)
            batch = (symbols[start:] + symbols[:start])[:100]
            self._crypto_cursor = (start + len(batch)) % len(symbols)
            try:
                for symbol, raw in self._provider.crypto_quotes(batch).items():
                    self.enqueue_quote(symbol, raw, market="Kripto")
            except Exception:
                self._crypto_due = now + 15

    def enqueue_quote(self, symbol: str, raw: dict, *, market="BIST", generation=None) -> None:
        """Callback only coalesces two actual ticks per symbol; no disk/network/calculation."""
        with self._lock:
            if self._stop.is_set() or (generation is not None and generation != self._reset_count):
                return
            key = (market, symbol)
            if key not in self._pending and len(self._pending) >= 4000:
                self._coalesced += 1
                return
            items = self._pending.setdefault(key, [])
            items.append(raw)
            if len(items) > 2:
                items.pop(0)
                self._coalesced += 1

    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            self.poll()
            self._stop.wait(1)

    def poll(self) -> None:
        now = self._clock()
        with self._lock:
            pending, self._pending = self._pending, {}
            for key, updates in pending.items():
                for raw in updates:
                    try:
                        price, source = float(raw["price"]), float(raw["source_timestamp"])
                        received = float(raw.get("received_at", now))
                        if not all(math.isfinite(v) for v in (price, source, received)):
                            raise ValueError
                        if price <= 0 or not 946684800 <= source <= now + 5 or received > now + 5:
                            raise ValueError
                    except (ValueError, TypeError, KeyError, OverflowError):
                        continue
                    prior = self._quotes.get(key, (None, None))[0]
                    if prior and source < prior.source:
                        self._symbol_resets[key] = self._symbol_resets.get(key, 0) + 1
                        self._quotes.pop(key, None)
                        continue
                    if prior and source == prior.source and price == prior.price:
                        continue  # Poll/repeated packet cannot freshen a provider observation.
                    if (
                        prior
                        and source - prior.source > self.settings.advanced_alarm_quote_stale_seconds
                    ):
                        self._symbol_resets[key] = self._symbol_resets.get(key, 0) + 1
                        prior = None
                    self._quote_sequence += 1
                    self._quotes[key] = (
                        Quote(price, source, received, self._quote_sequence),
                        prior,
                    )
                    if (
                        key[0] == "BIST"
                        and now - source <= self.settings.advanced_alarm_quote_stale_seconds
                    ):
                        self._attempts = 0

    def _refs(self, key: Key) -> list[dict]:
        market, _, timeframe = key
        refs = dict(self._global_refs.get(timeframe, {})) if market == "BIST" else {}
        refs.update(self._local_refs.get(key, {}))
        refs.setdefault(f"close:{timeframe}::", {"field": "close", "timeframe": timeframe})
        return list(refs.values())[:MAX_REFS]

    def _take_work(self) -> tuple[Key, list[dict], int, Work] | None:
        now = self._clock()
        with self._lock:
            if any(expires <= now for expires in self._chart_leases.values()):
                self._rebuild_requests()
            due = [key for key, work in self._requests.items() if not work.busy and work.due <= now]
            if not due:
                return None
            # Three alarm turns followed by one chart turn; sharing a chart with
            # an alarm still costs only one provider job.
            self._work_turn += 1
            prefer_active = self._work_turn % 4 != 0
            preferred = [key for key in due if (key in self._active) == prefer_active]
            key = min(preferred or due, key=lambda k: self._requests[k].due)
            self._requests[key].busy = True
            return key, self._refs(key), self._reset_count, self._requests[key]

    def _history_loop(self) -> None:
        while not self._stop.is_set():
            work = self._take_work()
            if work:
                self.fetch_history(*work)
            else:
                self._wake.wait(1)
                self._wake.clear()

    def fetch_history(
        self, key: Key, refs: list[dict], generation: int, selected_work: Work | None = None
    ) -> None:
        """Bounded I/O worker seam. Late results never resurrect a stopped/old account."""
        market, symbol, timeframe = key
        now = self._clock()
        with self._lock:
            symbol_generation = self._symbol_resets.get((market, symbol), 0)
            selected_work = selected_work or self._requests.get(key)
            if selected_work is None or self._requests.get(key) is not selected_work:
                return
            refs_signature = tuple(sorted(field_key(ref, timeframe) for ref in refs))

        def obsolete():
            return (
                self._stop.is_set()
                or generation != self._reset_count
                or symbol_generation != self._symbol_resets.get((market, symbol), 0)
                or self._requests.get(key) is not selected_work
                or refs_signature
                != tuple(sorted(field_key(ref, timeframe) for ref in self._refs(key)))
            )

        try:
            if obsolete():
                return
            provider_epoch = self._provider.epoch() if market == "BIST" else None
            if key not in self._hot:
                try:
                    saved = self._cache.load(":".join(key))
                    if saved and saved[0]:
                        cached = pd.DataFrame(saved[0]).set_index("time")
                        cached.index = pd.to_datetime(cached.index, unit="s", utc=True)
                        cached.columns = [column.title() for column in cached.columns]
                        cached.attrs["timeframe"] = timeframe
                        cached = validate_frame(cached, timeframe, market, self._clock())
                        with self._lock:
                            if not obsolete():
                                self._hot[key] = cached
                                while len(self._hot) > MAX_HOT_SERIES:
                                    self._hot.popitem(last=False)
                except Exception:
                    pass  # Cached history is optional and never authenticates a live signal.
            raw = self._provider.history(symbol, market, timeframe)
            frame = validate_frame(raw, timeframe, market, self._clock())
            with self._lock:
                anchors = tuple(
                    sorted(
                        {
                            point.end
                            for tf in TIMEFRAMES
                            if tf != timeframe
                            for pair in [self._series.get((market, symbol, tf))]
                            if pair
                            for point in [p for p in pair[0].points if p.confirmed][-2:]
                        }
                    )
                )
                old_frame = self._hot.get(key)
                old_result = self._series.get(key, (None, None))[0]
                # Full history participates: a revision outside the last four
                # bars must still recalculate indicators and reset continuity.
                same_frame = bool(
                    old_frame is not None
                    and old_frame.equals(frame)
                    and old_frame.attrs.get("volume_verified") == frame.attrs.get("volume_verified")
                )
                inputs = (refs_signature, anchors)
                reusable = bool(
                    same_frame
                    and old_result
                    and self._calculation_inputs.get(key) == inputs
                    and not any(
                        old_result.received < point.end <= self._clock()
                        for point in old_result.points
                    )
                )
            result = (
                replace(old_result, received=self._clock())
                if reusable
                else calculate_series(
                    frame, timeframe, market, refs, self._clock(), anchors=anchors
                )
            )
            if market == "BIST" and self._provider.epoch() != provider_epoch:
                return
            if obsolete():
                return
            try:
                if not same_frame or self._storage_error:
                    self._cache.save(":".join(key), candles(frame), result.received)
                    self._cache_bytes = self._cache.size()
                    self._storage_error = False
            except Exception:
                self._storage_error = True
            with self._lock:
                if obsolete():
                    return
                previous = self._series.get(key, (None, None))[0]
                previous_sample = self._series.get(key, (None, None))[1]
                old_frame = self._hot.get(key)
                discontinuity = bool(previous and result.received - previous.received > 180)
                # Without the retained or restored source frame, continuity
                # cannot be proven across a possible historical revision.
                discontinuity |= previous is not None and old_frame is None
                # Sparse native history is valid input, but a newly traversed gap
                # cannot connect old rule state to a later observed trading bar.
                discontinuity |= bool(
                    previous and any(gap > previous.source_time for gap in result.gaps)
                )
                discontinuity |= bool(previous and result.source_time < previous.source_time)
                if old_frame is not None:
                    # A removed/backfilled historical bar revises indicator inputs,
                    # even when all surviving prices and the latest time agree.
                    # Compare only the common retained window: normal rolling-tail
                    # truncation is not a provider revision.
                    start = max(old_frame.index[0], frame.index[0])
                    end = min(old_frame.index[-1], frame.index[-1])
                    old_window = old_frame.index[
                        (old_frame.index >= start) & (old_frame.index <= end)
                    ]
                    new_window = frame.index[(frame.index >= start) & (frame.index <= end)]
                    discontinuity |= not old_window.equals(new_window)
                    overlap = old_frame.index[:-1].intersection(frame.index)
                    discontinuity |= bool(
                        len(overlap) and not old_frame.loc[overlap].equals(frame.loc[overlap])
                    )
                if discontinuity:
                    # Provider revisions or observation gaps reset all native timeframes.
                    market_symbol = (market, symbol)
                    self._symbol_resets[market_symbol] = (
                        self._symbol_resets.get(market_symbol, 0) + 1
                    )
                    self._quotes.pop(market_symbol, None)
                    for other in list(self._series):
                        if other[:2] == market_symbol:
                            self._forget_series(other)
                    previous = previous_sample = None
                if previous and (
                    previous.version != result.version or previous.source_time != result.source_time
                ):
                    previous_sample = previous
                elif previous:
                    result = replace(result, changed=previous.changed)
                self._store_series(key, (result, previous_sample))
                if key in self._series:
                    self._calculation_inputs[key] = inputs
                self._hot[key] = frame
                self._hot.move_to_end(key)
                while len(self._hot) > MAX_HOT_SERIES:
                    self._hot.popitem(last=False)
                work = self._requests.get(key)
                if work:
                    work.reason, work.failures = None, 0
                    refresh = min(60, SECONDS.get(timeframe, 300) / 2)
                    work.due = self._clock() + max(10, refresh)
        except Exception as exc:
            with self._lock:
                work = self._requests.get(key)
                if work and not obsolete():
                    work.failures += 1
                    work.reason = exc.reason if isinstance(exc, SeriesError) else "provider"
                    work.due = now + min(300, 10 * 2 ** min(work.failures, 5))
                    self._forget_series(key)
                    self._hot.pop(key, None)
                    market_symbol = (market, symbol)
                    self._symbol_resets[market_symbol] = (
                        self._symbol_resets.get(market_symbol, 0) + 1
                    )
        finally:
            with self._lock:
                if self._requests.get(key) is selected_work:
                    selected_work.busy = False

    def _unknown(self, market: str, symbol: str, reason: str) -> dict:
        messages = {
            "auth": "TradingView hesabı doğrulanmalı.",
            "stale": "Veri eski; alarm için taze gözlem bekleniyor.",
            "gap": "Mum veya fiyat dizisi kesintili; yeni başlangıç bekleniyor.",
            "warming": "Koşul için yeterli ve kapanışı doğrulanmış veri bekleniyor.",
            "capacity": "Bu periyodun verisi sınırlı iş kuyruğunda bekliyor.",
            "provider": "Sağlayıcı verisi şu anda kullanılamıyor.",
            "invalid_data": "Sağlayıcının mum verisi doğrulanamadı.",
        }
        return {
            "ready": False,
            "reason": messages.get(reason, messages["provider"]),
            "continuity_reason": reason,
            "continuity_id": self._continuity(market, symbol),
            "matched": None,
            "previous_matched": None,
            "previous_ready": False,
            "value": None,
            "values": {},
            "observation_id": None,
            "observed_at": None,
            "bar_time": None,
            "source_timestamp": None,
        }

    def snapshot(self, rule: dict, symbol: dict, now: datetime | None = None) -> dict[str, Any]:
        current_time = now.timestamp() if now is not None else self._clock()
        if now is not None and now.tzinfo is None:
            raise ValueError("Gözlem zamanı saat dilimli olmalı.")
        market, name, timeframe = symbol["market_type"], symbol["symbol"], rule["timeframe"]
        with self._lock:
            return self._snapshot(rule, market, name, timeframe, current_time)

    def _snapshot(self, rule: dict, market: str, name: str, timeframe: str, now: float) -> dict:
        if not self.enabled or self._stop.is_set():
            return self._unknown(market, name, "provider")
        memory_epoch = getattr(self._provider, "memory_epoch", None)
        if market == "BIST" and memory_epoch is not None and memory_epoch() != self._epoch:
            return self._unknown(market, name, "auth")
        if market == "BIST" and self._connection is not None and not self._connection.connected:
            return self._unknown(market, name, "provider")
        if market == "BIST" and self._state == "auth_required":
            return self._unknown(market, name, "auth")
        plan = self._plans.get((str(rule.get("id")), rule.get("revision", 0)))
        prepared = (
            plan[2]
            if plan and plan[0] == rule["condition"]
            else prepare_condition(rule["condition"], timeframe)
        )
        refs = plan[1] if plan and plan[2] is prepared else prepared.fields
        closed = rule["trigger"] == "bar_close"
        custom_data = {}
        for ref in refs:
            if ref["field"] == "custom":
                custom = self.custom.observation(
                    ref, {"market_type": market, "symbol": name}, rule["trigger"], now
                )
                if not custom["ready"]:
                    result = self._unknown(market, name, "warming")
                    result["reason"] = custom["reason"]
                    return result
                custom_data[field_key(ref, timeframe)] = custom
        ordinary_refs = [ref for ref in refs if ref["field"] != "custom"]
        if custom_data and (
            not ordinary_refs
            or not closed
            and all(ref["field"] == "price" for ref in ordinary_refs)
        ):
            observations = list(custom_data.values())
            if (
                not closed
                and any(row.get("live_price") is not None for row in observations)
                and len({row["observation_id"] for row in observations}) != 1
            ):
                return self._unknown(market, name, "warming")
            if len({(row["bar_time"], row["bar_end"]) for row in observations}) != 1:
                return self._unknown(market, name, "warming")
            if (
                closed
                and len(
                    {(row["previous_bar_time"], row["previous_bar_end"]) for row in observations}
                )
                != 1
            ):
                return self._unknown(market, name, "warming")
            latest_update = max(row["observed_at"] for row in observations)
            result = evaluate_prepared_condition(
                prepared,
                lambda ref: (
                    observations[0].get("live_price"),
                    observations[0].get("previous_live_price"),
                )
                if ref["field"] == "price"
                else (
                    custom_data[field_key(ref, timeframe)]["current"],
                    custom_data[field_key(ref, timeframe)]["previous"]
                    if closed
                    or custom_data[field_key(ref, timeframe)]["observed_at"] == latest_update
                    else custom_data[field_key(ref, timeframe)]["current"],
                ),
            )
            if not result["ready"]:
                return self._unknown(market, name, "warming")
            return {
                **result,
                "continuity_reason": None,
                "continuity_id": ":".join(row["continuity_id"] for row in observations),
                "observation_id": hashlib.sha256(
                    "|".join(str(row["observation_id"]) for row in observations).encode()
                ).hexdigest()[:24],
                "observed_at": utc(max(row["observed_at"] for row in observations)),
                "bar_time": utc(observations[0]["bar_time"]),
                "source_timestamp": utc(min(row["source_timestamp"] for row in observations)),
            }
        data = {}
        for ref in ordinary_refs:
            if ref["field"] == "price" and not closed:
                continue
            key = (market, name, ref["timeframe"])
            pair = self._series.get(key)
            if pair is None:
                reason = self._requests.get(key, Work()).reason or "capacity"
                return self._unknown(market, name, reason)
            data[ref["timeframe"]] = pair
        if closed or rule.get("mode") == "once_per_bar":
            pair = self._series.get((market, name, timeframe))
            if not pair:
                return self._unknown(market, name, "warming")
            data[timeframe] = pair
        for tf, (series, _) in data.items():
            # Fetch time alone cannot make an old provider candle current.
            duration = DURATIONS[tf]
            if now - series.received > 180 or now - series.source_time > duration + 120:
                return self._unknown(market, name, "stale")
        quote_pair = self._quotes.get((market, name))
        if custom_data and not closed:
            custom_quote = next(iter(custom_data.values()))
            if custom_quote.get("live_price") is not None:
                quote_pair = (
                    Quote(
                        custom_quote["live_price"],
                        custom_quote["source_timestamp"],
                        custom_quote["observed_at"],
                        custom_quote["observation_id"],
                    ),
                    Quote(
                        custom_quote["previous_live_price"],
                        custom_quote["source_timestamp"],
                        custom_quote["observed_at"],
                        0,
                    )
                    if custom_quote.get("previous_live_price") is not None
                    else None,
                )
        needs_quote = any(ref["field"] == "price" for ref in refs) and not closed
        if needs_quote:
            if not quote_pair:
                return self._unknown(market, name, "warming")
            quote = quote_pair[0]
            if (
                max(now - quote.source, now - quote.received)
                > self.settings.advanced_alarm_quote_stale_seconds
            ):
                return self._unknown(market, name, "stale")
        observations, sources = [], []
        if closed:
            anchors = [point for point in data[timeframe][0].points if point.confirmed]
            if not anchors:
                return self._unknown(market, name, "warming")
            anchor, prior_anchor = anchors[-1], anchors[-2] if len(anchors) > 1 else None
            cutoff, prior_cutoff = anchor.end, prior_anchor.end if prior_anchor else None
            if custom_data:
                customs = list(custom_data.values())
                if (
                    len(
                        {
                            (
                                row["bar_time"],
                                row["bar_end"],
                                row["previous_bar_time"],
                                row["previous_bar_end"],
                            )
                            for row in customs
                        }
                    )
                    != 1
                ):
                    return self._unknown(market, name, "warming")
                selected = customs[0]
                if selected["bar_time"] != anchor.time or selected["previous_bar_time"] != (
                    prior_anchor.time if prior_anchor else None
                ):
                    return self._unknown(market, name, "warming")
                if selected["bar_end"] is None or (
                    prior_anchor and selected["previous_bar_end"] is None
                ):
                    return self._unknown(market, name, "warming")
                cutoff, prior_cutoff = selected["bar_end"], selected["previous_bar_end"]
            if anchor.segment != data[timeframe][0].points[-1].segment:
                return self._unknown(market, name, "gap")
            bar_time = anchor.time

            def resolve(ref):
                if ref["field"] == "custom":
                    custom = custom_data[field_key(ref, timeframe)]
                    sources.append(custom["source_timestamp"])
                    return custom["current"], custom["previous"]
                series = data[ref["timeframe"]][0]
                points = [p for p in series.points if p.confirmed and p.end <= cutoff]
                previous = [
                    p
                    for p in series.points
                    if p.confirmed and prior_cutoff and p.end <= prior_cutoff
                ]
                if custom_data and ref["timeframe"] == timeframe:
                    # The old daily reader uses a conservative midnight end.
                    # A matching, provider-confirmed primary candle is the same
                    # observation; never select a different date to compensate.
                    points = [p for p in series.points if p.confirmed and p.time == anchor.time]
                    previous = [
                        p
                        for p in series.points
                        if p.confirmed and prior_anchor and p.time == prior_anchor.time
                    ]
                key = field_key(ref, timeframe)
                sources.append(series.source_time)
                if points and previous and points[-1].segment != previous[-1].segment:
                    previous = []
                return (
                    points[-1].values.get(key) if points else None,
                    previous[-1].values.get(key) if previous else None,
                )

            observation = f"closed:{timeframe}:{anchor.time}"
            observed = max(series.received for series, _ in data.values())
        else:
            # Merge actual arrival observations. Unchanged fields carry into the
            # previous snapshot; only fields changed at the newest arrival step back.
            updates = [series.changed for series, _ in data.values()]
            updates.extend(item["observed_at"] for item in custom_data.values())
            if needs_quote:
                updates.append(quote_pair[0].received)
            newest = max(updates) if updates else now

            def resolve(ref):
                key = field_key(ref, timeframe)
                if ref["field"] == "custom":
                    custom = custom_data[key]
                    observations.append(str(custom["observation_id"]))
                    sources.append(custom["source_timestamp"])
                    return custom["current"], (
                        custom["previous"] if custom["observed_at"] == newest else custom["current"]
                    )
                if ref["field"] == "price":
                    current, previous = quote_pair
                    observations.append(f"q:{current.sequence}")
                    sources.append(current.source)
                    prior = previous.price if previous else None
                    return current.price, prior if current.received == newest else current.price
                current, previous = data[ref["timeframe"]]
                value = current.points[-1].values.get(key)
                prior = previous.points[-1].values.get(key) if previous else None
                observations.append(f"{ref['timeframe']}:{current.source_time}:{current.version}")
                sources.append(current.source_time)
                return value, prior if current.changed == newest else value

            primary = data.get(timeframe)
            bar_time = primary[0].points[-1].time if primary else None
            observed = newest
            observation = ""  # Filled from the references actually used below.
        result = evaluate_prepared_condition(prepared, resolve)
        if not result["ready"]:
            return self._unknown(market, name, "warming")
        if not closed:
            observation = hashlib.sha256("|".join(observations).encode()).hexdigest()[:24]
        return {
            **result,
            "continuity_reason": None,
            "continuity_id": self._continuity(market, name)
            + "".join(":" + item["continuity_id"] for item in custom_data.values()),
            "observation_id": observation,
            "observed_at": utc(observed),
            "bar_time": utc(bar_time),
            "source_timestamp": utc(min(sources)) if sources else None,
            "input_policy": "live_custom_with_last_fresh_native_technical"
            if custom_data and not closed
            else "native",
            "input_source_timestamps": {
                **{f"native:{tf}": utc(series.source_time) for tf, (series, _) in data.items()},
                **{
                    f"custom:{key}": utc(value["source_timestamp"])
                    for key, value in custom_data.items()
                },
            },
        }

    def history(self, symbol: str, market_type="BIST", timeframe="1m", limit=1000) -> dict:
        if (
            not re.fullmatch(
                r"[A-Z0-9]{1,20}" if market_type == "BIST" else r"[A-Z0-9]{2,20}USDT", symbol
            )
            or market_type not in {"BIST", "Kripto"}
            or timeframe not in TIMEFRAMES
        ):
            raise ValueError("Geçersiz mum isteği.")
        key = (market_type, symbol, timeframe)
        with self._lock:
            self._chart_leases[key] = self._clock() + CHART_LEASE_SECONDS
            self._chart_leases.move_to_end(key)
            while len(self._chart_leases) > MAX_CHART_REQUESTS:
                self._chart_leases.popitem(last=False)
            self._rebuild_requests()
            frame = self._hot.get(key)
            pair = self._series.get(key)
            generation = self._reset_count
            if frame is None:
                # Existing provider failures retain their retry backoff on HTTP polls.
                self._wake.set()
        cached_received = None
        if frame is None:
            # A hot-cache eviction is not loss of the persisted provider history.
            # Read outside the evaluation lock and never hydrate live indicators.
            try:
                saved = self._cache.load(":".join(key))
                if saved and saved[0]:
                    frame = pd.DataFrame(saved[0]).set_index("time")
                    frame.index = pd.to_datetime(frame.index, unit="s", utc=True)
                    frame.columns = [column.title() for column in frame.columns]
                    frame.attrs["timeframe"] = timeframe
                    frame = validate_frame(frame, timeframe, market_type, self._clock())
                    cached_received = saved[1]
            except Exception:
                frame = None
        with self._lock:
            if generation != self._reset_count:
                frame, pair = None, None
            available = frame is not None
            series = pair[0] if pair else None
            matching = bool(
                available and series and series.source_time == frame.index[-1].timestamp()
            )
            now = self._clock()
            fresh = bool(
                matching
                and now - series.received <= 180
                and now - series.source_time <= DURATIONS[timeframe] + 120
            )
            memory_epoch = getattr(self._provider, "memory_epoch", None)
            invalidated = self._stop.is_set() or (
                market_type == "BIST"
                and (
                    (memory_epoch is not None and memory_epoch() != self._epoch)
                    or (self._connection is not None and not self._connection.connected)
                    or self._state in {"auth_required", "reconnecting", "error", "stopped"}
                )
            )
            ready = fresh and cached_received is None and not invalidated
            closed = [p.time for p in series.points if p.confirmed] if matching else []
            state = (
                "ok"
                if ready
                else "stale"
                if matching and not fresh
                else "cached_unverified"
                if available
                else "waiting"
            )
            return {
                "candles": candles(frame, max(1, min(int(limit), MAX_BARS))) if available else [],
                "source": "borsapy_tradingview" if market_type == "BIST" else "binance",
                "state": state,
                "reason": None
                if ready
                else "Geçmiş veri eski; canlı alarm için taze gözlem bekleniyor."
                if state == "stale"
                else "Önbellek geçmişi canlı alarmda kullanılmaz."
                if available
                else "Mum verisi sırada.",
                "source_timestamp": utc(frame.index[-1].timestamp()) if available else None,
                "received_at": utc(
                    cached_received
                    if cached_received is not None
                    else series.received
                    if series
                    else None
                ),
                "closed_through": utc(closed[-1]) if closed else None,
                "realtime_verified": False,
            }

    def coverage(self) -> dict:
        """Bounded diagnostic view; no provider, history enqueue or disk access.

        The production share universe is a dated verified KAP snapshot. Explicit
        user symbols remain independent; a registry code is not a trading-status proof.
        Quote absence cannot distinguish an invalid code from an inactive security.
        This sampled view also cannot certify every intervening provider tick.
        """
        with self._lock:
            now = self._clock()
            candidates = {item["symbol"] for item in self._universe}
            describe = getattr(self._provider, "universe_metadata", None)
            universe_metadata = describe() if describe is not None else {}
            subscribed = set(self._subscriptions)
            all_symbols = candidates | subscribed | self._explicit_bist
            names = sorted(all_symbols)[:4000]
            memory_epoch = getattr(self._provider, "memory_epoch", None)
            connected = bool(self._connection and self._connection.connected)
            invalidated = (
                self._stop.is_set()
                or (memory_epoch is not None and memory_epoch() != self._epoch)
                or not connected
                or self._state in {"auth_required", "reconnecting", "error", "stopped"}
            )
            rows = []
            for name in names:
                quote_pair = self._quotes.get(("BIST", name))
                quote = quote_pair[0] if quote_pair else None
                quote_fresh = bool(
                    quote
                    and max(now - quote.source, now - quote.received)
                    <= self.settings.advanced_alarm_quote_stale_seconds
                )
                pair = self._series.get(("BIST", name, "1m"))
                series = pair[0] if pair else None
                work = self._requests.get(("BIST", name, "1m"))
                history_fresh = bool(
                    series and now - series.received <= 180 and now - series.source_time <= 180
                )
                closed = (
                    [point.time for point in series.points if point.confirmed] if series else []
                )
                rows.append(
                    {
                        "symbol": name,
                        "candidate": name in candidates,
                        "explicit": name in self._explicit_bist,
                        "subscribed": name in subscribed and connected,
                        "continuity_id": self._continuity("BIST", name),
                        "quote": {
                            "state": "invalidated"
                            if invalidated
                            else "missing"
                            if quote is None
                            else "fresh"
                            if quote_fresh
                            else "stale",
                            "source_timestamp": utc(quote.source) if quote else None,
                            "received_at": utc(quote.received) if quote else None,
                            "sequence": quote.sequence if quote else None,
                        },
                        "history_1m": {
                            "requested": work is not None,
                            "state": "invalidated"
                            if invalidated
                            else "missing"
                            if series is None
                            else "fresh"
                            if history_fresh
                            else "stale",
                            "source_timestamp": utc(series.source_time) if series else None,
                            "received_at": utc(series.received) if series else None,
                            "closed_through": utc(closed[-1]) if closed else None,
                            "native_gap_count": len(series.gaps) if series else None,
                            "request_reason": work.reason if work else None,
                            "request_failures": work.failures if work else 0,
                            "request_busy": bool(work and work.busy),
                            "request_due_at": utc(work.due) if work else None,
                        },
                    }
                )
            return {
                "schema": "rapot-advanced-coverage-v1",
                "observed_at": utc(now),
                "market": self.status(),
                "universe": {
                    "source": "borsapy_kap_company_codes",
                    "classification": "unverified_candidates",
                    "subscription_limit": self.settings.advanced_alarm_max_symbols,
                    "provider_source_total_known": False,
                    "equity_membership_verified": False,
                    "provider_resolution_verified": False,
                    **universe_metadata,
                    "candidate_count": len(candidates),
                    "universe_complete": len(candidates)
                    == universe_metadata.get("source_total_count"),
                },
                "rows": rows,
                "row_count": len(rows),
                "total_row_count": len(all_symbols),
                "rows_truncated": len(rows) != len(all_symbols),
                "provider_calls": False,
                "prices_included": False,
                "continuous_tick_capture": False,
                "realtime_entitlement_verified": False,
                "quote_freshness_policy_seconds": self.settings.advanced_alarm_quote_stale_seconds,
                "custom_indicators": self._custom.coverage() if self._custom is not None else None,
            }

    def status(self) -> dict:
        with self._lock:
            now = self._clock()
            describe = getattr(self._provider, "universe_metadata", None)
            universe_metadata = describe() if describe is not None else {}
            quotes = [pair[0] for pair in self._quotes.values()]
            fresh = sum(
                max(now - q.source, now - q.received)
                <= self.settings.advanced_alarm_quote_stale_seconds
                for q in quotes
            )
            valid_series = [
                pair[0]
                for key, pair in self._series.items()
                if now - pair[0].received <= 180
                and now - pair[0].source_time <= DURATIONS[key[2]] + 120
            ]
            memory_epoch = getattr(self._provider, "memory_epoch", None)
            invalidated = (
                self._stop.is_set()
                or (memory_epoch is not None and memory_epoch() != self._epoch)
                or (self._connection is not None and not self._connection.connected)
                or self._state in {"auth_required", "reconnecting", "error", "stopped"}
            )
            if invalidated:
                fresh, valid_series = 0, []
            tracked = len(self._subscriptions) + len(self._crypto)
            state = "ok" if fresh else self._state
            if self._storage_error:
                state = "storage_error"
            return {
                "enabled": self.enabled,
                "running": self._running,
                "state": state,
                "message": "Piyasa geçmişi diske kaydedilemiyor; kapasite ve disk rezervi kontrol edilmeli."
                if self._storage_error
                else "Taze gözlemler alınıyor; gecikmesiz piyasa kabulü yapılmadı."
                if fresh
                else self._message,
                "universe_count": len(self._universe),
                "universe_as_of": universe_metadata.get("audit_as_of"),
                "universe_source": universe_metadata.get("source"),
                "universe_source_count": universe_metadata.get("source_total_count"),
                "universe_equity_membership_verified": universe_metadata.get(
                    "equity_membership_verified", False
                ),
                "tracked_symbols": tracked,
                "subscribed_symbols": len(self._subscriptions)
                if self._connection and self._connection.connected
                else 0,
                "fresh_symbols": fresh,
                "stale_symbols": max(0, tracked - fresh),
                "history_ready": len(valid_series),
                "history_cached": len(self._series),
                "history_failures_by_reason": {
                    reason: sum(work.reason == reason for work in self._requests.values())
                    for reason in ("provider", "gap", "invalid_data")
                },
                "history_requested": max(self._requested_total, len(self._requests)),
                "history_scheduled": len(self._requests),
                "history_alarm_series": len(self._active),
                "history_chart_series": len(set(self._chart_leases) - self._active),
                "history_policy": "alarm_requirements_and_recent_charts",
                "history_pending": sum(
                    work.busy or work.due <= now for work in self._requests.values()
                ),
                "history_oldest_pending_seconds": max(
                    (
                        max(0, now - work.due)
                        for work in self._requests.values()
                        if work.busy or work.due <= now
                    ),
                    default=0,
                ),
                "history_capacity": MAX_SERIES,
                "indicator_value_capacity": MAX_VALUE_CELLS,
                "indicator_value_count": self._value_cells,
                "queue_coalesced": self._coalesced,
                "reconnect_attempts": self._attempts,
                "disconnects": self._disconnects,
                "next_retry_at": utc(self._retry_at) if self._retry_at > now else None,
                "oldest_history_age_seconds": max(
                    (now - s.received for s in valid_series), default=None
                ),
                "quote_age_seconds": max((now - q.received for q in quotes), default=None),
                "source_age_seconds": max((now - q.source for q in quotes), default=None),
                "cache_bytes": self._cache_bytes,
                "continuity_id": f"{self._generation}:{self._reset_count}",
                "realtime_verified": False,
                "one_second_coverage_guaranteed": False,
                "custom_indicators": self._custom.status() if self._custom is not None else None,
                "bar_finality_policy": "BIST son mumunun kapanışı sonraki gerçek sağlayıcı mumu ile doğrulanır; seans sonu teyidi gecikebilir. Tatil/yarım gün takvimi varsayılmaz.",
            }


_instance: AdvancedMarketData | None = None
_instance_lock = threading.Lock()


def get_advanced_market_data() -> AdvancedMarketData:
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = AdvancedMarketData()
        return _instance
