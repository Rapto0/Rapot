"""Pure ports of the two user-supplied RSI score Pine scripts.

Native provider bucket boundaries, never calendar guesses, select HTF state.
The original sources are retained under ``indicators/pine``.  This module does
not fetch data, resample bars, persist alerts, or execute arbitrary Pine code.
"""

from bisect import bisect_right
from typing import Any

from .core import Bar, pine_rsi, rma, rsi_values

_WEIGHTED_FRAMES = (
    ("1d", "1D", "1 Günlük", 3.0),
    ("2d", "2D", "2 Günlük", 6.0),
    ("3d", "3D", "3 Günlük", 7.0),
    ("4d", "4D", "4 Günlük", 7.0),
    ("5d", "5D", "5 Günlük", 8.0),
    ("6d", "6D", "6 Günlük", 9.0),
    ("1w", "1W", "1 Haftalık", 10.0),
    ("2w", "2W", "2 Haftalık", 14.0),
    ("3w", "3W", "3 Haftalık", 16.0),
    ("1m", "1M", "1 Aylık", 20.0),
)
_SNAPSHOT_FRAMES = ("1D", "2D", "3D", "4D", "5D", "6D", "7D", "2W", "3W", "1M")


def _input(key: str, label: str, kind: str, default: Any, group: str, **kw: Any) -> dict:
    return {"key": key, "label": label, "type": kind, "default": default, "group": group, **kw}


def _weighted_inputs() -> list[dict]:
    group = "⚙️ Genel Ayarlar"
    result = [
        _input("rsiLength", "RSI Periyodu", "int", 14, group, min=2, max=50),
        _input("dipThresh", "Dip Eşiği (Alış)", "float", 30.0, group, min=0, max=100, step=1),
        _input("tepeThresh", "Tepe Eşiği (Satış)", "float", 70.0, group, min=0, max=100, step=1),
        _input("showTable", "Tabloyu Göster", "bool", True, group, visual=True),
    ]
    for key, timeframe, label, weight in _WEIGHTED_FRAMES:
        group = (
            "📅 Günlük Zaman Dilimleri"
            if timeframe.endswith("D")
            else "📆 Haftalık & Aylık Zaman Dilimleri"
        )
        result.extend(
            [
                _input(f"en_{key}", label, "bool", True, group),
                _input(f"w_{key}", "Ağırlık %", "float", weight, group, min=0, max=100, step=0.5),
            ]
        )
    return result


def _snapshot_inputs() -> list[dict]:
    group = "00 • GENEL"
    result = [
        _input("dipTargetScore", "DİP Hedef Skoru", "float", 29.0, group, min=0.01, step=0.25),
        _input("topTargetScore", "TEPE Hedef Skoru", "float", 29.0, group, min=0.01, step=0.25),
        _input("maxStreak", "Maksimum Seri", "int", 0, group, min=0),
    ]
    for slot, timeframe in enumerate(_SNAPSHOT_FRAMES, 1):
        group = f"{slot:02} • ZAMAN DİLİMİ {slot}"
        result.extend(
            [
                _input(f"en{slot}", "Aktif", "bool", True, group),
                _input(f"tf{slot}", "TF", "timeframe", timeframe, group),
                _input(f"len{slot}", "RSI", "int", 14, group, min=2),
                _input(
                    f"dipThr{slot}", "DİP <", "float", 30.0, group, min=0.0, max=100.0, step=0.1
                ),
                _input(
                    f"topThr{slot}", "TEPE >", "float", 70.0, group, min=0.0, max=100.0, step=0.1
                ),
                _input(f"tfPts{slot}", "TF Puanı", "float", 1.0, group, min=0.0, step=0.25),
                _input(f"serialPts{slot}", "Seri Puanı", "float", 1.0, group, min=0.0, step=0.25),
            ]
        )
    return result


def _output(key: str, label: str, kind: str = "number") -> dict:
    return {"key": key, "label": label, "kind": kind}


