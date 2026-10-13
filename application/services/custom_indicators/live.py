"""Compiled, event-driven versions of the five retained Pine indicators.

The live policy deliberately removes the original scripts' bar-close signal
gate. Closed native history seeds the recursions once; an open native candle is
replaced on every observation, never appended once per quote. The provider owns
all candle identities (including multi-day/week boundaries).
"""

from dataclasses import dataclass, replace

from .core import Bar, finite, pine_rsi, rsi_values
from .score import _WEIGHTED_FRAMES, _averages, _points, _streaks
from .votes import _ema_step, _ratio, _series


@dataclass(frozen=True, slots=True)
class _Seed:
    bucket: Bar | None
    family: str
    length: int
    reference: float | None = None
    gain: float | None = None
    loss: float | None = None
    num1: float | None = None
    num2: float | None = None
    den1: float | None = None
    den2: float | None = None
    tail_high: float | None = None
    tail_low: float | None = None
    smooth_a: int = 1
    smooth_b: int = 1
    momentum_closes: tuple[float, ...] = ()
    window_extremes: tuple[tuple[float, float], ...] = ()
    streak_gain: float | None = None
    streak_loss: float | None = None
    reason: str | None = None


def _valid_bars(bars: tuple[Bar, ...]) -> bool:
    for index, bar in enumerate(bars):
        if (
            not all(
                finite(value) is not None
                for value in (bar.time, bar.open, bar.high, bar.low, bar.close)
            )
            or bar.end is not None
            and (finite(bar.end) is None or bar.end <= bar.time)
            or bar.low > min(bar.open, bar.close)
            or bar.high < max(bar.open, bar.close)
        ):
            return False
        if index:
            previous = bars[index - 1]
            if (
                not previous.confirmed
                or previous.time >= bar.time
                or previous.end is not None
                and previous.end > bar.time
            ):
                return False
    return bool(bars)


def _compile_seed(family, bars, length, momentum=1, smooth_a=1, smooth_b=1):
    bucket = bars[-1] if bars else None
    invalid = _Seed(bucket, family, length, reason="insufficient_native_history")
    if not _valid_bars(bars):
        return invalid
    # A closed-market bootstrap retains the final confirmed candle as a
    # pending commit. It cannot evaluate live, but the next provider-native
    # pair can advance this state without fetching all history again.
    closed = bars[:-1]
    if not closed:
        return invalid
    if family == "snapshot":
        gains, losses = _averages(closed, length, initial_zero=True)
        standard_gains, standard_losses = _averages(closed, length, initial_zero=False)
        gain, loss = _live_averages(closed, length, 1, gains[-1], losses[-1], initial_zero=True)
        streak_gain, streak_loss = _live_averages(
            closed, length, 1, standard_gains[-1], standard_losses[-1]
        )
        return _Seed(
            bucket,
            family,
            length,
            reference=closed[-1].close,
            gain=gain,
            loss=loss,
            streak_gain=streak_gain,
            streak_loss=streak_loss,
            reason=None if gain is not None and loss is not None else "insufficient_native_history",
        )
    prepared = _series(family, closed, length, momentum, smooth_a, smooth_b)
    if family == "smi":
        num1, num2, den1, den2, high, low = (state[-1] for state in prepared.states)
        return _Seed(
            bucket,
            family,
            length,
            num1=num1,
            num2=num2,
            den1=den1,
            den2=den2,
            tail_high=high,
            tail_low=low,
            smooth_a=smooth_a,
            smooth_b=smooth_b,
            window_extremes=tuple((bar.high, bar.low) for bar in closed[-(length - 1) :])
            if length > 1
            else (),
        )
    reference_index = len(closed) - momentum
    gain, loss = (state[-1] for state in prepared.states)
    gain, loss = _live_averages(closed, length, momentum, gain, loss)
    return _Seed(
        bucket,
        family,
        length,
        reference=closed[reference_index].close if reference_index >= 0 else None,
        gain=gain,
        loss=loss,
        momentum_closes=tuple(bar.close for bar in closed[-momentum:]) if family == "rmi" else (),
        reason=None
        if reference_index >= 0 and gain is not None and loss is not None
        else "insufficient_native_history",
    )


