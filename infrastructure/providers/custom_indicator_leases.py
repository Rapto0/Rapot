"""Native long-period witnesses with bounded temporary chart-session leases.

No calendar reconstruction is performed here. A native, semantically accepted
daily candle identifies the current trading day. Long-period witnesses are
valid only for that daily generation, and only after the consumer ACKs them.
"""

from __future__ import annotations

import re
import threading
import uuid

LEASE_SLOTS_PER_CONNECTION = 32
LEASE_TIMEOUT_SECONDS = 30
LEASE_RETRY_BASE_SECONDS = 30
LEASE_RETRY_MAX_SECONDS = 1800


def is_leased_timeframe(timeframe):
    """Intraday and 1D stay persistent; other native D/W/M periods can lease."""
    return bool(re.fullmatch(r"[1-9][0-9]*[DWM]", str(timeframe))) and timeframe != "1D"


def persistent_keys(keys):
    result = {key for key in keys if not is_leased_timeframe(key[2])}
    result.update((*key[:2], "1D") for key in keys if is_leased_timeframe(key[2]))
    return result


class NativeLeaseBook:
    """Thread-safe bookkeeping; it never sends packets or invokes callbacks."""

    def __init__(self, clock):
        self.clock = clock
        self.generation = uuid.uuid4().hex
        self._lock = threading.RLock()
        self.wanted = set()
        self.persistent = set()
        self.slots = {}
        self._members = {}
        self._days = {}
        self._day_counters = {}
        self._member_versions = {}
        self._certificates = {}
        self._inflight = {}
        self._refused = set()
        self._retry = {}
        self._sequence = 0

    def configure(self, wanted, slots):
        with self._lock:
            new_members = set(slots) - self.slots.keys()
            for member in new_members:
                self._sequence += 1
                self._member_versions[member] = self._sequence
            self.wanted = set(wanted)
            self.persistent = persistent_keys(self.wanted)
            self.slots = dict(slots)
            self._members = {}
            for key in self.wanted | self.persistent:
                self._members.setdefault(key[:2], set()).add(key)
            present = set(self.slots)
            for mapping in (self._days, self._day_counters, self._member_versions):
                for member in set(mapping) - present:
                    del mapping[member]
            for mapping in (self._certificates, self._inflight, self._retry):
                for key in set(mapping) - self.wanted:
                    del mapping[key]
            self._refused.intersection_update(self.wanted | self.persistent)

    def _context(self, member, day=None, lease=None):
        return {
            "native_stream_generation": self.generation,
            "native_member_generation": self._member_versions.get(member, 0),
            "native_day_generation": day,
            "native_lease_id": lease,
        }

    def _invalidate(self, member, *, fresh_anchor=False):
        self._day_counters[member] = self._day_counters.get(member, 0) + 1
        for mapping in (self._certificates, self._inflight):
            for key in self._members.get(member, ()):
                mapping.pop(key, None)
        if fresh_anchor:
            self._days.pop(member, None)
            self._sequence += 1
            self._member_versions[member] = self._sequence

    def invalidate_member(self, member):
        with self._lock:
            if member in self.slots:
                self._invalidate(member, fresh_anchor=True)

    def desired(self):
        """Return bounded actual subscriptions plus their immutable wire context."""
        with self._lock:
            now = self.clock()
            for key, lease in list(self._inflight.items()):
                if lease["started"] is not None and now - lease["started"] >= LEASE_TIMEOUT_SECONDS:
                    del self._inflight[key]
                    attempts = self._retry.get(key, (0, 0))[0] + 1
                    delay = min(
                        LEASE_RETRY_MAX_SECONDS,
                        LEASE_RETRY_BASE_SECONDS * 2 ** min(attempts - 1, 6),
                    )
                    self._retry[key] = attempts, now + delay
            counts = {}
            for key in self._inflight:
                slot = self.slots[key[:2]]
                counts[slot] = counts.get(slot, 0) + 1
            for key in sorted(self.wanted - self.persistent):
                member = key[:2]
                slot = self.slots[member]
                if (
                    member not in self._days
                    or (*member, "1D") in self._refused
                    or key in self._certificates
                    or key in self._inflight
                    or key in self._refused
                    or self._retry.get(key, (0, 0))[1] > now
                    or counts.get(slot, 0) >= LEASE_SLOTS_PER_CONNECTION
                ):
                    continue
                self._sequence += 1
                context = self._context(member, self._day_counters[member], self._sequence)
                self._inflight[key] = {"context": context, "started": None}
                counts[slot] = counts.get(slot, 0) + 1
            contexts = {key: self._context(key[:2]) for key in self.persistent}
            contexts.update({key: lease["context"].copy() for key, lease in self._inflight.items()})
            groups = {}
            for key in contexts:
                groups.setdefault(self.slots[key[:2]], set()).add(key)
            return groups, contexts

    def mark_started(self, registered):
        with self._lock:
            for key in registered:
                lease = self._inflight.get(key)
                if lease is not None and lease["started"] is None:
                    lease["started"] = self.clock()

    def _current_context(self, event):
        member = tuple(event.get("key", ()))[:2]
        return (
            member in self.slots
            and event.get("native_stream_generation") == self.generation
            and event.get("native_member_generation") == self._member_versions.get(member, 0)
        )

    def reject(self, event):
        with self._lock:
            key = tuple(event.get("key", ()))
            if len(key) != 3 or not self._current_context(event):
                return False
            if is_leased_timeframe(key[2]):
                lease = self._inflight.get(key)
                if lease is None or any(event.get(k) != v for k, v in lease["context"].items()):
                    return False
                del self._inflight[key]
                self._certificates.pop(key, None)
            self._refused.add(key)
            if key[2] == "1D":
                self._invalidate(key[:2])
                self._days.pop(key[:2], None)
            return True

    @staticmethod
    def certificate(event):
        return tuple(
            event.get(field)
            for field in ("native_stream_generation", "native_day_generation", "native_lease_id")
        )

    def confirm(self, event):
        answer = {"accepted": False, "invalidated": False}
        with self._lock:
            key = tuple(event.get("key", ()))
            if len(key) != 3 or not self._current_context(event):
                return answer
            if (key not in self.wanted and key not in self.persistent) or key in self._refused:
                return answer
            member = key[:2]
            if key in self.persistent:
                if key[2] == "1D":
                    rows = event.get("rows", ())
                    if len(rows) != 2 or not event.get("metadata"):
                        return answer
                    previous, current = tuple(rows[0]), tuple(rows[1])
                    metadata = tuple(sorted(event["metadata"].items()))
                    old = self._days.get(member)
                    changed = old is not None and (
                        previous != old[0]
                        or current[0] != old[1][0]
                        or current[1] != old[1][1]
                        or current[2] < old[1][2]
                        or current[3] > old[1][3]
                        or metadata != old[2]
                    )
                    if old is None or changed:
                        self._invalidate(member)
                    self._days[member] = previous, current, metadata
                    answer["invalidated"] = changed
                    # A genuine next daily bar closes the exact native bucket
                    # we observed. Its range may widen and its Close may finish
                    # at another price. Corrections/shrunken ranges or a changed
                    # session require a full seed rebuild, not incremental carry.
                    if (
                        changed
                        and current[0] > old[1][0]
                        and previous[0] == old[1][0]
                        and previous[1] == old[1][1]
                        and previous[2] >= old[1][2]
                        and previous[3] <= old[1][3]
                        and metadata == old[2]
                    ):
                        answer["rollover"] = True
                answer["accepted"] = True
                return answer
            lease = self._inflight.get(key)
            certificate = self.certificate(event)
            if lease is None:
                answer["accepted"] = self.witness_valid(key, certificate)
                return answer
            if any(event.get(k) != v for k, v in lease["context"].items()):
                return answer
            if event.get("native_day_generation") != self._day_counters.get(member):
                return answer
            rows = event.get("rows", ())
            day = self._days.get(member)
            if (
                len(rows) != 2
                or not event.get("metadata")
                or day is None
                or rows[-1][0] > day[1][0]
            ):
                return answer
            self._certificates[key] = certificate
            del self._inflight[key]
            self._retry.pop(key, None)
            answer["accepted"] = True
            return answer

    def witness_valid(self, key, certificate):
        if not isinstance(certificate, (tuple, list)) or len(certificate) != 3:
            return False
        with self._lock:
            return (
                key in self._certificates
                and self._certificates[key] == tuple(certificate)
                and certificate[0] == self.generation
                and certificate[1] == self._day_counters.get(key[:2])
            )

    def ready(self, member, needed):
        with self._lock:
            return not any(
                key in self._refused
                or (is_leased_timeframe(key[2]) and key not in self._certificates)
                for key in needed
            ) and (not any(is_leased_timeframe(key[2]) for key in needed) or member in self._days)

    def status(self):
        with self._lock:
            leased = self.wanted - self.persistent
            return {
                "virtual_subscriptions": len(self.wanted),
                "persistent_subscriptions": len(self.persistent),
                "transient_subscriptions": len(self._inflight),
                "witnesses_confirmed": len(self._certificates),
                "witnesses_pending": len(leased - self._certificates.keys() - self._refused),
                "lease_active": len(self._inflight),
                "lease_certified": len(self._certificates),
                "lease_pending": len(leased - self._certificates.keys() - self._refused),
                "lease_refused": len(leased & self._refused),
                "lease_retry_waiting": sum(
                    retry_at > self.clock() for _, retry_at in self._retry.values()
                ),
            }