_SIGNALS = [
    _output("buy_signal", "DİP sinyali", "boolean"),
    _output("sell_signal", "TEPE sinyali", "boolean"),
    _output("any_signal", "DİP veya TEPE sinyali", "boolean"),
]
_COUNTS = [
    _output("active_count", "Etkin zaman dilimi sayısı"),
    _output("ready_count", "RSI değeri hazır zaman dilimi sayısı"),
]
SPECS = (
    {
        "id": "htf_rsi_score",
        "name": "HTF RSI Score",
        "inputs": _weighted_inputs(),
        "outputs": [
            _output("score", "HTF RSI Skoru"),
            *_SIGNALS,
            _output("buy_zone", "DİP bölgesi", "boolean"),
            _output("sell_zone", "TEPE bölgesi", "boolean"),
            *_COUNTS,
        ],
        "base_policy": "any",
    },
    {
        "id": "rsi_snapshot",
        "name": "MTF RSI DİP + TEPE Snapshot [PRO]",
        "inputs": _snapshot_inputs(),
        "outputs": [
            _output("dip_score", "DIP Skoru"),
            _output("top_score", "TEPE Skoru"),
            *_SIGNALS,
            *_COUNTS,
        ],
        "base_policy": "daily",
    },
)


def _averages(bars: tuple[Bar, ...], length: int, *, initial_zero: bool) -> tuple[list, list]:
    gains: list[float | None] = [0.0 if initial_zero else None] if bars else []
    losses: list[float | None] = gains.copy()
    for previous, current in zip(bars, bars[1:]):
        change = current.close - previous.close
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    return list(rma(gains, length)), list(rma(losses, length))


def _bucket(
    bars: tuple[Bar, ...], times: list[float], point: float, as_of: float | None = None
) -> int | None:
    index = bisect_right(times, point) - 1
    if index < 0:
        return None
    if bars[index].end is None:
        # Following native starts witness historical bucket membership; the
        # latest open bucket needs an explicit observation time. This is not a
        # synthetic close timestamp, and its future OHLC is never consumed.
        if index + 1 >= len(bars) and (as_of is None or point > as_of):
            return None
    elif not point < bars[index].end:
        return None
    return index


def _safe_prefixes(bars: tuple[Bar, ...]) -> list[bool]:
    """A seed can use historical closes with a following native-bucket witness."""
    result = []
    safe = True
    for position, bar in enumerate(bars):
        safe = safe and bar.confirmed and (bar.end is None or bar.end > bar.time)
        if position:
            previous = bars[position - 1]
            safe = (
                safe
                and previous.time < bar.time
                and (previous.end is None or previous.end <= bar.time)
            )
        result.append(safe)
    return result


def _contains_primary(bars: tuple[Bar, ...], index: int, primary: Bar, as_of) -> bool:
    if primary.end is None:
        return False
    bar = bars[index]
    upper = (
        bar.end if bar.end is not None else bars[index + 1].time if index + 1 < len(bars) else as_of
    )
    # The final open HTF can be observed before a daily primary closes. A
    # developing snapshot only needs its current close at the supplied as_of.
    observation = (
        primary.end
        if primary.confirmed
        else min(primary.end, as_of)
        if as_of is not None
        else primary.end
    )
    return upper is not None and observation <= upper


def _developing(
    current_close: float,
    bars: tuple[Bar, ...],
    gains: list,
    losses: list,
    index: int,
    length: int,
    safe_prefixes: list[bool],
    *,
    standard_rsi: bool,
) -> float | None:
    previous = index - 1
    if previous < 0:
        return None
    bar = bars[previous]
    if (
        not bar.confirmed
        or not safe_prefixes[previous]
        or bar.time >= bars[index].time
        or bar.end is not None
        and bar.end > bars[index].time
        or gains[previous] is None
        or losses[previous] is None
    ):
        return None
    change = current_close - bar.close
    gain = (gains[previous] * (length - 1) + max(change, 0.0)) / length
    loss = (losses[previous] * (length - 1) + max(-change, 0.0)) / length
    return pine_rsi(gain, loss, zero_loss_100=standard_rsi)


def _known_at(bar: Bar, as_of: float | None) -> bool:
    if as_of is None:
        return True
    if bar.time > as_of or bar.end is None:
        return False
    return bar.end <= as_of if bar.confirmed else as_of < bar.end


def _unavailable(spec: dict) -> dict:
    return {
        "outputs": {output["key"]: None for output in spec["outputs"]},
        "rows": [],
        "ready": False,
        "reason": "Ana mum gözlem anında henüz bilinmiyor veya kapanış durumu tutarsız.",
    }


