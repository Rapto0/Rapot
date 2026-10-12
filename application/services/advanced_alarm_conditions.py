"""Bounded, typed alarm expressions. No source code or dynamic evaluation is accepted."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

TIMEFRAMES = frozenset({"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1wk", "1mo"})
FIELDS = frozenset(
    {
        "price",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "rsi",
        "ema",
        "sma",
        "macd",
        "macd_signal",
        "atr",
        "wr",
        "combo",
        "hunter",
    }
)
OPERATORS = frozenset({"gt", "gte", "lt", "lte", "eq", "crossed_above", "crossed_below"})
PERIOD_FIELDS = frozenset({"rsi", "ema", "sma", "atr", "wr"})
MAX_DEPTH = 4
MAX_LEAVES = 32
MAX_NODES = 63
MAX_PERIOD = 200
Resolver = Callable[[Mapping[str, Any]], tuple[float | None, float | None]]


def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Koşul değeri sonlu bir sayı olmalıdır.")
    try:
        result = float(value)
    except (ValueError, OverflowError):
        raise ValueError("Koşul değeri sonlu bir sayı olmalıdır.") from None
    if not math.isfinite(result) or abs(result) > 1e15:
        raise ValueError("Koşul değeri sonlu ve ±10¹⁵ sınırında olmalıdır.")
    return result


def _reference(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) - {"field", "timeframe", "period", "side"}:
        raise ValueError("Gösterge alanı geçersiz.")
    field = raw.get("field")
    if not isinstance(field, str) or field not in FIELDS:
        raise ValueError("Gösterge alanı desteklenmiyor.")
    result: dict[str, Any] = {"field": field}
    if "timeframe" in raw:
        timeframe = raw["timeframe"]
        if not isinstance(timeframe, str) or timeframe not in TIMEFRAMES:
            raise ValueError("Gösterge periyodu desteklenmiyor.")
        result["timeframe"] = timeframe
    if field in PERIOD_FIELDS:
        period = raw.get("period", 20 if field in {"ema", "sma"} else 14)
        if isinstance(period, bool) or not isinstance(period, int) or not 2 <= period <= MAX_PERIOD:
            raise ValueError("Gösterge uzunluğu 2–200 arasında tam sayı olmalıdır.")
        result["period"] = period
    elif "period" in raw:
        raise ValueError("Bu gösterge ayarlanabilir uzunluk kabul etmiyor.")
    if field in {"combo", "hunter"}:
        side = raw.get("side", "buy")
        if not isinstance(side, str) or side not in {"buy", "sell"}:
            raise ValueError("Skor yönü buy veya sell olmalıdır.")
        result["side"] = side
    elif "side" in raw:
        raise ValueError("Bu alan skor yönü kabul etmiyor.")
    return result


def validate_condition(raw: Any) -> dict[str, Any]:
    """Return a fresh canonical tree; reject excess size/depth and unknown fields."""
    leaves = nodes = 0

    def visit(node: Any, depth: int) -> dict[str, Any]:
        nonlocal leaves, nodes
        nodes += 1
        if depth > MAX_DEPTH or nodes > MAX_NODES or not isinstance(node, dict):
            raise ValueError("Koşul en fazla 4 seviye ve 32 karşılaştırma içerebilir.")
        op = node.get("op")
        if not isinstance(op, str):
            raise ValueError("Koşul işleci geçersiz.")
        if op in {"and", "or"}:
            children = node.get("children")
            if set(node) != {"op", "children"} or not isinstance(children, list):
                raise ValueError("Koşul grubu geçersiz.")
            if not 1 <= len(children) <= MAX_LEAVES:
                raise ValueError("Koşul grubu 1–32 öğe içermelidir.")
            return {"op": op, "children": [visit(child, depth + 1) for child in children]}
        leaves += 1
        if leaves > MAX_LEAVES or op not in OPERATORS or set(node) != {"op", "left", "right"}:
            raise ValueError("Koşul karşılaştırması geçersiz veya 32 öğe sınırını aşıyor.")
        right = node["right"]
        return {
            "op": op,
            "left": _reference(node["left"]),
            "right": _reference(right) if isinstance(right, dict) else _number(right),
        }

    return visit(raw, 1)


def field_key(ref: dict[str, Any], default_timeframe: str) -> str:
    """Stable cache/message key including the full indicator identity."""
    return ":".join(
        str(value)
        for value in (
            ref["field"],
            ref.get("timeframe", default_timeframe),
            ref.get("period", ""),
            ref.get("side", ""),
        )
    )


@dataclass(frozen=True, slots=True)
class PreparedCondition:
    """Immutable expression plan; never retains observations or provider state."""

    tree: tuple
    fields: tuple[Mapping[str, Any], ...]
    keys: tuple[str, ...]


def prepare_condition(condition: dict, default_timeframe: str) -> PreparedCondition:
    """Validate once and index repeated references for a configured rule revision."""
    if default_timeframe not in TIMEFRAMES:
        raise ValueError("Alarm periyodu desteklenmiyor.")
    indices: dict[str, int] = {}
    fields = []

    def operand(raw):
        if not isinstance(raw, dict):
            return raw  # Validation canonicalizes numeric constants to float.
        ref = {**raw, "timeframe": raw.get("timeframe", default_timeframe)}
        key = field_key(ref, default_timeframe)
        if key not in indices:
            indices[key] = len(fields)
            fields.append(MappingProxyType(ref))
        return indices[key]

    def visit(node: dict) -> tuple:
        if node["op"] in {"and", "or"}:
            return node["op"], tuple(visit(child) for child in node["children"])
        return node["op"], operand(node["left"]), operand(node["right"])

    tree = visit(validate_condition(condition))
    return PreparedCondition(tree=tree, fields=tuple(fields), keys=tuple(indices))


def condition_fields(condition: dict, default_timeframe: str) -> list[dict[str, Any]]:
    return [dict(ref) for ref in prepare_condition(condition, default_timeframe).fields]


def evaluate_condition(
    condition: dict, resolver: Resolver, default_timeframe: str
) -> dict[str, Any]:
    """Evaluate supplied observations; missing OR branches stay unknown, never false.

    Resolver supplies current/previous values from one consistent snapshot. It
    owns freshness, provider time and bar-finality checks. Repeated field reads
    within a tree are shared. Crossing needs two actual, contiguous observations.
    """
    return evaluate_prepared_condition(prepare_condition(condition, default_timeframe), resolver)


def evaluate_prepared_condition(plan: PreparedCondition, resolver: Resolver) -> dict[str, Any]:
    """Evaluate a validated plan against this call's observations, without AST rebuilding.

    The caller still owns freshness, continuity, credentials and bar-finality
    checks for every snapshot. A plan may be shared; an evaluated result may not.
    """
    observations: list[tuple[float | None, float | None]] = []
    values: dict[str, float] = {}
    for ref, key in zip(plan.fields, plan.keys, strict=True):
        pair = resolver(ref)
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            pair = (None, None)
        current, previous = pair
        normalized = []
        for item in (current, previous):
            try:
                normalized.append(_number(item))
            except ValueError:
                normalized.append(None)
        observations.append((normalized[0], normalized[1]))
        if normalized[0] is not None:
            values[key] = normalized[0]
    missing = any(pair[0] is None for pair in observations)

    def operand(ref: int | float, index: int) -> float | None:
        return observations[ref][index] if isinstance(ref, int) else ref

    def compare(node: tuple, index: int) -> bool | None:
        op = node[0]
        if op in {"and", "or"}:
            children = [compare(child, index) for child in node[1]]
            if any(child is None for child in children):
                return None
            return all(children) if op == "and" else any(children)
        left, right = operand(node[1], index), operand(node[2], index)
        if left is None or right is None:
            return None
        if op in {"crossed_above", "crossed_below"}:
            if index:
                # Crossing is an event on this pair, not an assumed prior event.
                return False
            previous_left, previous_right = operand(node[1], 1), operand(node[2], 1)
            if previous_left is None or previous_right is None:
                return None
            if op == "crossed_above":
                return previous_left <= previous_right and left > right
            return previous_left >= previous_right and left < right
        if op == "gt":
            return left > right
        if op == "gte":
            return left >= right
        if op == "lt":
            return left < right
        if op == "lte":
            return left <= right
        return left == right

    matched = None if missing else compare(plan.tree, 0)
    previous_matched = compare(plan.tree, 1)
    return {
        "ready": matched is not None,
        "reason": None
        if matched is not None
        else "Koşul için yeterli ve kesintisiz veri bekleniyor.",
        "matched": matched,
        "previous_matched": previous_matched,
        "previous_ready": previous_matched is not None,
        "value": next(iter(values.values()), None),
        "values": values,
    }
