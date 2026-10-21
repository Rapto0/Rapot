"""Streaming bootstrap agrees with retained replay and an independent formula."""

import math
from dataclasses import replace

import pandas as pd
import pytest

from application.services.custom_indicators.core import Bar
from application.services.custom_indicators.live import _compile_seed, compile_live
from application.services.custom_indicators.votes import _series


def native_history(count, shape="wave"):
    bars = []
    for index in range(count):
        close = 100.0 if shape == "flat" else 100 + math.sin(index * 0.61) * 8 + index * 0.007
        # Repeated extrema exercise both window expiry and equal-value removal.
        high, low = (close, close) if shape == "flat" else (110 + index // 7, 90 - index // 11)
        bars.append(Bar(index * 86400.0, (index + 1) * 86400.0, close, high, low, close, True))
    return tuple(bars)


@pytest.mark.parametrize("shape", ["wave", "flat"])
@pytest.mark.parametrize(
    "count,length,smooth_a,smooth_b",
    [
        (1, 1, 1, 1),
        (2, 2, 3, 4),
        (9, 10, 3, 3),
        (10, 10, 3, 3),
        (519, 10, 3, 3),
        (519, 47, 7, 4),
        (519, 5000, 5000, 5000),
        (5001, 5000, 7, 9),
    ],
)
def test_smi_bootstrap_states_match_retained_replay_exactly(
    shape, count, length, smooth_a, smooth_b
):
    bars = native_history(count + 1, shape)
    seed = _compile_seed("smi", bars, length, smooth_a=smooth_a, smooth_b=smooth_b)
    replay = _series("smi", bars[:-1], length, 1, smooth_a, smooth_b)
    assert (seed.num1, seed.num2, seed.den1, seed.den2, seed.tail_high, seed.tail_low) == tuple(
        values[-1] for values in replay.states
    )
    assert seed.window_extremes == (
        tuple((bar.high, bar.low) for bar in bars[:-1][-(length - 1) :]) if length > 1 else ()
    )


@pytest.mark.parametrize(
    "length,smooth_a,smooth_b", [(1, 1, 1), (2, 3, 4), (47, 7, 4), (5000, 5000, 5000)]
)
def test_smi_bootstrap_then_ticks_and_rollovers_match_independent_full_prefix(
    length, smooth_a, smooth_b
):
    bars = native_history(541)
    settings = {f"en{slot}": slot == 1 for slot in range(1, 11)}
    settings.update(len1=length, smoothA1=smooth_a, smoothB1=smooth_b)
    evaluator = compile_live(
        "smi_votes", settings, {"1D": (*bars[:519], replace(bars[519], confirmed=False))}
    )
    for index in range(519, 540):
        current = bars[index]
        high, low = current.high, current.low
        for step, offset in enumerate((0.0, 1.0, -2.0)):
            price = current.close + offset
            high, low = max(high, price), min(low, price)
            point = evaluator.evaluate(price=price, as_of=current.time + step + 1)
            closes = pd.Series([bar.close for bar in bars[:index]] + [price])
            highs = (
                pd.Series([bar.high for bar in bars[:index]] + [high])
                .rolling(length, min_periods=1)
                .max()
            )
            lows = (
                pd.Series([bar.low for bar in bars[:index]] + [low])
                .rolling(length, min_periods=1)
                .min()
            )
            numerator = (
                (closes - (highs + lows) / 2)
                .ewm(span=smooth_a, adjust=False)
                .mean()
                .ewm(span=smooth_b, adjust=False)
                .mean()
                .iloc[-1]
            )
            denominator = (
                (highs - lows)
                .ewm(span=smooth_a, adjust=False)
                .mean()
                .ewm(span=smooth_b, adjust=False)
                .mean()
                .iloc[-1]
            )
            assert point["ready"]
            assert point["rows"][0]["value"] == pytest.approx(
                200 * numerator / denominator, abs=1e-11
            )
        assert evaluator.advance_native("1D", current, replace(bars[index + 1], confirmed=False))


def test_smi_seed_preserves_nonfinite_intermediate_ema_semantics():
    bars = tuple(
        Bar(float(i), float(i + 1), 1e308, 1.7e308, -1.7e308, 1e308, True) for i in range(5)
    )
    seed = _compile_seed("smi", bars, 3, smooth_a=3, smooth_b=4)
    replay = _series("smi", bars[:-1], 3, 1, 3, 4)
    assert (seed.num1, seed.num2, seed.den1, seed.den2) == tuple(
        row[-1] for row in replay.states[:4]
    )


def test_smi_seed_preserves_replay_float_coercion_before_extrema_arithmetic():
    center = 2**54
    bars = tuple(
        Bar(float(i), float(i + 1), center, center + 3 + i, center - 5 - i, center + 1, True)
        for i in range(5)
    )
    seed = _compile_seed("smi", bars, 3, smooth_a=3, smooth_b=4)
    replay = _series("smi", bars[:-1], 3, 1, 3, 4)
    assert (seed.num1, seed.num2, seed.den1, seed.den2, seed.tail_high, seed.tail_low) == tuple(
        row[-1] for row in replay.states
    )


@pytest.mark.parametrize(
    "invalid", ["revised_order", "unconfirmed_predecessor", "invalid_ohlc", "nonfinite"]
)
def test_smi_streaming_seed_keeps_native_history_validation(invalid):
    bars = list(native_history(20))
    if invalid == "revised_order":
        bars[5] = replace(bars[5], time=bars[4].time)
    elif invalid == "unconfirmed_predecessor":
        bars[5] = replace(bars[5], confirmed=False)
    elif invalid == "invalid_ohlc":
        bars[5] = replace(bars[5], high=bars[5].low - 1)
    else:
        bars[5] = replace(bars[5], close=float("nan"))
    seed = _compile_seed("smi", tuple(bars), 10, smooth_a=3, smooth_b=3)
    assert seed.reason == "insufficient_native_history"