def _weighted(
    inputs: dict, primary: tuple[Bar, ...], frames: dict, as_of: float | None
) -> list[dict]:
    length = inputs["rsiLength"]
    prepared = {}
    for _, timeframe, _, _ in _WEIGHTED_FRAMES:
        bars = frames.get(timeframe, ())
        gains, losses = _averages(bars, length, initial_zero=False)
        closed_indices = [i for i, bar in enumerate(bars) if bar.confirmed and bar.end is not None]
        prepared[timeframe] = (
            bars,
            [b.time for b in bars],
            rsi_values([b.close for b in bars], length),
            gains,
            losses,
            closed_indices,
            [bars[i].end for i in closed_indices],
            _safe_prefixes(bars),
        )
    results = []
    previous_dip = previous_top = False
    for primary_index, bar in enumerate(primary):
        if not _known_at(bar, as_of):
            results.append(_unavailable(SPECS[0]))
            previous_dip = previous_top = False
            continue
        rows = []
        weight_sum = weighted_sum = 0.0
        active_count = ready_count = 0
        for key, timeframe, _, _ in _WEIGHTED_FRAMES:
            bars, times, values, gains, losses, closed_indices, closed_ends, safe_prefixes = (
                prepared[timeframe]
            )
            enabled, weight = inputs[f"en_{key}"], inputs[f"w_{key}"]
            value = None
            if bar.confirmed and bar.end is not None:
                # Historical lookahead_off publishes the HTF value only when
                # that native HTF candle has actually closed.
                closed_position = bisect_right(closed_ends, bar.end) - 1
                if closed_position >= 0:
                    value_index = closed_indices[closed_position]
                    value = values[value_index] if safe_prefixes[value_index] else None
            elif not bar.confirmed and primary_index == len(primary) - 1:
                index = _bucket(bars, times, bar.time if as_of is None else as_of, as_of)
                # With a real observation time, this also identifies the
                # current native LTF candle inside an open primary candle.
                # Without it the primary opening timestamp only locates HTF.
                if (
                    index is not None
                    and bar.end is not None
                    and (as_of is not None or _contains_primary(bars, index, bar, as_of))
                ):
                    value = _developing(
                        bar.close,
                        bars,
                        gains,
                        losses,
                        index,
                        length,
                        safe_prefixes,
                        standard_rsi=True,
                    )
            if enabled:
                active_count += 1
                if value is not None:
                    ready_count += 1
                    weight_sum += weight
                    weighted_sum += value * weight
            rows.append(
                {
                    "slot": key,
                    "timeframe": timeframe,
                    "enabled": enabled,
                    "rsi": value,
                    "weight": weight,
                    "ready": value is not None,
                }
            )
        score = weighted_sum / weight_sum if weight_sum > 0 else None
        dip = score is not None and score <= inputs["dipThresh"]
        top = score is not None and score >= inputs["tepeThresh"]
        buy_signal, sell_signal = dip and not previous_dip, top and not previous_top
        outputs = {
            "score": score,
            "buy_zone": float(dip),
            "sell_zone": float(top),
            "buy_signal": float(buy_signal),
            "sell_signal": float(sell_signal),
            "any_signal": float(buy_signal or sell_signal),
            "active_count": float(active_count),
            "ready_count": float(ready_count),
        }
        results.append(
            {
                "outputs": outputs,
                "rows": rows,
                "ready": score is not None,
                "reason": None
                if score is not None
                else "RSI geçmişi veya pozitif etkin ağırlık yok.",
            }
        )
        previous_dip, previous_top = dip, top
    return results


def _streaks(values: list, threshold: float, *, below: bool) -> list[int]:
    result = []
    streak = 0
    for value in values:
        meets = value is not None and (value < threshold if below else value > threshold)
        streak = streak + 1 if meets else 0
        result.append(streak)
    return result


def _points(streak: int, base: float, serial: float, cap: int) -> float:
    if streak <= 0:
        return 0.0
    effective = min(streak, cap) if cap > 0 else streak
    return base + (effective - 1) * serial


