"""Versioned indicator contracts, input validation and native data requirements."""

import hashlib
import json
import math
import re
from copy import deepcopy

from .live import compile_live  # noqa: F401
from .score import SPECS as SCORE_SPECS
from .score import evaluate_score
from .votes import SPECS as VOTE_SPECS
from .votes import evaluate_votes

VERSION = 2
MAX_HISTORY = 10000
ALIASES = {
    "1m": "1",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1h": "60",
    "4h": "240",
    "1d": "1D",
    "1wk": "1W",
    "1mo": "1M",
}
SPECS = {item["id"]: item for item in (*SCORE_SPECS, *VOTE_SPECS)}


def canonical_timeframe(value: str, default: str = "1D") -> str:
    if not isinstance(value, str):
        raise ValueError("Periyot metin olmalıdır.")
    value = ALIASES.get(value, value.strip()) or default
    if value in {"D", "W", "M", "S"}:
        value = "1" + value
    match = re.fullmatch(r"([1-9][0-9]{0,3})([SDWM]?)", value)
    if not match:
        raise ValueError("Periyot dakika sayısı veya 1D, 3D, 1W, 1M gibi Pine biçiminde olmalıdır.")
    count, unit = int(match[1]), match[2]
    valid = (
        count in {1, 5, 10, 15, 30, 45}
        if unit == "S"
        else count <= {"": 1440, "D": 365, "W": 52, "M": 12}[unit]
    )
    if not valid:
        raise ValueError("Periyot desteklenen Pine aralığının dışında.")
    return f"{count}{unit}"


def timeframe_seconds(value: str) -> float:
    value = canonical_timeframe(value)
    match = re.fullmatch(r"(\d+)([SDWM]?)", value)
    return int(match[1]) * {"S": 1, "": 60, "D": 86400, "W": 604800, "M": 2628003}[match[2]]


def catalog() -> dict:
    return {
        "version": VERSION,
        "indicators": deepcopy(list(SPECS.values())),
        "max_history_bars": MAX_HISTORY,
        "live_policy": {
            "evaluation": "native_bucket_quote_update",
            "requires_primary_close": False,
            "signal_edges": "previous_continuous_live_observation",
            "history": "original_pine_replay",
        },
    }


def validate_config(indicator_id: str, inputs: dict | None, chart_timeframe: str = "1D") -> dict:
    spec = SPECS.get(indicator_id) if isinstance(indicator_id, str) else None
    if spec is None:
        raise ValueError("Özel gösterge desteklenmiyor.")
    if inputs is None:
        inputs = {}
    if not isinstance(inputs, dict) or set(inputs) - {item["key"] for item in spec["inputs"]}:
        raise ValueError("Göstergenin tanımlamadığı bir ayar gönderildi.")
    base = canonical_timeframe(chart_timeframe)
    result = {}
    for item in spec["inputs"]:
        key, kind = item["key"], item["type"]
        value = inputs.get(key, item["default"])
        if kind == "bool":
            valid = isinstance(value, bool)
        elif kind == "timeframe":
            value = canonical_timeframe(value, base)
            valid = True
        else:
            valid = not isinstance(value, bool) and isinstance(value, (int, float))
            valid = valid and abs(value) <= 1e12 and math.isfinite(value)
            if kind == "int":
                valid = valid and isinstance(value, int)
            valid = (
                valid
                and ("min" not in item or value >= item["min"])
                and ("max" not in item or value <= item["max"])
            )
        if not valid:
            raise ValueError(f"{item['label']} için geçersiz değer.")
        if kind == "float":
            value = float(value)
        result[key] = value
    return result


