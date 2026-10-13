# SPDX-License-Identifier: MPL-2.0
# Pine RSI/SMI source: Copyright Rapto_o, Mozilla Public License 2.0.
"""Pure ports of the supplied RSI, SMI and Wilder RMI voting indicators.

The original Pine sources are retained in ``indicators/pine``. Native candle
boundaries select historical state; duration comparisons never create candles.
This module does not fetch data, submit orders, or execute arbitrary Pine.
"""

import re
from bisect import bisect_right
from collections import deque
from dataclasses import dataclass
from typing import Any

from .core import Bar, ema, finite, pine_rsi, rma, rsi_values

_FRAMES = ("1D", "2D", "3D", "4D", "5D", "6D", "1W", "2W", "3W", "1M")


def _input(key, label, kind, default, group, **kw):
    return {"key": key, "label": label, "type": kind, "default": default, "group": group, **kw}


def _inputs(family: str) -> list[dict]:
    group = "00 • GENEL"
    result = [
        _input(
            "requiredBuyVotes",
            "AL için en az kaç zaman dilimi doğrulasın? (N)",
            "int",
            2,
            group,
            min=1,
            max=10,
        ),
        _input(
            "requiredSellVotes",
            "SAT için en az kaç zaman dilimi doğrulasın? (N)",
            "int",
            2,
            group,
            min=1,
            max=10,
        ),
        _input("showTable", "Oy tablosunu göster", "bool", True, group, visual=True),
        _input("onlyFirst", "Sadece N şartının ilk mumunda sinyal", "bool", False, group),
    ]
    for slot, timeframe in enumerate(_FRAMES, 1):
        group = f"{slot:02} • ZAMAN DİLİMİ {slot}"
        result.extend(
            [
                _input(f"en{slot}", "Aktif", "bool", slot in (1, 3), group),
                _input(f"tf{slot}", "TF", "timeframe", timeframe, group),
                _input(
                    f"len{slot}",
                    "SMI pencere (%K)" if family == "smi" else f"{family.upper()} uzunluğu",
                    "int",
                    10 if family == "smi" else 14,
                    group,
                    **({"min": 1, "max": 5000} if family == "smi" else {"min": 2}),
                ),
            ]
        )
        if family == "smi":
            result.extend(
                [
                    _input(f"smoothA{slot}", "EMA 1", "int", 3, group, min=1, max=5000),
                    _input(f"smoothB{slot}", "EMA 2", "int", 3, group, min=1, max=5000),
                ]
            )
        elif family == "rmi":
            result.append(
                _input(f"mom{slot}", "Momentum periyodu", "int", 5, group, min=1, max=5000)
            )
        result.extend(
            [
                _input(
                    f"dipThr{slot}",
                    "AL ≤",
                    "float",
                    -40.0 if family == "smi" else 20.0,
                    group,
                    min=-100 if family == "smi" else 0,
                    max=100,
                    step=0.1,
                ),
                _input(
                    f"topThr{slot}",
                    "SAT ≥",
                    "float",
                    40.0 if family == "smi" else 80.0,
                    group,
                    min=-100 if family == "smi" else 0,
                    max=100,
                    step=0.1,
                ),
            ]
        )
    return result


def _outputs() -> list[dict]:
    return [
        {"key": key, "label": label, "kind": kind}
        for key, label, kind in (
            ("buy_votes", "AL Oy", "number"),
            ("sell_votes", "SAT Oy", "number"),
            ("buy_signal", "AL • DİP", "boolean"),
            ("sell_signal", "SAT • TEPE", "boolean"),
            ("any_signal", "AL veya SAT", "boolean"),
            ("buy_zone", "AL için en az N oy", "boolean"),
            ("sell_zone", "SAT için en az N oy", "boolean"),
            ("active_count", "Aktif TF", "number"),
            ("ready_count", "Hazır TF", "number"),
            ("buy_reachable", "AL hedefi erişilebilir", "boolean"),
            ("sell_reachable", "SAT hedefi erişilebilir", "boolean"),
        )
    ]


SPECS = tuple(
    {
        "id": f"{family}_votes",
        "name": "MTF RSI DİP + TEPE • En Az N Oy" if family == "rsi" else f"{family.upper()} N OY",
        "inputs": _inputs(family),
        "outputs": _outputs(),
        "base_policy": "minimum",
    }
    for family in ("rsi", "smi", "rmi")
)