def _live_averages(bars, length, momentum, gain, loss, *, initial_zero=False):
    """Permit the current native candle to complete the first Wilder seed.

    Exactly length-1 closed samples can be represented by their partial
    means: the ordinary one-step recurrence then produces the first SMA.
    Repeated quotes replace the final sample, and rollover commits it once.
    No extra retained tail or partial-state flag is necessary.
    """
    if gain is not None and loss is not None:
        return gain, loss
    if len(bars) - momentum + int(initial_zero) != length - 1:
        return gain, loss
    gains = losses = 0.0
    for index in range(momentum, len(bars)):
        change = bars[index].close - bars[index - momentum].close
        gains += max(change, 0.0)
        losses += max(-change, 0.0)
    return gains / (length - 1), losses / (length - 1)


def _advance_seed(seed, closed, current):
    if seed.family == "smi":
        high = closed.high if seed.length == 1 else max(closed.high, seed.tail_high)
        low = closed.low if seed.length == 1 else min(closed.low, seed.tail_low)
        num1 = _ema_step(seed.num1, closed.close - (high + low) / 2, seed.smooth_a)
        den1 = _ema_step(seed.den1, high - low, seed.smooth_a)
        extremes = (
            (*seed.window_extremes, (closed.high, closed.low))[-(seed.length - 1) :]
            if seed.length > 1
            else ()
        )
        return replace(
            seed,
            bucket=current,
            num1=num1,
            den1=den1,
            num2=_ema_step(seed.num2, num1, seed.smooth_b),
            den2=_ema_step(seed.den2, den1, seed.smooth_b),
            tail_high=max((row[0] for row in extremes), default=None),
            tail_low=min((row[1] for row in extremes), default=None),
            window_extremes=extremes,
        ), None
    change = closed.close - seed.reference
    gain = (seed.gain * (seed.length - 1) + max(change, 0.0)) / seed.length
    loss = (seed.loss * (seed.length - 1) + max(-change, 0.0)) / seed.length
    reference = closed.close
    closes = seed.momentum_closes
    if seed.family == "rmi":
        closes = (*closes[1:], closed.close)
        reference = closes[0]
    streak_gain, streak_loss = seed.streak_gain, seed.streak_loss
    if seed.family == "snapshot":
        streak_gain = (streak_gain * (seed.length - 1) + max(change, 0.0)) / seed.length
        streak_loss = (streak_loss * (seed.length - 1) + max(-change, 0.0)) / seed.length
    return replace(
        seed,
        bucket=current,
        reference=reference,
        gain=gain,
        loss=loss,
        momentum_closes=closes,
        streak_gain=streak_gain,
        streak_loss=streak_loss,
    ), pine_rsi(streak_gain, streak_loss)


@dataclass(frozen=True, slots=True)
class _Row:
    slot: str | int
    timeframe: str
    enabled: bool
    seed: _Seed | None
    weight: float = 0.0
    dip_streak: int = 0
    top_streak: int = 0


