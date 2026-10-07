"""Autonomous, bounded market input for private advanced alarms.

Snapshot/status are memory-only. Fixed workers own provider I/O; history may read
the bounded disk cache without authenticating it for alarms. The browser never
keeps this service alive. Quotes cannot manufacture OHLCV.
No unverified real-time entitlement or holiday calendar is implied.
"""

from __future__ import annotations

import asyncio
import hashlib
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
    condition_fields,
    evaluate_condition,
    field_key,
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
        self._plans: dict[tuple, tuple[dict, list[dict]]] = {}
        self._universe: tuple[dict, ...] = ()
        self._universe_due = 0.0
        self._global_refs: dict[str, dict[str, dict]] = {}
        self._local_refs: dict[Key, dict[str, dict]] = {}
        self._explicit_bist: set[str] = set()
        self._crypto: set[str] = set()
        self._requests: OrderedDict[Key, Work] = OrderedDict()
        self._active: set[Key] = set()
        self._requested_total = 0
        self._series: OrderedDict[Key, tuple[Series, Series | None]] = OrderedDict()
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
        for rule in rules:
            if not rule.get("enabled", True):
                continue
            refs = condition_fields(rule["condition"], rule["timeframe"])
            signature = tuple(field_key(ref, rule["timeframe"]) for ref in refs)
            intern_refs.setdefault(signature, refs.copy())
            plans[(str(rule["id"]), rule.get("revision", 0))] = (
                rule["condition"],
                intern_refs[signature],
            )
            # Bar-close price also requires the real primary candle series.
            if rule.get("trigger") == "bar_close" or rule.get("mode") == "once_per_bar":
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

    def _rebuild_requests(self) -> None:
        active = set(self._local_refs)
        for member in self._universe:
            for tf in self._global_refs:
                active.add(("BIST", member["symbol"], tf))
        desired = set(active)
        if self.settings.advanced_alarm_all_bist_enabled:
            desired.update(("BIST", member["symbol"], "1m") for member in self._universe)
        self._active = active
        self._requested_total = len(desired)
        self._requests = OrderedDict(
            (key, self._requests.get(key, Work())) for key in sorted(desired)[:MAX_REQUESTS]
        )

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

    async def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        with self._lock:
            connection, self._connection = self._connection, None
            self._invalidate("stopped", "Sunucu piyasa veri servisi durduruldu.")

        def finish():
            if connection:
                connection.close()
            # Fixed workers use native provider timeouts. Do not abandon an in-flight thread.
            for thread in self._threads:
                thread.join()
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
        self._hot.clear()
        self._state, self._message = state, message
        for work in self._requests.values():
            work.due = 0

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
                + sorted({item["symbol"] for item in self._universe} - self._explicit_bist)
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

    def _take_work(self) -> tuple[Key, list[dict], int] | None:
        now = self._clock()
        with self._lock:
            due = [key for key, work in self._requests.items() if not work.busy and work.due <= now]
            if not due:
                return None
            # Three active turns followed by one background turn; no starvation in
            # either direction when thousands of all-universe minute jobs are due.
            self._work_turn += 1
            prefer_active = self._work_turn % 4 != 0
            preferred = [key for key in due if (key in self._active) == prefer_active]
            key = min(preferred or due, key=lambda k: self._requests[k].due)
            self._requests[key].busy = True
            return key, self._refs(key), self._reset_count

    def _history_loop(self) -> None:
        while not self._stop.is_set():
            work = self._take_work()
            if work:
                self.fetch_history(*work)
            else:
                self._wake.wait(1)
                self._wake.clear()

    def fetch_history(self, key: Key, refs: list[dict], generation: int) -> None:
        """Bounded I/O worker seam. Late results never resurrect a stopped/old account."""
        market, symbol, timeframe = key
        now = self._clock()
        with self._lock:
            symbol_generation = self._symbol_resets.get((market, symbol), 0)
        try:
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
                            if generation == self._reset_count and not self._stop.is_set():
                                self._hot[key] = cached
                                while len(self._hot) > MAX_HOT_SERIES:
                                    self._hot.popitem(last=False)
                except Exception:
                    pass  # Cached history is optional and never authenticates a live signal.
            raw = self._provider.history(symbol, market, timeframe)
            frame = validate_frame(raw, timeframe, market, self._clock())
            with self._lock:
                anchors = tuple(
                    {
                        point.end
                        for tf in TIMEFRAMES
                        if tf != timeframe
                        for pair in [self._series.get((market, symbol, tf))]
                        if pair
                        for point in [p for p in pair[0].points if p.confirmed][-2:]
                    }
                )
            result = calculate_series(
                frame, timeframe, market, refs, self._clock(), anchors=anchors
            )
            if market == "BIST" and self._provider.epoch() != provider_epoch:
                return
            if (
                self._stop.is_set()
                or generation != self._reset_count
                or symbol_generation != self._symbol_resets.get((market, symbol), 0)
            ):
                return
            try:
                self._cache.save(":".join(key), candles(frame), result.received)
                self._cache_bytes = self._cache.size()
                self._storage_error = False
            except Exception:
                self._storage_error = True
            with self._lock:
                if (
                    self._stop.is_set()
                    or generation != self._reset_count
                    or symbol_generation != self._symbol_resets.get((market, symbol), 0)
                ):
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
                            self._series.pop(other, None)
                    previous = previous_sample = None
                if previous and (
                    previous.version != result.version or previous.source_time != result.source_time
                ):
                    previous_sample = previous
                elif previous:
                    result = replace(result, changed=previous.changed)
                self._series[key] = (result, previous_sample)
                self._series.move_to_end(key)
                while len(self._series) > MAX_SERIES:
                    self._series.popitem(last=False)
                cells = sum(
                    sum(len(point.values) for point in series.points)
                    for pair in self._series.values()
                    for series in pair
                    if series is not None
                )
                while cells > MAX_VALUE_CELLS:
                    _, removed = self._series.popitem(last=False)
                    cells -= sum(
                        len(point.values) for series in removed if series for point in series.points
                    )
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
                if work:
                    work.failures += 1
                    work.reason = exc.reason if isinstance(exc, SeriesError) else "provider"
                    work.due = now + min(300, 10 * 2 ** min(work.failures, 5))
                    self._series.pop(key, None)
                    self._hot.pop(key, None)
                    market_symbol = (market, symbol)
                    self._symbol_resets[market_symbol] = (
                        self._symbol_resets.get(market_symbol, 0) + 1
                    )
        finally:
            with self._lock:
                if key in self._requests:
                    self._requests[key].busy = False

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
        refs = (
            plan[1]
            if plan and plan[0] == rule["condition"]
            else condition_fields(rule["condition"], timeframe)
        )
        closed = rule["trigger"] == "bar_close"
        data = {}
        for ref in refs:
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
            if anchor.segment != data[timeframe][0].points[-1].segment:
                return self._unknown(market, name, "gap")
            bar_time = anchor.time

            def resolve(ref):
                series = data[ref["timeframe"]][0]
                points = [p for p in series.points if p.confirmed and p.end <= anchor.end]
                previous = [
                    p
                    for p in series.points
                    if p.confirmed and prior_anchor and p.end <= prior_anchor.end
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
            if needs_quote:
                updates.append(quote_pair[0].received)
            newest = max(updates) if updates else now

            def resolve(ref):
                key = field_key(ref, timeframe)
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
        result = evaluate_condition(rule["condition"], resolve, timeframe)
        if not result["ready"]:
            return self._unknown(market, name, "warming")
        if not closed:
            observation = hashlib.sha256("|".join(observations).encode()).hexdigest()[:24]
        return {
            **result,
            "continuity_reason": None,
            "continuity_id": self._continuity(market, name),
            "observation_id": observation,
            "observed_at": utc(observed),
            "bar_time": utc(bar_time),
            "source_timestamp": utc(min(sources)) if sources else None,
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
            frame = self._hot.get(key)
            pair = self._series.get(key)
            generation = self._reset_count
            if frame is None:
                if key not in self._requests and len(self._requests) < MAX_REQUESTS:
                    self._requests[key] = Work()
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

    def status(self) -> dict:
        with self._lock:
            now = self._clock()
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
                "history_pending": sum(
                    work.busy or work.due <= now for work in self._requests.values()
                ),
                "history_capacity": MAX_SERIES,
                "indicator_value_capacity": MAX_VALUE_CELLS,
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