def _tf_key(timeframe: str, chart_timeframe: str) -> str:
    value = timeframe or chart_timeframe
    return "1" + value if value in ("S", "D", "W", "M") else value


def _seconds(timeframe: str) -> float | None:
    match = re.fullmatch(r"([1-9][0-9]*)([SDWM]?)", timeframe)
    if not match:
        return None
    number, unit = match.groups()
    # Pine's comparison duration is approximate for months. It is NEVER used
    # to infer starts/ends or to aggregate exchange-session bars.
    return int(number) * {"": 60, "S": 1, "D": 86400, "W": 604800, "M": 2628003}[unit]


def _extrema(values: list[float], length: int, high: bool) -> list[float | None]:
    """Pine highest/lowest use available non-NA observations before length bars."""
    queue: deque[tuple[int, float]] = deque()
    result = []
    for index, raw in enumerate(values):
        while queue and queue[0][0] <= index - length:
            queue.popleft()
        value = finite(raw)
        if value is not None:
            while queue and (queue[-1][1] <= value if high else queue[-1][1] >= value):
                queue.pop()
            queue.append((index, value))
        result.append(queue[0][1] if queue else None)
    return result


def _ratio(numerator, denominator) -> float | None:
    return (
        200.0 * numerator / denominator
        if numerator is not None and denominator is not None and denominator > 0
        else None
    )


def _ema_step(previous, sample, length):
    if sample is None:
        return previous
    alpha = 2.0 / (length + 1.0)
    return sample if previous is None else alpha * sample + (1.0 - alpha) * previous


@dataclass
class _Series:
    bars: tuple[Bar, ...]
    values: list
    states: tuple[list, ...]
    times: list[float]
    closed_indices: list[int]
    closed_ends: list[float]
    safe_prefix: list[bool]


def _series(family, bars, length, momentum, smooth_a, smooth_b) -> _Series:
    if family == "smi":
        highs = _extrema([b.high for b in bars], length, True)
        lows = _extrema([b.low for b in bars], length, False)
        distances = [
            b.close - (h + low) / 2 if h is not None and low is not None else None
            for b, h, low in zip(bars, highs, lows)
        ]
        widths = [
            h - low if h is not None and low is not None else None for h, low in zip(highs, lows)
        ]
        num1, den1 = ema(distances, smooth_a), ema(widths, smooth_a)
        num2, den2 = ema(num1, smooth_b), ema(den1, smooth_b)
        states = (
            num1,
            num2,
            den1,
            den2,
            _extrema([b.high for b in bars], max(length - 1, 1), True),
            _extrema([b.low for b in bars], max(length - 1, 1), False),
        )
        values = [_ratio(n, d) for n, d in zip(num2, den2)]
    else:
        differences = [
            b.close - bars[i - momentum].close if i >= momentum else None
            for i, b in enumerate(bars)
        ]
        gains = rma(
            [max(delta, 0.0) if delta is not None else None for delta in differences], length
        )
        losses = rma(
            [max(-delta, 0.0) if delta is not None else None for delta in differences], length
        )
        states = (gains, losses)
        values = (
            rsi_values([b.close for b in bars], length)
            if family == "rsi"
            else [pine_rsi(gain, loss) for gain, loss in zip(gains, losses)]
        )
    closed_indices, closed_ends, safe_prefix = [], [], []
    safe = True
    for index, bar in enumerate(bars):
        safe = (
            safe
            and (bar.end is None or bar.end > bar.time)
            and all(finite(value) is not None for value in (bar.open, bar.high, bar.low, bar.close))
        )
        if index:
            previous = bars[index - 1]
            safe = (
                safe
                and previous.confirmed
                and previous.time < bar.time
                and (previous.end is None or previous.end <= bar.time)
            )
        safe_prefix.append(safe)
        if safe and bar.confirmed and bar.end is not None:
            closed_indices.append(index)
            closed_ends.append(bar.end)
    return _Series(
        bars, values, states, [b.time for b in bars], closed_indices, closed_ends, safe_prefix
    )


@dataclass
class _Range:
    start: float | None = None
    high: float | None = None
    low: float | None = None
    complete: bool = False

    def update(self, bar: Bar, bucket: Bar | None, witnessed_until: float | None) -> None:
        if bucket is None or witnessed_until is None or bar.end is None:
            self.start, self.high, self.low, self.complete = None, None, None, False
            return
        contained = bar.time >= bucket.time and bar.end <= witnessed_until
        if self.start != bucket.time:
            self.start, self.high, self.low = bucket.time, bar.high, bar.low
            self.complete = contained and bar.time == bucket.time
        else:
            self.high, self.low = max(self.high, bar.high), min(self.low, bar.low)
            self.complete = self.complete and contained