class LiveEvaluator:
    """A bounded per-configuration state machine; one caller serializes updates.

    ``buckets`` is the provider's current native candle map. Unknown closing
    timestamps are accepted only with that explicit current-candle witness.
    Feed age, disconnects and gaps must be rejected by the caller before this
    method; call ``reset()`` when continuity is lost. A changed native identity
    requires compilation from its newly confirmed history, not a guessed bar.
    """

    def __init__(self, indicator_id, inputs, rows, outputs):
        self.indicator_id = indicator_id
        self.inputs = inputs
        self.rows = tuple(rows)
        self.output_keys = tuple(output["key"] for output in outputs)
        self.required_timeframes = tuple(dict.fromkeys(row.timeframe for row in rows if row.seed))
        self._ranges = {}
        self._previous_zones = None
        self._last_as_of = None
        self._last_key = None
        self._last_result = None

    def reset(self):
        """Discard edge continuity and accumulated tick extremes after a gap."""
        self._ranges.clear()
        self._previous_zones = None
        self._last_as_of = self._last_key = self._last_result = None

    def pause_signal_baseline(self):
        """Break signal edges while keeping observed extrema and source ordering."""
        self._previous_zones = None
        self._last_key = self._last_result = None

    def current_range(self, timeframe):
        """Read the native/tick extrema already observed, without changing state."""
        if timeframe in self._ranges:
            return self._ranges[timeframe]
        for row in self.rows:
            if row.timeframe == timeframe and row.seed and row.seed.bucket:
                return row.seed.bucket.high, row.seed.bucket.low
        return None

    @property
    def retained_cells(self):
        """Conservative scalar-slot budget, not a byte/RSS memory measurement.

        Per-seed fixed allowance covers its compact state/current candle;
        potentially long RMI/SMI tails are counted explicitly. Duplicate rows
        sharing one seed do not multiply retained tail storage.
        """
        seeds = {id(row.seed): row.seed for row in self.rows if row.seed is not None}
        return (
            len(self.inputs)
            + 8 * len(self.rows)
            + sum(
                32 + len(seed.momentum_closes) + 2 * len(seed.window_extremes)
                for seed in seeds.values()
            )
        )

    def advance_native(self, timeframe, closed_bar, new_current_bar):
        """Commit one provider-witnessed native rollover without history IO.

        The caller supplies consecutive bars from the same continuous native
        series. A later start is the witness when native close time is unknown;
        no calendar duration is inferred. Corrections, gaps/reconnects or
        missing seeds require the caller's normal history bootstrap instead.
        Failure does not mutate any seed, range or signal baseline.
        """
        selected = [row for row in self.rows if row.timeframe == timeframe and row.seed]
        if (
            not selected
            or not closed_bar.confirmed
            or new_current_bar.confirmed
            or not _valid_bars((closed_bar, new_current_bar))
            or self._last_as_of is not None
            and self._last_as_of >= new_current_bar.time
        ):
            return False
        prior_range = self.current_range(timeframe)
        if prior_range and (closed_bar.high < prior_range[0] or closed_bar.low > prior_range[1]):
            return False
        replacements = {}
        for row in selected:
            seed = row.seed
            if id(seed) in replacements:
                continue
            if (
                seed.reason
                or seed.family == "snapshot"
                and (seed.streak_gain is None or seed.streak_loss is None)
                or seed.bucket is None
                or seed.bucket.time != closed_bar.time
                or seed.bucket.open != closed_bar.open
                or seed.bucket.end is not None
                and seed.bucket.end != closed_bar.end
                or closed_bar.high < seed.bucket.high
                or closed_bar.low > seed.bucket.low
            ):
                return False
            replacements[id(seed)] = _advance_seed(seed, closed_bar, new_current_bar)
        updated = []
        for row in self.rows:
            if row.timeframe != timeframe or row.seed is None:
                updated.append(row)
                continue
            new_seed, closed_rsi = replacements[id(row.seed)]
            if self.indicator_id == "rsi_snapshot":
                slot = row.slot
                dip = (
                    row.dip_streak + 1
                    if closed_rsi is not None and closed_rsi < self.inputs[f"dipThr{slot}"]
                    else 0
                )
                top = (
                    row.top_streak + 1
                    if closed_rsi is not None and closed_rsi > self.inputs[f"topThr{slot}"]
                    else 0
                )
                updated.append(replace(row, seed=new_seed, dip_streak=dip, top_streak=top))
            else:
                updated.append(replace(row, seed=new_seed))
        self.rows = tuple(updated)
        self._ranges.pop(timeframe, None)
        self._last_key = self._last_result = None
        return True

    def _unknown(self, reason, rows=()):
        self._previous_zones = None
        self._last_key = self._last_result = None
        return {
            "outputs": dict.fromkeys(self.output_keys),
            "rows": list(rows),
            "ready": False,
            "reason": reason,
        }

    def _value(self, row, price, as_of, buckets):
        seed = row.seed
        if seed is None:
            return None, "zero_weight" if row.enabled else "disabled"
        if seed.reason:
            return None, seed.reason
        current = seed.bucket if buckets is None else buckets.get(row.timeframe)
        if current is None:
            return None, "current_native_bucket_missing"
        if current.time != seed.bucket.time:
            return None, "native_seed_recompile_required"
        if current.confirmed:
            return None, "current_native_bucket_missing"
        if current.end is None and buckets is None:
            return None, "native_boundary_unknown"
        if as_of < current.time or current.end is not None and as_of >= current.end:
            return None, "outside_current_native_bucket"
        if not _valid_bars((current,)):
            return None, "invalid_current_native_bucket"
        if seed.family != "smi":
            change = price - seed.reference
            gain = (seed.gain * (seed.length - 1) + max(change, 0.0)) / seed.length
            loss = (seed.loss * (seed.length - 1) + max(-change, 0.0)) / seed.length
            value = pine_rsi(gain, loss, zero_loss_100=seed.family != "snapshot")
            return value, None if value is not None else "undefined_oscillator"
        previous_high, previous_low = self._ranges.get(row.timeframe, (current.high, current.low))
        high, low = max(current.high, previous_high, price), min(current.low, previous_low, price)
        self._ranges[row.timeframe] = high, low
        window_high = high if seed.length == 1 else max(high, seed.tail_high)
        window_low = low if seed.length == 1 else min(low, seed.tail_low)
        num1 = _ema_step(seed.num1, price - (window_high + window_low) / 2, seed.smooth_a)
        den1 = _ema_step(seed.den1, window_high - window_low, seed.smooth_a)
        value = _ratio(
            _ema_step(seed.num2, num1, seed.smooth_b),
            _ema_step(seed.den2, den1, seed.smooth_b),
        )
        return value, None if value is not None else "undefined_oscillator"

    def evaluate(self, *, price, as_of, buckets=None):
        price, as_of = finite(price), finite(as_of)
        if price is None or price <= 0 or as_of is None:
            self.reset()
            return self._unknown("invalid_live_observation")
        if self._last_as_of is not None and as_of < self._last_as_of:
            self.reset()
            return self._unknown("out_of_order_observation")
        bucket_key = (
            None
            if buckets is None
            else tuple((tf, buckets.get(tf)) for tf in self.required_timeframes)
        )
        key = price, as_of, bucket_key
        if key == self._last_key:
            return self._last_result
        self._last_as_of = as_of
        rows, values = [], {}
        for row in self.rows:
            value, reason = self._value(row, price, as_of, buckets)
            values[row.slot] = value
            native_bucket = (
                None
                if row.seed is None
                else row.seed.bucket
                if buckets is None
                else buckets.get(row.timeframe)
            )
            field = (
                "rsi"
                if self.indicator_id in {"htf_rsi_score", "rsi_snapshot"}
                else self.indicator_id.removesuffix("_votes")
            )
            rows.append(
                {
                    "slot": row.slot,
                    "timeframe": row.timeframe,
                    "enabled": row.enabled,
                    "value": value,
                    field: value,
                    "ready": value is not None,
                    "reason": reason,
                    "observed_at": as_of,
                    "native_time": native_bucket.time if native_bucket is not None else None,
                    "native_end": native_bucket.end if native_bucket is not None else None,
                }
            )
        required = [row for row in self.rows if row.seed]
        if not required or any(values[row.slot] is None for row in required):
            return self._unknown("live_native_state_incomplete", rows)
        active_count = sum(row.enabled for row in self.rows)
        if self.indicator_id == "htf_rsi_score":
            total_weight = sum(row.weight for row in required)
            score = sum(values[row.slot] * row.weight for row in required) / total_weight
            buy, sell = score <= self.inputs["dipThresh"], score >= self.inputs["tepeThresh"]
            outputs = {"score": score, "buy_zone": float(buy), "sell_zone": float(sell)}
            first_only = True
            for row, public in zip(self.rows, rows):
                public["weight"] = row.weight
        elif self.indicator_id == "rsi_snapshot":
            dip_score = top_score = 0.0
            for row, public in zip(self.rows, rows):
                slot, value = row.slot, values[row.slot]
                dip = (
                    row.dip_streak + 1
                    if value is not None and value < self.inputs[f"dipThr{slot}"]
                    else 0
                )
                top = (
                    row.top_streak + 1
                    if value is not None and value > self.inputs[f"topThr{slot}"]
                    else 0
                )
                args = (
                    self.inputs[f"tfPts{slot}"],
                    self.inputs[f"serialPts{slot}"],
                    self.inputs["maxStreak"],
                )
                dip_points = _points(dip, *args) if row.enabled else 0.0
                top_points = _points(top, *args) if row.enabled else 0.0
                dip_score += dip_points
                top_score += top_points
                public.update(
                    dip_streak=dip, top_streak=top, dip_score=dip_points, top_score=top_points
                )
            buy, sell = (
                dip_score >= self.inputs["dipTargetScore"],
                top_score >= self.inputs["topTargetScore"],
            )
            outputs = {"dip_score": dip_score, "top_score": top_score}
            first_only = False
        else:
            buy_votes = sell_votes = 0
            for row, public in zip(self.rows, rows):
                slot, value = row.slot, values[row.slot]
                buy_vote = value is not None and value <= self.inputs[f"dipThr{slot}"]
                sell_vote = value is not None and value >= self.inputs[f"topThr{slot}"]
                buy_votes += buy_vote
                sell_votes += sell_vote
                public.update(
                    buy_vote=buy_vote,
                    sell_vote=sell_vote,
                    buy_threshold=self.inputs[f"dipThr{slot}"],
                    sell_threshold=self.inputs[f"topThr{slot}"],
                )
            buy_reachable = active_count >= self.inputs["requiredBuyVotes"]
            sell_reachable = active_count >= self.inputs["requiredSellVotes"]
            buy = buy_reachable and buy_votes >= self.inputs["requiredBuyVotes"]
            sell = sell_reachable and sell_votes >= self.inputs["requiredSellVotes"]
            outputs = {
                "buy_votes": float(buy_votes),
                "sell_votes": float(sell_votes),
                "buy_zone": float(buy),
                "sell_zone": float(sell),
                "buy_reachable": float(buy_reachable),
                "sell_reachable": float(sell_reachable),
            }
            first_only = self.inputs["onlyFirst"]
        if first_only:
            buy_signal = bool(
                buy and self._previous_zones is not None and not self._previous_zones[0]
            )
            sell_signal = bool(
                sell and self._previous_zones is not None and not self._previous_zones[1]
            )
        else:
            buy_signal, sell_signal = buy, sell
        self._previous_zones = buy, sell
        outputs.update(
            buy_signal=float(buy_signal),
            sell_signal=float(sell_signal),
            any_signal=float(buy_signal or sell_signal),
            active_count=float(active_count),
            ready_count=float(len(required)),
        )
        result = {
            "outputs": outputs,
            "rows": rows,
            "ready": True,
            "reason": None,
            "observed_at": as_of,
        }
        self._last_key, self._last_result = key, result
        return result