def _snapshot(
    inputs: dict, primary: tuple[Bar, ...], frames: dict, as_of: float | None
) -> list[dict]:
    prepared = {}
    shared = {}
    for slot in range(1, 11):
        timeframe, length = inputs[f"tf{slot}"], inputs[f"len{slot}"]
        key = (timeframe, length, inputs[f"dipThr{slot}"], inputs[f"topThr{slot}"])
        if key not in shared:
            bars = frames.get(timeframe, ())
            gains, losses = _averages(bars, length, initial_zero=True)
            values = rsi_values([b.close for b in bars], length)
            shared[key] = (
                bars,
                [b.time for b in bars],
                gains,
                losses,
                _streaks(values, inputs[f"dipThr{slot}"], below=True),
                _streaks(values, inputs[f"topThr{slot}"], below=False),
                _safe_prefixes(bars),
            )
        prepared[slot] = shared[key]
    result = []
    for bar in primary:
        if not _known_at(bar, as_of):
            result.append(_unavailable(SPECS[1]))
            continue
        rows = []
        total_dip = total_top = 0.0
        active_count = ready_count = 0
        for slot in range(1, 11):
            bars, times, gains, losses, dip_streaks, top_streaks, safe_prefixes = prepared[slot]
            enabled, length = inputs[f"en{slot}"], inputs[f"len{slot}"]
            index = _bucket(bars, times, bar.time, as_of)
            value = None
            dip_streak = top_streak = 0
            if index is not None and _contains_primary(bars, index, bar, as_of):
                value = _developing(
                    bar.close, bars, gains, losses, index, length, safe_prefixes, standard_rsi=False
                )
                if value is not None and value < inputs[f"dipThr{slot}"]:
                    dip_streak = dip_streaks[index - 1] + 1
                if value is not None and value > inputs[f"topThr{slot}"]:
                    top_streak = top_streaks[index - 1] + 1
            base, serial, cap = (
                inputs[f"tfPts{slot}"],
                inputs[f"serialPts{slot}"],
                inputs["maxStreak"],
            )
            dip_score = _points(dip_streak, base, serial, cap) if enabled else 0.0
            top_score = _points(top_streak, base, serial, cap) if enabled else 0.0
            total_dip += dip_score
            total_top += top_score
            active_count += int(enabled)
            ready_count += int(enabled and value is not None)
            rows.append(
                {
                    "slot": slot,
                    "timeframe": inputs[f"tf{slot}"],
                    "enabled": enabled,
                    "rsi": value,
                    "dip_streak": dip_streak,
                    "top_streak": top_streak,
                    "dip_score": dip_score,
                    "top_score": top_score,
                    "ready": value is not None,
                }
            )
        buy_signal = bar.confirmed and total_dip >= inputs["dipTargetScore"]
        sell_signal = bar.confirmed and total_top >= inputs["topTargetScore"]
        ready = ready_count > 0
        result.append(
            {
                "outputs": {
                    "dip_score": total_dip,
                    "top_score": total_top,
                    "buy_signal": float(buy_signal),
                    "sell_signal": float(sell_signal),
                    "any_signal": float(buy_signal or sell_signal),
                    "active_count": float(active_count),
                    "ready_count": float(ready_count),
                },
                "rows": rows,
                "ready": ready,
                "reason": None
                if ready
                else "Önceki kapanmış yerel TF durumu veya RSI geçmişi yok.",
            }
        )
    return result


def evaluate_score(
    indicator_id: str,
    inputs: dict,
    primary: tuple[Bar, ...],
    frames: dict[str, tuple[Bar, ...]],
    *,
    chart_timeframe: str = "1D",
    as_of: float | None = None,
) -> list[dict]:
    """Evaluate native bars with original Pine inputs and no external effects.

    ``frames`` must contain ascending native bars with their true end times;
    unconfirmed realtime bars are not consumed as historical closing values.
    Input validation belongs to the shared catalogue boundary.
    """
    spec = next((spec for spec in SPECS if spec["id"] == indicator_id), None)
    if spec is None:
        raise ValueError(f"Bilinmeyen RSI skor göstergesi: {indicator_id}")
    settings = {field["key"]: field["default"] for field in spec["inputs"]}
    settings.update(inputs)
    if indicator_id == "rsi_snapshot":
        if chart_timeframe != "1D":
            raise ValueError("MTF RSI Snapshot yalnız 1D grafik için tasarlanmıştır.")
        return _snapshot(settings, primary, frames, as_of)
    return _weighted(settings, primary, frames, as_of)
