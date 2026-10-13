"""Small, deterministic Pine-compatible numeric primitives; no provider IO."""

from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class Bar:
    time: float
    end: float | None
    open: float
    high: float
    low: float
    close: float
    confirmed: bool


def finite(value) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if isfinite(result) else None


def rma(values: Iterable, length: int, zero_initial: bool = False) -> list[float | None]:
    """Wilder mean seeded by the first length finite observations, ignoring NA.

    zero_initial is only for scripts explicitly mapping their first NA change
    to zero. It is not the default behavior of ta.rma or ta.rsi.
    """
    if length < 1:
        raise ValueError("RMA uzunluğu pozitif olmalıdır.")
    result = []
    seed = []
    previous = None
    for index, raw in enumerate(values):
        value = finite(raw)
        if index == 0 and value is None and zero_initial:
            value = 0.0
        if value is not None:
            if previous is None:
                seed.append(value)
                if len(seed) == length:
                    previous = sum(seed) / length
                    seed.clear()
            else:
                previous += (value - previous) / length
        result.append(previous)
    return result


def ema(values: Iterable, length: int) -> list[float | None]:
    if length < 1:
        raise ValueError("EMA uzunluğu pozitif olmalıdır.")
    result = []
    previous = None
    alpha = 2.0 / (length + 1)
    for raw in values:
        value = finite(raw)
        if value is not None:
            previous = value if previous is None else alpha * value + (1 - alpha) * previous
        result.append(previous)
    return result


def pine_rsi(gain, loss, zero_loss_100: bool = True) -> float | None:
    gain, loss = finite(gain), finite(loss)
    if gain is None or loss is None or gain < 0 or loss < 0:
        return None
    if loss == 0:
        return 100.0 if zero_loss_100 and gain > 0 else None
    return 100.0 - 100.0 / (1.0 + gain / loss)


def rsi_values(closes: Iterable, length: int) -> list[float | None]:
    closes = [finite(value) for value in closes]
    gains, losses = [], []
    for index, close in enumerate(closes):
        previous = closes[index - 1] if index else None
        delta = close - previous if close is not None and previous is not None else None
        gains.append(max(delta, 0.0) if delta is not None else None)
        losses.append(max(-delta, 0.0) if delta is not None else None)
    return [pine_rsi(gain, loss) for gain, loss in zip(rma(gains, length), rma(losses, length))]
