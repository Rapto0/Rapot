"""Ordered price-event execution over compact native indicator seeds.

Socket callbacks only enqueue. One event worker publishes all calculations for
one symbol atomically, then synchronously evaluates its alarms before processing
the next event. Provider/bootstrap I/O runs on other fixed workers.
"""

from __future__ import annotations

import math
import threading
from collections import OrderedDict, deque
from dataclasses import replace

from infrastructure.providers.custom_indicator_stream import MAX_LIVE_SERIES

MAX_LIVE_EVENTS = 8192
MAX_COMPILED_ROWS = 40960
MAX_LIVE_JOBS = 4096
MAX_LIVE_SEED_CELLS = 2_000_000
LIVE_STALE_SECONDS = 30
HISTORY_RECONCILIATION_SECONDS = 21600


class LiveIndicatorData:
    def __init__(self, owner):
        self.owner = owner
        self._lock = threading.RLock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._threads = []
        self._queue = deque()
        self._configs = {}
        self._members = {}
        self._wanted = set()
        self._requested = 0
        self._compiled = OrderedDict()
        self._buckets = {}
        self._previous_quotes = {}
        self._connection = None
        self._subscribed = set()
        self._retry = 0
        self._failures = 0
        self._serial = 0
        self._generation = 0
        self._overflow = self._processed = self._rejected = 0
        self._last_source = self._last_processed = self._last_lag = None
        self._listener = None
        self._enabled = False
        self._refused = set()
        self._blocked_jobs = 0
        self._extreme_waits = 0
        self._admitted_rule_jobs = 0
        self._admitted_cells = 0
        self._daily_witness_after = {}
        self._native_advances = 0
        self._last_transport_failures = ()

    def admitted(self, key):
        return key in self._configs

    def set_listener(self, listener):
        self._listener = listener

    def configure(self, jobs, *, rule_job_keys=()):
        """Jobs are the deduplicated configured and leased symbol/settings pairs."""
        members, configs, wanted, blocked, requested = {}, {}, set(), 0, set()
        from application.services.custom_indicators.live import estimate_live_cells

        estimates, cells = {}, 0
        for key, config in jobs:
            if key[2] not in estimates:
                estimates[key[2]] = estimate_live_cells(
                    config["indicator"], config["inputs"], config["chart_timeframe"]
                )
            cost = estimates[key[2]]
            required = {(*key[:2], row["timeframe"]) for row in config["requirements"]} | {
                (*key[:2], config["chart_timeframe"])
            }
            if key[0] == "BIST":
                required.add((*key[:2], "1D"))
            requested.update(required)
            if (
                len(configs) >= MAX_LIVE_JOBS
                or len(wanted | required) > MAX_LIVE_SERIES
                or cells + cost > MAX_LIVE_SEED_CELLS
            ):
                blocked += 1
                continue
            configs[key] = config
            cells += cost
            members.setdefault(key[:2], []).append(key)
            for row in config["requirements"]:
                wanted.add((*key[:2], row["timeframe"]))
            wanted.add((*key[:2], config["chart_timeframe"]))
            if key[0] == "BIST":
                wanted.add((*key[:2], "1D"))
        with self._lock:
            self._blocked_jobs = blocked
            self._admitted_cells = cells
            self._admitted_rule_jobs = len(set(configs).intersection(rule_job_keys))
            self._configs, self._members = configs, members
            self._previous_quotes = {
                key: value for key, value in self._previous_quotes.items() if key in members
            }
            self._daily_witness_after = {
                key: value for key, value in self._daily_witness_after.items() if key in members
            }
            self._refused.intersection_update(wanted)
            self._requested = len(requested)
            self._wanted = set(sorted(wanted)[:MAX_LIVE_SERIES])
            for key in list(self._compiled):
                if key not in configs:
                    self._compiled.pop(key)
            for key in list(self._buckets):
                if key not in self._wanted:
                    self._buckets.pop(key)
            if not configs:
                self._queue.clear()
                self._compiled.clear()
                self._previous_quotes.clear()
        self._wake.set()

    def start(self):
        if self._threads:
            return
        self._enabled = True
        self._stop.clear()
        self._threads = [
            threading.Thread(target=target, name=name, daemon=True)
            for target, name in (
                (self._control_loop, "custom-native-stream"),
                (self._event_loop, "custom-live-events"),
            )
        ]
        for thread in self._threads:
            thread.start()

    def stop(self):
        self._stop.set()
        self._wake.set()
        for thread in self._threads:
            thread.join()
        self._threads.clear()
        if self._connection:
            self._connection.close()
            self._connection = None
        self.invalidate()

    def invalidate(self):
        with self._lock:
            self._generation += 1
            self._queue.clear()
            self._compiled.clear()
            self._buckets.clear()
            self._previous_quotes.clear()
            self._refused.clear()
            self._daily_witness_after.clear()
        self._wake.set()

    def clear_comparisons(self, member=None):
        """Called in owner → live lock order after a broken source observation."""
        with self._lock:
            if member is None:
                self._compiled.clear()
                self._previous_quotes.clear()
            else:
                for key in self._members.get(member, ()):
                    self._compiled.pop(key, None)
                self._previous_quotes.pop(member, None)

    def enqueue(self, event, generation=None):
        with self._lock:
            if self._stop.is_set() or generation is not None and generation != self._generation:
                return
            if len(self._queue) >= MAX_LIVE_EVENTS:
                self._overflow += 1
                self._queue.clear()
                self._compiled.clear()
                self._buckets.clear()
                self._previous_quotes.clear()
                # The next worker turn discards every observation and rebuilds
                # native seeds; no missed edge is silently treated as continuous.
                self._queue.append({"kind": "gap"})
            self._queue.append(event)
        self._wake.set()

    def _control_loop(self):
        while not self._stop.is_set():
            self.control_step()
            self._stop.wait(1)

    def _remember_transport_failure(self, connection):
        status = getattr(connection, "status", lambda: {})()
        allowed = {
            "authentication_failed",
            "session_rate_limited",
            "provider_critical_error",
            "provider_protocol_error",
        }
        codes = tuple(code for code in status.get("failure_codes", ()) if code in allowed)
        if codes:
            self._last_transport_failures = codes

    def control_step(self):
        self.owner._sync_live()
        now = self.owner._clock()
        with self._lock:
            wanted = self._wanted.copy()
            connection = self._connection
        if not wanted:
            if connection:
                connection.close()
                self._connection = None
                self._subscribed.clear()
            return
        try:
            epoch = self.owner.provider.data_epoch()
            if connection and (connection.epoch != epoch or not connection.connected):
                self._remember_transport_failure(connection)
                connection.close()
                self._connection = None
                self._subscribed.clear()
                self.invalidate()
                self.owner.live_gap(
                    "Native canlı bağlantı kesildi; yeni mum başlangıcı bekleniyor."
                )
                self._failures += 1
                self._retry = now + min(60, 2 ** min(self._failures, 5))
                connection = None
            if connection is None:
                if now < self._retry:
                    return
                generation = self._generation
                connection = self.owner.provider.create_custom_indicator_stream(
                    lambda event: self.enqueue(event, generation)
                )
                self._connection = connection
            if wanted != self._subscribed or getattr(connection, "needs_reconcile", False):
                connection.configure(wanted)
                self._subscribed = wanted
            if not connection.connected:
                raise ValueError("Native stream is not connected")
            self._failures = 0
        except Exception:
            if self._connection:
                self._remember_transport_failure(self._connection)
                self._connection.close()
            self._connection = None
            self._subscribed.clear()
            self.invalidate()
            self.owner.live_gap(
                "Native canlı gösterge akışı hazır değil; yeniden bağlantı bekleniyor."
            )
            self._failures += 1
            self._retry = now + min(60, 2 ** min(self._failures, 5))

    def _event_loop(self):
        while not self._stop.is_set():
            try:
                if not self.process_event():
                    self._wake.wait(0.1)
                    self._wake.clear()
            except Exception:
                self.invalidate()
                self.owner.live_gap("Canlı değerlendirme tamamlanamadı; devamlılık sıfırlandı.")
                if self._connection:
                    self._connection.close()

    def process_event(self):
        with self._lock:
            event = self._queue.popleft() if self._queue else None
        if event is None:
            return False
        if event["kind"] == "gap":
            self.owner.live_gap("Canlı gösterge kuyruğu taştı; devamlılık sıfırlandı.")
            # Current native identity must be witnessed again after lost packets.
            if self._connection:
                self._connection.close()
        elif event["kind"] == "bars":
            with self.owner._publication_lock:
                self._bars(event)
        elif event["kind"] == "quote":
            with self.owner._publication_lock:
                self._quote(event)
        elif event["kind"] == "rejected":
            key = tuple(event["key"])
            with self._lock:
                self._refused.add(key)
            self.owner.live_gap("Sağlayıcı bu native sembol/periyot aboneliğini reddetti.", key[:2])
        return True

    def _bars(self, event):
        import pandas as pd

        from application.services.custom_indicator_data import native_bars

        key = tuple(event["key"])
        with self._lock:
            if key not in self._wanted:
                return
        rows = event["rows"]
        if len(rows) < 2:
            return
        try:
            frame = pd.DataFrame(
                [row[1:] for row in rows],
                columns=["Open", "High", "Low", "Close"],
                index=pd.to_datetime([row[0] for row in rows], unit="s", utc=True),
            )
            frame.attrs.update(native_timeframe=key[2], session_metadata=event["metadata"])
            points = native_bars(frame, key[2], key[0], self.owner._clock())
            # A following provider bar witnesses the prior bar, even when the
            # exact exchange close timestamp of a multi-day/week bar is absent.
            points = (replace(points[-2], confirmed=True), replace(points[-1], confirmed=False))
        except Exception:
            self.owner.live_gap("Native canlı mum paketi doğrulanamadı.", key[:2])
            return
        dirty = rollover = False
        refresh = set()
        with self._lock:
            old = self._buckets.get(key)
            if old and (
                points[-1].time < old[0][-1].time
                or points[-1].time == old[0][-1].time
                and points[-2] != old[0][-2]
            ):
                dirty = True
            if old and points[-1].time != old[0][-1].time:
                dirty = True
                rollover = points[-1].time > old[0][-1].time and points[-2].time == old[0][-1].time
            if (
                old
                and points[-1].time == old[0][-1].time
                and (
                    points[-1].high < old[0][-1].high
                    or points[-1].low > old[0][-1].low
                    or points[-1].open != old[0][-1].open
                )
            ):
                dirty = True
            self._buckets[key] = (points, event["received_at"])
            if rollover:
                if key[0] == "BIST" and key[2] == "1D":
                    self._daily_witness_after[key[:2]] = event["received_at"]
                for item in self._members.get(key[:2], ()):
                    compiled = self._compiled.get(item)
                    if compiled is None or key[2] not in compiled["buckets"]:
                        continue
                    opening = points[-1].open
                    current = replace(points[-1], high=opening, low=opening, close=opening)
                    required = key[2] in compiled["evaluator"].required_timeframes
                    if required and not compiled["evaluator"].advance_native(
                        key[2], points[-2], current
                    ):
                        self._compiled.pop(item, None)
                        refresh.add(item)
                        continue
                    compiled["buckets"][key[2]] = current
                    compiled["pending_extremes"].pop(key[2], None)
                    self._native_advances += 1
                    if (
                        item[2] in self.owner._closed_configs
                        and key[2] == self._configs[item]["chart_timeframe"]
                    ):
                        refresh.add(item)
                self._stage_extremes(key, points[-1], event["received_at"])
            elif dirty:
                for item in self._members.get(key[:2], ()):
                    if key[2] in {row["timeframe"] for row in self._configs[item]["requirements"]}:
                        self._compiled.pop(item, None)
            else:
                self._stage_extremes(key, points[-1], event["received_at"])
        if dirty:
            if rollover:
                self.owner.native_advanced(key, points[-2], points[-1])
            if rollover and refresh:
                self.owner.native_refresh(key, jobs=refresh, invalidate_native=False)
            elif not rollover:
                self.owner.live_gap(
                    "Native mum başlangıcı/geçmişi değişti; gösterge yeniden hazırlanıyor.",
                    key[:2],
                    native_key=key,
                )
        self.owner._wake.set()

    def prepare_seed(self, config, frames, epoch):
        from application.services.custom_indicators.catalog import compile_live

        # This runs only on the existing fixed history worker. No full-history
        # arrays are retained by the compiled evaluator.
        evaluator = compile_live(
            config["indicator"], config["inputs"], frames, chart_timeframe=config["chart_timeframe"]
        )
        current = {tf: frame[-1] for tf, frame in frames.items()}
        return {
            "evaluator": evaluator,
            "buckets": current,
            "epoch": epoch,
            "watermark": math.ceil(self.owner._clock()),
            "seeded": self.owner._clock(),
            "pending_extremes": {},
        }

    def install_seed(self, key, prepared, *, generation):
        with self._lock:
            if (
                key not in self._configs
                or self._stop.is_set()
                or generation != self.owner._generation
            ):
                return
            mismatches = [
                (*key[:2], tf)
                for tf, bucket in prepared["buckets"].items()
                if (witness := self._buckets.get((*key[:2], tf))) is not None
                and witness[0][-1].time != bucket.time
            ]
            if not mismatches:
                self._compiled[key] = prepared
                self._compiled.move_to_end(key)
        # Never acquire the owner's lock while retaining the live-state lock.
        for native_key in mismatches:
            self.owner.native_refresh(native_key, jobs={key})

    def retains_seed(self, key, prepared):
        with self._lock:
            current = self._compiled.get(key)
            return bool(
                current
                and current["epoch"] == prepared["epoch"]
                and {tf: bar.time for tf, bar in current["buckets"].items()}
                == {tf: bar.time for tf, bar in prepared["buckets"].items()}
            )

    def has_seed(self, key, epoch):
        with self._lock:
            return bool((current := self._compiled.get(key)) and current["epoch"] == epoch)

    def native_continuity(self, key, epoch):
        with self._lock:
            return bool(
                self._connection
                and self._connection.connected
                and any(
                    (compiled := self._compiled.get(item))
                    and compiled["epoch"] == epoch
                    and key[2] in compiled["buckets"]
                    for item in self._members.get(key[:2], ())
                )
            )

    def _stage_extremes(self, key, native, received):
        for item in self._members.get(key[:2], ()):
            compiled = self._compiled.get(item)
            if (
                compiled is None
                or self._configs[item]["indicator"] != "smi_votes"
                or key[2] not in compiled["evaluator"].required_timeframes
            ):
                continue
            bucket = compiled["buckets"][key[2]]
            hi, lo = compiled["evaluator"].current_range(key[2]) or (bucket.high, bucket.low)
            hi, lo = max(hi, bucket.high), min(lo, bucket.low)
            if native.high > hi or native.low < lo:
                pending = compiled["pending_extremes"].get(key[2])
                compiled["pending_extremes"][key[2]] = (
                    max(native.high, pending[0] if pending else hi),
                    min(native.low, pending[1] if pending else lo),
                    max(math.ceil(received), pending[2] if pending else 0),
                )

    def _live_buckets(self, compiled, needed, price, source, *, smi):
        buckets = {tf: compiled["buckets"][tf] for tf in needed}
        waiting = False
        if not smi:
            return buckets, waiting
        for tf, bucket in buckets.items():
            bucket = replace(bucket, high=max(bucket.high, price), low=min(bucket.low, price))
            compiled["buckets"][tf] = buckets[tf] = bucket
            pending = compiled["pending_extremes"].get(tf)
            if not pending:
                continue
            hi, lo = compiled["evaluator"].current_range(tf) or (bucket.high, bucket.low)
            covered = max(hi, bucket.high) >= pending[0] and min(lo, bucket.low) <= pending[1]
            if source >= pending[2] or covered:
                bucket = replace(
                    bucket, high=max(bucket.high, pending[0]), low=min(bucket.low, pending[1])
                )
                compiled["buckets"][tf] = buckets[tf] = bucket
                compiled["pending_extremes"].pop(tf)
            else:
                waiting = True
        return buckets, waiting

    def _quote(self, event):
        member, now = tuple(event["member"]), self.owner._clock()
        publication_epoch = self.owner.publication_token(member)
        epoch = self.owner.provider.memory_epoch()
        try:
            price, source, received = (
                float(event[key]) for key in ("price", "source_timestamp", "received_at")
            )
            if (
                not all(math.isfinite(value) for value in (price, source, received))
                or price <= 0
                or not 946684800 <= source <= now + 5
                or received > now + 5
                or max(now - source, now - received) > LIVE_STALE_SECONDS
            ):
                raise ValueError
        except (ValueError, KeyError, TypeError, OverflowError):
            self._rejected += 1
            self.owner.live_gap("Canlı fiyat eski veya geçersiz; yeni gözlem bekleniyor.", member)
            return
        updates = []
        with self._lock:
            live_generation = self._generation
            keys = self._members.get(member, ())
            if not keys:
                return
            previous = self._previous_quotes.get(member)
            if previous and source == previous[0] and price == previous[1]:
                return
            if previous and source < previous[0]:
                self._rejected += 1
                for key in keys:
                    self._compiled.pop(key, None)
                self._previous_quotes.pop(member, None)
                gap = True
            else:
                gap = False
                self._previous_quotes[member] = source, price
            if not gap:
                for key in keys:
                    config = self._configs[key]
                    compiled = self._compiled.get(key)
                    reason, point = (
                        "Canlı gösterge için native başlangıç verisi hazırlanıyor.",
                        None,
                    )
                    if (
                        compiled
                        and compiled["epoch"] == epoch
                        and source >= math.floor(compiled["seeded"])
                    ):
                        needed = set(compiled["evaluator"].required_timeframes) | {
                            config["chart_timeframe"]
                        }
                        if member[0] == "BIST":
                            needed.add("1D")
                        witnessed = {tf: self._buckets.get((*member, tf)) for tf in needed}
                        if all(
                            (*member, tf) not in self._refused
                            and value is not None
                            and value[0][-1].time == compiled["buckets"][tf].time
                            and source >= value[0][-1].time
                            and (value[0][-1].end is None or source < value[0][-1].end)
                            and (
                                value[0][-1].end is not None
                                or value[1] >= self._daily_witness_after.get(member, 0)
                            )
                            for tf, value in witnessed.items()
                        ):
                            buckets, extreme_wait = self._live_buckets(
                                compiled,
                                needed,
                                price,
                                source,
                                smi=config["indicator"] == "smi_votes",
                            )
                            if source < compiled["watermark"]:
                                # Same-second quotes after bootstrap can widen
                                # SMI extrema even though their coarse source
                                # timestamp cannot establish a signal boundary.
                                for tf, bucket in buckets.items():
                                    compiled["buckets"][tf] = replace(
                                        bucket,
                                        high=max(bucket.high, price),
                                        low=min(bucket.low, price),
                                    )
                                point = {
                                    "outputs": {},
                                    "rows": [],
                                    "ready": False,
                                    "reason": "Başlangıçtan sonraki ilk zaman damgası bekleniyor.",
                                }
                            elif extreme_wait:
                                self._extreme_waits += 1
                                compiled["evaluator"].pause_signal_baseline()
                                point = {
                                    "outputs": {},
                                    "rows": [],
                                    "ready": False,
                                    "reason": "Native H/L güncellemesinin fiyat zaman damgasıyla eşleşmesi bekleniyor.",
                                }
                            else:
                                # Freeze seed extremes; later native updates cannot
                                # leak future H/L into an older queued quote.
                                point = compiled["evaluator"].evaluate(
                                    price=price, as_of=source, buckets=buckets
                                )
                            reason = point.get("reason")
                        else:
                            reason = (
                                "Native zaman dilimleri aynı canlı mum başlangıcını doğrulamıyor."
                            )
                    base = compiled["buckets"].get(config["chart_timeframe"]) if compiled else None
                    if point is None:
                        point = {"outputs": {}, "rows": [], "ready": False, "reason": reason}
                    point = {
                        "time": base.time if base else None,
                        "end": base.end if base else None,
                        "confirmed": False,
                        **point,
                    }
                    updates.append((key, config, point))
                self._serial += 1
                serial = self._serial
        if gap:
            self.owner.live_gap(
                "Canlı fiyat sırasında boşluk/sıra değişimi görüldü; başlangıç yenileniyor.", member
            )
            return
        if not self.owner.publish_live(
            updates,
            source=source,
            received=received,
            serial=serial,
            price=price,
            publication_epoch=publication_epoch,
            live_generation=live_generation,
            expected_epoch=epoch,
        ):
            self._rejected += 1
            with self._lock:
                for key in self._members.get(member, ()):
                    self._compiled.pop(key, None)
            self.owner.live_gap(
                "Canlı gözlem yayımlanmadan kaynak değişti; başlangıç yenileniyor.", member
            )
            return
        self._last_source, self._last_processed = source, self.owner._clock()
        self._last_lag = max(0, self._last_processed - source)
        # A complete symbol observation is visible before synchronous targeted
        # alarm evaluation. The next price cannot overwrite a transient edge.
        if self._listener:
            self._listener(*member)
        self._processed += 1

    def status(self):
        with self._lock:
            transport = self._connection.status() if self._connection else {}
            return {
                "update_mode": "live_price_events",
                "live_queue_pending": len(self._queue),
                "live_queue_limit": MAX_LIVE_EVENTS,
                "live_overflow_count": self._overflow,
                "live_rejected": self._rejected,
                "live_processed": self._processed,
                "last_live_source_at": self._last_source,
                "last_live_processed_at": self._last_processed,
                "last_live_lag_seconds": self._last_lag,
                "native_subscriptions_requested": self._requested,
                "native_subscriptions_admitted": len(self._wanted),
                "native_subscriptions_blocked": max(0, self._requested - len(self._wanted)),
                "native_streams_connected": transport.get("connected", 0),
                "native_subscriptions_registered": transport.get("subscriptions", 0),
                "native_subscriptions_pending": transport.get("subscriptions_pending", 0),
                "last_native_failure_codes": list(self._last_transport_failures),
                "compiled_configurations": len(self._compiled),
                "blocked_rule_symbols": max(
                    0, self.owner._jobs_requested - self._admitted_rule_jobs
                ),
                "refused_native_series": len(self._refused),
                "native_extreme_waits": self._extreme_waits,
                "compiled_rows": sum(
                    len(item["evaluator"].rows) for item in self._compiled.values()
                ),
                "compiled_row_limit": MAX_COMPILED_ROWS,
                "admitted_seed_cells": self._admitted_cells,
                "seed_cell_limit": MAX_LIVE_SEED_CELLS,
                "native_seed_advances": self._native_advances,
                "history_reconciliation_seconds": HISTORY_RECONCILIATION_SECONDS,
            }
