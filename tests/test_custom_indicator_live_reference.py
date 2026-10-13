"""Full-prefix references for the compact live path, independent of its seeds."""

import math
from dataclasses import replace

import pandas as pd
import pytest

from application.services.custom_indicators.core import Bar
from application.services.custom_indicators.live import compile_live


def native_history():
    # Intentionally irregular native starts: the evaluator must not resample.
    bars = []
    stamp = 1_760_000_000.0
    for index in range(91):
        close = 100 + math.sin(index * 0.61) * 8 + index * 0.07
        next_stamp = stamp + (3 if index % 5 else 5) * 86400
        bars.append(Bar(stamp, next_stamp, close - 0.2, close + 2, close - 3, close, True))
        stamp = next_stamp
    return (*bars[:-1], replace(bars[-1], end=None, confirmed=False))


def full_wilder(values, length):
    result = sum(values[:length]) / length
    for sample in values[length:]:
        result = (result * (length - 1) + sample) / length
    return result


def expected_ratio(closes, length, momentum):
    changes = [closes[index] - closes[index - momentum] for index in range(momentum, len(closes))]
    gain = full_wilder([max(change, 0) for change in changes], length)
    loss = full_wilder([max(-change, 0) for change in changes], length)
    return 100 - 100 / (1 + gain / loss)


@pytest.mark.parametrize("family", ["rsi", "rmi", "smi"])
@pytest.mark.parametrize("length", [2, 7, 14])
def test_compact_tick_result_matches_full_native_prefix_recalculation(family, length):
    native = native_history()
    inputs = {f"en{slot}": slot == 1 for slot in range(1, 11)}
    inputs.update(tf1="3D", len1=length, requiredBuyVotes=1, requiredSellVotes=1)
    if family == "rmi":
        inputs["mom1"] = 3
    if family == "smi":
        inputs.update(smoothA1=4, smoothB1=6)
    evaluator = compile_live(f"{family}_votes", inputs, {"3D": native}, "3D")
    high, low = native[-1].high, native[-1].low
    for step, price in enumerate((110, 96, 107, 102, 115, 90, 110, 110), 1):
        high, low = max(high, price), min(low, price)
        result = evaluator.evaluate(
            price=price, as_of=native[-1].time + step, buckets={"3D": native[-1]}
        )
        closes = [bar.close for bar in native[:-1]] + [price]
        if family == "smi":
            highs = (
                pd.Series([bar.high for bar in native[:-1]] + [high])
                .rolling(length, min_periods=1)
                .max()
            )
            lows = (
                pd.Series([bar.low for bar in native[:-1]] + [low])
                .rolling(length, min_periods=1)
                .min()
            )
            deviations = pd.Series(closes) - (highs + lows) / 2
            numerator = (
                deviations.ewm(span=4, adjust=False)
                .mean()
                .ewm(span=6, adjust=False)
                .mean()
                .iloc[-1]
            )
            denominator = (
                (highs - lows)
                .ewm(span=4, adjust=False)
                .mean()
                .ewm(span=6, adjust=False)
                .mean()
                .iloc[-1]
            )
            expected = 200 * numerator / denominator
        else:
            expected = expected_ratio(closes, length, 3 if family == "rmi" else 1)
        assert result["ready"] is True
        assert result["rows"][0]["value"] == pytest.approx(expected, abs=1e-11)
        assert all(row["observed_at"] == native[-1].time + step for row in result["rows"])