def validate_base(indicator_id: str, inputs: dict, chart_timeframe: str) -> None:
    base = canonical_timeframe(chart_timeframe)
    policy = SPECS[indicator_id]["base_policy"]
    if policy == "daily" and base != "1D":
        raise ValueError("RSI Snapshot göstergesi yalnız 1 günlük alarm periyodunda çalışır.")
    if policy == "minimum":
        frames = [inputs[f"tf{i}"] for i in range(1, 11) if inputs[f"en{i}"]]
        if not frames:
            raise ValueError("En az bir zaman dilimi satırı etkin olmalıdır.")
        minimum = min(frames, key=timeframe_seconds)
        if base != minimum:
            raise ValueError(
                f"Bu göstergenin alarm periyodu en küçük etkin satırla aynı olmalıdır: {minimum}."
            )
        for i in range(1, 11):
            if inputs[f"en{i}"] and inputs[f"dipThr{i}"] >= inputs[f"topThr{i}"]:
                raise ValueError(f"{i}. satırda DİP eşiği TEPE eşiğinden küçük olmalıdır.")


def config_key(indicator_id: str, inputs: dict, chart_timeframe: str = "1D") -> str:
    values = validate_config(indicator_id, inputs, chart_timeframe)
    visual = {item["key"] for item in SPECS[indicator_id]["inputs"] if item.get("visual")}
    payload = [
        VERSION,
        indicator_id,
        canonical_timeframe(chart_timeframe),
        {key: value for key, value in values.items() if key not in visual},
    ]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def requirements(indicator_id: str, inputs: dict, chart_timeframe: str = "1D") -> list[dict]:
    inputs = validate_config(indicator_id, inputs, chart_timeframe)
    validate_base(indicator_id, inputs, chart_timeframe)
    primary = canonical_timeframe(chart_timeframe)
    needed = {primary: 500}

    def add(timeframe, length, momentum=1):
        # Finite seed history is explicit. Long recursions request extra warmup;
        # it never silently truncates the user's requested oscillator length.
        minimum = length + momentum
        if minimum > MAX_HISTORY:
            raise ValueError(
                f"Bu ayar en az {minimum:,} mum ister; sağlayıcı sınırı {MAX_HISTORY:,}. Uzunluğu veya momentumu azaltın."
            )
        bars = min(MAX_HISTORY, max(500, minimum + 500))
        needed[timeframe] = max(needed.get(timeframe, 0), bars)

    if indicator_id == "htf_rsi_score":
        for key, timeframe in zip(
            ("1d", "2d", "3d", "4d", "5d", "6d", "1w", "2w", "3w", "1m"),
            ("1D", "2D", "3D", "4D", "5D", "6D", "1W", "2W", "3W", "1M"),
        ):
            if inputs[f"en_{key}"] and inputs[f"w_{key}"] > 0:
                add(timeframe, inputs["rsiLength"])
    else:
        for i in range(1, 11):
            if inputs[f"en{i}"]:
                length = inputs[f"len{i}"]
                if indicator_id == "smi_votes":
                    length = max(length, inputs[f"smoothA{i}"], inputs[f"smoothB{i}"])
                add(inputs[f"tf{i}"], length, inputs.get(f"mom{i}", 1))
        if indicator_id == "smi_votes":
            # Developing SMI needs the primary high/low range from the native
            # HTF bucket start. This estimates only a bounded fetch budget;
            # calendar boundaries still come exclusively from native bars.
            spans = [
                int(inputs[f"tf{i}"][:-1]) * 31 * 86400
                if inputs[f"tf{i}"].endswith("M")
                else timeframe_seconds(inputs[f"tf{i}"])
                for i in range(1, 11)
                if inputs[f"en{i}"]
            ]
            coverage = math.ceil(max(spans) / timeframe_seconds(primary)) + 500
            needed[primary] = max(needed[primary], min(MAX_HISTORY, coverage))
    return [{"timeframe": tf, "bars": bars} for tf, bars in sorted(needed.items())]


def evaluate(indicator_id, inputs, primary, frames, chart_timeframe="1D", as_of=None):
    inputs = validate_config(indicator_id, inputs, chart_timeframe)
    validate_base(indicator_id, inputs, chart_timeframe)
    function = (
        evaluate_score if indicator_id in {"htf_rsi_score", "rsi_snapshot"} else evaluate_votes
    )
    return function(
        indicator_id,
        inputs,
        primary,
        frames,
        chart_timeframe=canonical_timeframe(chart_timeframe),
        as_of=as_of,
    )
