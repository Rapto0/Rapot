"""Standard ta RSI over the existing 500-bar native history, without provider I/O.

Unlike Pine RSI this starts the EWM with zero directional change. Open-bar
replacement is O(1); a witnessed rollover rebuilds the bounded 500-bar window.
"""

from array import array
from dataclasses import dataclass


@dataclass(slots=True)
class StandardRsiSeed:
    closes: array
    bucket: object
    states: dict

    @classmethod
    def build(cls, bars, periods):
        bars = bars[-500:]
        if len(bars) < 2:
            raise ValueError("Standard RSI native history insufficient")
        result = cls(array("d", (bar.close for bar in bars)), bars[-1], {})
        result._prepare(periods)
        return result

    def _prepare(self, periods):
        self.states = {}
        for period in periods:
            gain = loss = 0.0
            alpha = 1.0 / period
            for previous, current in zip(self.closes[:-2], self.closes[1:-1]):
                change = current - previous
                gain = (1 - alpha) * gain + alpha * max(change, 0)
                loss = (1 - alpha) * loss + alpha * max(-change, 0)
            self.states[period] = gain, loss

    def value(self, period, price):
        if period not in self.states or len(self.closes) < period:
            return None
        gain, loss = self.states[period]
        alpha = 1.0 / period
        change = price - self.closes[-2]
        gain = (1 - alpha) * gain + alpha * max(change, 0)
        loss = (1 - alpha) * loss + alpha * max(-change, 0)
        return 100.0 if loss == 0 else 100.0 - 100.0 / (1.0 + gain / loss)

    def advance(self, closed, current):
        if closed.time != self.bucket.time or current.time <= closed.time or not closed.confirmed:
            return False
        self.closes[-1] = closed.close
        self.closes.append(current.close)
        if len(self.closes) > 500:
            self.closes.pop(0)
        self.bucket = current
        self._prepare(tuple(self.states))
        return True
