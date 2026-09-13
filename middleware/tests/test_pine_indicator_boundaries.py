"""Numeric oracles for two extracted Pine function bodies, not a Pine runtime.

Only the arithmetic/control-flow subset used by calcEma/calcAtr is interpreted.
This does not compile Pine, emulate realtime rollback, or prove engine equivalence.
Pine for loops include both bounds and descend when the start exceeds the end:
https://www.tradingview.com/pine-script-docs/language/loops/#for-loops
"""

from __future__ import annotations

import ast
import math
import operator
import re
import textwrap
from pathlib import Path

import pytest

PINE = (Path(__file__).resolve().parents[1] / "pine/combo_hunter_binance.pine").read_text(
    encoding="utf-8"
)
OPERATIONS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
COMPARISONS = {ast.Gt: operator.gt, ast.GtE: operator.ge}


def pine_range(start: int, end: int) -> range:
    """The extracted loops have immutable bounds and the default positive step."""
    step = 1 if end >= start else -1
    return range(start, end + step, step)


class HtfFixture:
    """Closed candles followed by one developing candle, matching Pine accessors.

    The real accessors alias every index >= closed size to developing OHLC.
    Preserve that behavior so an erroneous loop fails numerically, and log reads
    so equal-valued updates cannot hide an out-of-range logical index.
    """

    def __init__(self, candles: list[tuple[float, float, float]]) -> None:
        assert candles
        self.closed = candles[:-1]
        self.developing = candles[-1]
        self.reads: list[tuple[str, int]] = []

    def total(self) -> int:
        return len(self.closed) + 1

    def get(self, field: str, index: int) -> float:
        assert index >= 0
        self.reads.append((field, index))
        candle = self.closed[index] if index < len(self.closed) else self.developing
        return candle[{"getH": 0, "getL": 1, "getC": 2}[field]]


def extracted_body(name: str) -> ast.Module:
    """Translate only the known syntax; unsupported statements fail in the evaluator."""
    assert name in {"calcEma", "calcAtr"}
    match = re.search(rf"^{name}\([^\n]*\) =>\n((?:    [^\n]*\n|\n)+)", PINE, re.MULTILINE)
    assert match is not None, f"Missing Pine function: {name}"
    translated = []
    for line in textwrap.dedent(match.group(1)).splitlines():
        line = re.sub(r"^(\s*)(?:int|float) ", r"\1", line).replace(":=", "=")
        if loop := re.fullmatch(r"(\s*)for i = (.+) to (.+)", line):
            indent, start, end = loop.groups()
            line = f"{indent}for i in pine_range({start}, {end}):"
        elif line.lstrip().startswith("if "):
            line += ":"
        translated.append(line)
    return ast.parse("\n".join(translated))


class ArithmeticSubset:
    """Explicit AST interpreter; no eval/exec or arbitrary attribute/call access."""

    def __init__(self, htf: HtfFixture, length: int) -> None:
        self.htf = htf
        self.values = {"len": length, "na": math.nan}

    def expression(self, node: ast.expr) -> float | int | bool | range:
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
            return node.value
        if isinstance(node, ast.Name):
            assert node.id in self.values, f"Unknown name: {node.id}"
            return self.values[node.id]
        if isinstance(node, ast.BinOp) and type(node.op) in OPERATIONS:
            return OPERATIONS[type(node.op)](
                self.expression(node.left), self.expression(node.right)
            )
        if (
            isinstance(node, ast.Compare)
            and len(node.ops) == 1
            and type(node.ops[0]) in COMPARISONS
        ):
            return COMPARISONS[type(node.ops[0])](
                self.expression(node.left), self.expression(node.comparators[0])
            )
        if isinstance(node, ast.Call) and not node.keywords:
            args = [self.expression(arg) for arg in node.args]
            if isinstance(node.func, ast.Name) and node.func.id == "pine_range":
                assert len(args) == 2 and all(type(arg) is int for arg in args)
                return pine_range(*args)
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                owner, method = node.func.value.id, node.func.attr
                if (owner, method) == ("htf", "total") and not args:
                    return self.htf.total()
                if owner == "htf" and method in {"getC", "getH", "getL"}:
                    assert len(args) == 1 and type(args[0]) is int
                    return self.htf.get(method, args[0])
                if owner == "math" and method == "max" and len(args) == 2:
                    return max(args)
                if owner == "math" and method == "abs" and len(args) == 1:
                    return abs(args[0])
        raise AssertionError(f"Unsupported Pine expression: {ast.dump(node)}")

    def statements(self, nodes: list[ast.stmt]) -> None:
        for node in nodes:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                assert isinstance(target, ast.Name)
                self.values[target.id] = self.expression(node.value)
            elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                assert type(node.op) in OPERATIONS
                self.values[node.target.id] = OPERATIONS[type(node.op)](
                    self.values[node.target.id], self.expression(node.value)
                )
            elif isinstance(node, ast.If) and not node.orelse:
                if self.expression(node.test):
                    self.statements(node.body)
            elif isinstance(node, ast.For) and not node.orelse:
                assert isinstance(node.target, ast.Name) and node.target.id == "i"
                indices = self.expression(node.iter)
                assert isinstance(indices, range) and len(indices) <= 100
                for index in indices:
                    self.values["i"] = index
                    self.statements(node.body)
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Name):
                assert node.value.id == "result"
            else:
                raise AssertionError(f"Unsupported Pine statement: {ast.dump(node)}")