def compile_live(
    indicator_id, inputs, frames, chart_timeframe="1D", *, previous=None, continuity=False
):
    """Compile native closed state once; retain at most ten compact row seeds.

    A verified normal native rollover can preserve edge state with explicit
    ``continuity=True, previous=...``. Revisions, reconnects or uncertain history
    must leave that option false, so an unknown interval cannot create an edge.
    """
    from .catalog import SPECS, validate_base, validate_config

    inputs = validate_config(indicator_id, inputs, chart_timeframe)
    validate_base(indicator_id, inputs, chart_timeframe)
    rows, shared = [], {}
    if indicator_id == "htf_rsi_score":
        for slot, timeframe, _, _ in _WEIGHTED_FRAMES:
            enabled, weight = inputs[f"en_{slot}"], inputs[f"w_{slot}"]
            seed = (
                _compile_seed("rsi", frames.get(timeframe, ()), inputs["rsiLength"])
                if enabled and weight > 0
                else None
            )
            rows.append(_Row(slot, timeframe, enabled, seed, weight))
    else:
        family = (
            "snapshot" if indicator_id == "rsi_snapshot" else indicator_id.removesuffix("_votes")
        )
        for slot in range(1, 11):
            timeframe, enabled, length = (
                inputs[f"tf{slot}"],
                inputs[f"en{slot}"],
                inputs[f"len{slot}"],
            )
            momentum = inputs[f"mom{slot}"] if family == "rmi" else 1
            smooth_a = inputs[f"smoothA{slot}"] if family == "smi" else 1
            smooth_b = inputs[f"smoothB{slot}"] if family == "smi" else 1
            key = timeframe, length, momentum, smooth_a, smooth_b
            bars = frames.get(timeframe, ())
            if enabled and key not in shared:
                shared[key] = _compile_seed(family, bars, length, momentum, smooth_a, smooth_b)
            dip_streak = top_streak = 0
            if enabled and family == "snapshot" and bars:
                values = rsi_values([bar.close for bar in bars[:-1]], length)
                dip_streak = (
                    _streaks(values, inputs[f"dipThr{slot}"], below=True)[-1] if values else 0
                )
                top_streak = (
                    _streaks(values, inputs[f"topThr{slot}"], below=False)[-1] if values else 0
                )
            rows.append(
                _Row(
                    slot,
                    timeframe,
                    enabled,
                    shared.get(key) if enabled else None,
                    dip_streak=dip_streak,
                    top_streak=top_streak,
                )
            )
    evaluator = LiveEvaluator(indicator_id, inputs, rows, SPECS[indicator_id]["outputs"])
    if (
        continuity
        and previous is not None
        and previous.indicator_id == indicator_id
        and previous.inputs == inputs
    ):
        evaluator._previous_zones = previous._previous_zones
        evaluator._last_as_of = previous._last_as_of
    return evaluator


def estimate_live_cells(indicator_id, inputs, chart_timeframe="1D"):
    """Deterministic pre-bootstrap upper bound for compiled native state slots."""
    from .catalog import validate_base, validate_config

    settings = validate_config(indicator_id, inputs, chart_timeframe)
    validate_base(indicator_id, settings, chart_timeframe)
    cells = len(settings) + 8 * 10
    if indicator_id == "htf_rsi_score":
        return cells + 32 * sum(
            settings[f"en_{slot}"] and settings[f"w_{slot}"] > 0
            for slot, _, _, _ in _WEIGHTED_FRAMES
        )
    seen = set()
    for slot in range(1, 11):
        if not settings[f"en{slot}"]:
            continue
        momentum = settings.get(f"mom{slot}", 1)
        length = settings[f"len{slot}"]
        key = (
            settings[f"tf{slot}"],
            length,
            momentum,
            settings.get(f"smoothA{slot}", 1),
            settings.get(f"smoothB{slot}", 1),
        )
        if key in seen:
            continue
        seen.add(key)
        cells += 32
        if indicator_id == "rmi_votes":
            cells += momentum
        elif indicator_id == "smi_votes":
            cells += 2 * (length - 1)
    return cells