def _native_bucket(series: _Series, point: float, as_of: float | None) -> int | None:
    index = bisect_right(series.times, point) - 1
    if index < 0:
        return None
    bar = series.bars[index]
    if bar.end is not None:
        return index if point < bar.end else None
    # A later provider-native bucket witnesses an earlier bucket's historical
    # existence. For the final open bucket, an explicit observation time is
    # required. Neither case claims to know its actual closing timestamp.
    return index if index + 1 < len(series.bars) or as_of is not None and point <= as_of else None


def _snapshot(family, series, bar, cutoff, length, momentum, smooth_a, smooth_b, running, as_of):
    closed_position = bisect_right(series.closed_ends, cutoff) - 1
    anchor_index = series.closed_indices[closed_position] if closed_position >= 0 else None
    bucket_index = _native_bucket(series, bar.time, as_of)
    bucket = series.bars[bucket_index] if bucket_index is not None else None
    witnessed_until = None
    if bucket is not None:
        witnessed_until = bucket.end
        if witnessed_until is None:
            witnessed_until = (
                series.bars[bucket_index + 1].time if bucket_index + 1 < len(series.bars) else as_of
            )
        previous_index = bucket_index - 1
        if (
            previous_index >= 0
            and series.bars[previous_index].confirmed
            and series.safe_prefix[previous_index]
            and (anchor_index is None or previous_index > anchor_index)
        ):
            anchor_index = previous_index
    if family == "smi":
        running.update(bar, bucket, witnessed_until)
    if anchor_index is None:
        return None, "insufficient_history"
    anchor = series.bars[anchor_index]
    if anchor.end == bar.end:
        return series.values[anchor_index], None
    if family == "smi":
        if not running.complete or bucket is None:
            return None, "timeframe_boundary"
        if anchor.time >= bucket.time or anchor.end is not None and anchor.end > bucket.time:
            return None, "insufficient_history"
        num1, num2, den1, den2, tails_high, tails_low = (
            state[anchor_index] for state in series.states
        )
        high = running.high if length == 1 else max(tails_high, running.high)
        low = running.low if length == 1 else min(tails_low, running.low)
        numerator1 = _ema_step(num1, bar.close - (high + low) / 2, smooth_a)
        denominator1 = _ema_step(den1, high - low, smooth_a)
        value = _ratio(
            _ema_step(num2, numerator1, smooth_b), _ema_step(den2, denominator1, smooth_b)
        )
        return value, None
    reference_index = anchor_index + 1 - momentum
    gain, loss = (state[anchor_index] for state in series.states)
    if reference_index < 0 or gain is None or loss is None:
        return None, "insufficient_history"
    change = bar.close - series.bars[reference_index].close
    return pine_rsi(
        (gain * (length - 1) + max(change, 0)) / length,
        (loss * (length - 1) + max(-change, 0)) / length,
    ), None