def calculate(
    name: str, candles: list[tuple[float, float, float]], length: int
) -> tuple[float, HtfFixture]:
    htf = HtfFixture(candles)
    evaluator = ArithmeticSubset(htf, length)
    evaluator.statements(extracted_body(name).body)
    return float(evaluator.values["result"]), htf


@pytest.mark.parametrize("start,end,expected", [(0, 2, [0, 1, 2]), (3, 2, [3, 2]), (3, 3, [3])])
def test_pine_loop_bounds_are_inclusive_and_directional(
    start: int, end: int, expected: list[int]
) -> None:
    assert list(pine_range(start, end)) == expected


@pytest.mark.parametrize("expression", ["__import__('os')", "htf.__class__", "math.sqrt(4)"])
def test_arithmetic_subset_rejects_unsupported_expressions(expression: str) -> None:
    evaluator = ArithmeticSubset(HtfFixture([(11, 9, 10)]), 1)
    with pytest.raises(AssertionError, match="Unsupported Pine expression"):
        evaluator.expression(ast.parse(expression, mode="eval").body)


@pytest.mark.parametrize("length", [1, 3, 12, 20, 26])
@pytest.mark.parametrize("extra", [0, 1])
def test_ema_seed_and_one_continuation_include_developing_once(length: int, extra: int) -> None:
    # Closes 10,20,...: seed mean = 5*(length+1), next recurrence adds exactly 10.
    # length=3 gives the independent hand-calculated goldens 20 and 30.
    closes = [float(10 * index) for index in range(1, length + extra + 1)]
    candles = [(close + 1, close - 1, close) for close in closes]
    result, htf = calculate("calcEma", candles, length)
    assert result == pytest.approx(5 * (length + 1) + 10 * extra)
    assert htf.reads == [("getC", index) for index in range(len(candles))]


@pytest.mark.parametrize("length", [1, 3, 12, 20, 26])
@pytest.mark.parametrize("extra", [0, 1])
def test_atr_seed_and_one_continuation_include_developing_once(length: int, extra: int) -> None:
    # First length-1 true ranges are 2; the gap at the developing seed bar gives 9.
    # length=3 seed is 13/3. The optional next bar's TR=2 gives 32/9.
    closes = [float(10 + index) for index in range(length)] + [float(17 + length)]
    if extra:
        closes.append(closes[-1] + 1)
    candles = [(close + 1, close - 1, close) for close in closes]
    result, htf = calculate("calcAtr", candles, length)
    expected = 2 + 7 / length if not extra else 2 + 7 * (length - 1) / (length * length)
    assert result == pytest.approx(expected)
    # Each TR makes one getH(i) for its range and another for the previous-close gap.
    high_reads = [index for field, index in htf.reads if field == "getH"]
    assert high_reads == [index for index in range(1, len(candles)) for _ in range(2)]
    assert all(0 <= index < len(candles) for _, index in htf.reads)


@pytest.mark.parametrize(
    "name,length,count",
    [("calcEma", 3, 2), ("calcEma", 20, 19), ("calcAtr", 3, 3), ("calcAtr", 12, 12)],
)
def test_below_seed_length_is_na_without_reading_candles(
    name: str, length: int, count: int
) -> None:
    result, htf = calculate(name, [(11, 9, 10)] * count, length)
    assert math.isnan(result)
    assert htf.reads == []
