"""Leased scanner RSI calculations over the existing native history and quote workers."""

from dataclasses import dataclass

from application.services.custom_indicators.core import Bar, pine_rsi

NATIVE_TIMEFRAMES = {
    "15m": "15",
    "30m": "30",
    "1h": "60",
    "2h": "120",
    "4h": "240",
    **{
        f"{count}{unit}": f"{count}{unit}"
        for unit, maximum in (("D", 6), ("W", 3), ("M", 2))
        for count in range(1, maximum + 1)
    },
}
RSI_LENGTH = 14
HISTORY_BARS = 240
MAX_TRACKER_SYMBOLS = 25
MAX_TRACKER_VIEWS = 4
LEASE_SECONDS = 15
STALE_SECONDS = 30
HISTORY_SPACING = 2
HISTORY_REFRESH = 21600


@dataclass(frozen=True, slots=True)
class WilderRsi:
    """SMA of the first 14 changes, then Wilder's recurrence."""

    last: float
    count: int = 0
    gain: float = 0.0
    loss: float = 0.0

    def add(self, price):
        delta = price - self.last
        up, down = max(delta, 0.0), max(-delta, 0.0)
        if self.count < RSI_LENGTH:
            count = self.count + 1
            return WilderRsi(
                price,
                count,
                (self.gain * self.count + up) / count,
                (self.loss * self.count + down) / count,
            )
        return WilderRsi(
            price,
            self.count,
            self.gain + (up - self.gain) / RSI_LENGTH,
            self.loss + (down - self.loss) / RSI_LENGTH,
        )

    def value(self, price):
        current = self.add(price)
        if current.count == RSI_LENGTH:
            return pine_rsi(current.gain, current.loss)
        return None


@dataclass(frozen=True, slots=True)
class TrackerSeed:
    previous: Bar
    current: Bar
    state: WilderRsi
    epoch: int
    loaded: float

    @classmethod
    def build(cls, bars, epoch, now):
        state = WilderRsi(bars[0].close)
        for bar in bars[1:-1]:
            state = state.add(bar.close)
        return cls(bars[-2], bars[-1], state, epoch, now)

    def matches(self, pair):
        previous, current = pair
        return (
            self.current.time == current.time
            and self.previous.time == previous.time
            and self.previous.close == previous.close
        )

    def advance(self, closed, current):
        if self.current.time != closed.time:
            return None
        return TrackerSeed(closed, current, self.state.add(closed.close), self.epoch, self.loaded)


class RsiTrackerData:
    """Owner lock protects leases, compact seeds and one atomic row per symbol."""

    def __init__(self):
        self.views = {}
        self.seeds = {}
        self.rows = {}
        self.retry = {}
        self.next_history = 0

    def demands(self, now):
        self.views = {key: value for key, value in self.views.items() if value[0] > now}
        demanded = {}
        for _, members, periods in self.views.values():
            for member in members:
                if member not in demanded and len(demanded) == MAX_TRACKER_SYMBOLS:
                    continue
                demanded.setdefault(member, set()).update(periods)
        return demanded

    def request(self, view, members, periods, now):
        self.demands(now)
        if not members:
            self.views.pop(view, None)
        elif view in self.views or len(self.views) < MAX_TRACKER_VIEWS:
            self.views[view] = (now + LEASE_SECONDS, members, periods)
        return self.demands(now)

    def prune(self, wanted):
        self.seeds = {key: seed for key, seed in self.seeds.items() if key in wanted}
        self.retry = {key: retry for key, retry in self.retry.items() if key in wanted}
        members = {key[:2] for key in wanted}
        self.rows = {member: row for member, row in self.rows.items() if member in members}

    def invalidate(self, member=None, key=None):
        if member is None:
            self.seeds.clear()
            self.rows.clear()
            self.retry.clear()
        else:
            self.rows.pop(member, None)
            for series in tuple(self.seeds):
                if series[:2] == member and (key is None or series == key):
                    self.seeds.pop(series)

    def observe(self, member, periods, witness, source, received, price, epoch, now):
        cells = {}
        for tf in periods:
            key = (*member, tf)
            seed, observed = self.seeds.get(key), witness(key)
            if seed is None or seed.epoch != epoch or observed is None:
                continue
            pair, day = observed
            current = pair[-1]
            if (
                not seed.matches(pair)
                or not day.time <= source < (day.end or day.time)
                or source < current.time
                or current.end is not None
                and source >= current.end
                or current.end is None
                and tf[-1] not in "DWM"
            ):
                continue
            value = seed.state.value(price)
            if value is not None:
                cells[tf] = {"value": value, "bar_time": current.time}
        self.rows[member] = {
            "epoch": epoch,
            "source_time": source,
            "received_at": received,
            "price": price,
            "cells": cells,
            "observed_at": now,
        }

    def advance(self, key, closed, current):
        self.rows.pop(key[:2], None)
        seed = self.seeds.get(key)
        if seed is not None:
            advanced = seed.advance(closed, current)
            if advanced is None:
                self.seeds.pop(key)
            else:
                self.seeds[key] = advanced

    def install(self, key, seed):
        previous = self.seeds.get(key)
        if previous and previous.state != seed.state and (row := self.rows.get(key[:2])):
            row["cells"].pop(key[2], None)
        self.seeds[key] = seed