def evaluate_votes(
    indicator_id: str,
    inputs: dict[str, Any],
    primary: tuple[Bar, ...],
    frames: dict[str, tuple[Bar, ...]],
    chart_timeframe: str = "1D",
    as_of: float | None = None,
) -> list[dict]:
    spec = next((spec for spec in SPECS if spec["id"] == indicator_id), None)
    if spec is None:
        raise ValueError("Bilinmeyen oy göstergesi.")
    settings = {item["key"]: item["default"] for item in spec["inputs"]} | inputs
    family = indicator_id.removesuffix("_votes")
    chart = _tf_key(chart_timeframe, chart_timeframe)
    selected = [_tf_key(settings[f"tf{slot}"], chart) for slot in range(1, 11)]
    enabled = [bool(settings[f"en{slot}"]) for slot in range(1, 11)]
    active = sum(enabled)
    valid = all(
        _seconds(tf) is not None and settings[f"dipThr{slot}"] < settings[f"topThr{slot}"]
        for slot, tf, on in zip(range(1, 11), selected, enabled)
        if on
    )
    minimum = min(
        (tf for tf, on in zip(selected, enabled) if on),
        key=lambda tf: _seconds(tf) or float("inf"),
        default=None,
    )
    valid = valid and active > 0 and chart == minimum
    prepared = []
    cache = {}
    for slot, tf in enumerate(selected, 1):
        length = settings[f"len{slot}"]
        momentum = settings[f"mom{slot}"] if family == "rmi" else 1
        smooth_a = settings[f"smoothA{slot}"] if family == "smi" else 1
        smooth_b = settings[f"smoothB{slot}"] if family == "smi" else 1
        bars = primary if tf == chart else frames.get(tf, ())
        key = (tf, length, momentum, smooth_a, smooth_b)
        if enabled[slot - 1] and key not in cache:
            cache[key] = _series(family, bars, length, momentum, smooth_a, smooth_b)
        prepared.append((cache.get(key), length, momentum, smooth_a, smooth_b, _Range()))
    result = []
    previous_buy = previous_sell = False
    for index, bar in enumerate(primary):
        boundary_ok = bar.end is not None and bar.end > bar.time
        temporal_ok = as_of is None or (
            bar.time <= as_of
            and boundary_ok
            and (bar.end <= as_of if bar.confirmed else as_of < bar.end)
        )
        usable = valid and boundary_ok and temporal_ok
        cutoff = min(bar.end, as_of) if boundary_ok and as_of is not None else bar.end
        rows = []
        buy_votes = sell_votes = ready_count = 0
        for slot, (tf, on, prepared_row) in enumerate(zip(selected, enabled, prepared), 1):
            series, length, momentum, smooth_a, smooth_b, running = prepared_row
            value = None
            reason = (
                "disabled"
                if not on
                else "invalid_chart"
                if not valid
                else "native_boundary_unknown"
                if not boundary_ok
                else "future_bar"
                if not temporal_ok
                else None
            )
            if on and usable:
                if tf == chart:
                    value = series.values[index] if series.safe_prefix[index] else None
                else:
                    value, reason = _snapshot(
                        family,
                        series,
                        bar,
                        cutoff,
                        length,
                        momentum,
                        smooth_a,
                        smooth_b,
                        running,
                        as_of,
                    )
            if on and value is not None:
                ready_count += 1
                buy_votes += value <= settings[f"dipThr{slot}"]
                sell_votes += value >= settings[f"topThr{slot}"]
            if value is None and reason is None:
                reason = "insufficient_history"
            rows.append(
                {
                    "slot": slot,
                    "timeframe": tf,
                    "enabled": on,
                    "value": value,
                    family: value,
                    "ready": value is not None,
                    "reason": reason,
                    "buy_vote": bool(value is not None and value <= settings[f"dipThr{slot}"]),
                    "sell_vote": bool(value is not None and value >= settings[f"topThr{slot}"]),
                    "buy_threshold": settings[f"dipThr{slot}"],
                    "sell_threshold": settings[f"topThr{slot}"],
                }
            )
        buy_reachable = active >= settings["requiredBuyVotes"]
        sell_reachable = active >= settings["requiredSellVotes"]
        buy_zone = usable and buy_reachable and buy_votes >= settings["requiredBuyVotes"]
        sell_zone = usable and sell_reachable and sell_votes >= settings["requiredSellVotes"]
        ready = bool(usable and ready_count)
        buy_signal = bar.confirmed and buy_zone and (not settings["onlyFirst"] or not previous_buy)
        sell_signal = (
            bar.confirmed and sell_zone and (not settings["onlyFirst"] or not previous_sell)
        )
        outputs = {
            "buy_votes": float(buy_votes) if usable else None,
            "sell_votes": float(sell_votes) if usable else None,
            "buy_signal": float(buy_signal) if ready else None,
            "sell_signal": float(sell_signal) if ready else None,
            "any_signal": float(buy_signal or sell_signal) if ready else None,
            "buy_zone": float(buy_zone) if ready else None,
            "sell_zone": float(sell_zone) if ready else None,
            "active_count": float(active),
            "ready_count": float(ready_count),
            "buy_reachable": float(buy_reachable),
            "sell_reachable": float(sell_reachable),
        }
        reason = (
            None
            if ready
            else "invalid_chart"
            if not valid
            else "native_boundary_unknown"
            if not boundary_ok
            else "future_bar"
            if not temporal_ok
            else "insufficient_history"
        )
        result.append({"outputs": outputs, "rows": rows, "ready": ready, "reason": reason})
        if bar.confirmed:
            previous_buy, previous_sell = buy_zone, sell_zone
    return result
