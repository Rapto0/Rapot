"""Expressions operate on observations, never execute user source code."""

import math

import pytest

from application.services.advanced_alarm_conditions import (
    condition_fields,
    evaluate_condition,
    validate_condition,
)


def leaf(field="price", op="gt", right=100, **params):
    return {"op": op, "left": {"field": field, **params}, "right": right}


def test_normalization_is_independent_and_preserves_multitimeframe_identity():
    raw = {"op": "and", "children": [leaf("rsi"), leaf("rsi", timeframe="1d")]}
    tree = validate_condition(raw)
    fields = condition_fields(tree, "15m")
    assert fields == [
        {"field": "rsi", "period": 14, "timeframe": "15m"},
        {"field": "rsi", "period": 14, "timeframe": "1d"},
    ]
    tree["children"][0]["left"]["period"] = 7
    assert "period" not in raw["children"][0]["left"]


@pytest.mark.parametrize("value", [True, None, "100", math.nan, math.inf, 10**400])
def test_thresholds_reject_nonfinite_boolean_and_code_like_values(value):
    with pytest.raises(ValueError):
        validate_condition(leaf(right=value))


@pytest.mark.parametrize(
    "raw",
    [
        leaf("__import__('os').system('x')"),
        {**leaf(), "python": "print('untrusted')"},
        leaf("rsi", period=True),
        leaf("rsi", period=201),
        leaf("price", period=14),
        leaf("price", timeframe="1s"),
        leaf("rsi", side="buy"),
        leaf("hunter", side="unknown"),
        {"op": "or", "children": []},
        {"op": "and", "children": [leaf()] * 33},
    ],
)
def test_unbounded_or_unsupported_expressions_are_rejected(raw):
    with pytest.raises(ValueError):
        validate_condition(raw)


def test_depth_and_leaf_budgets_apply_to_whole_tree():
    too_deep = leaf()
    for _ in range(4):
        too_deep = {"op": "or", "children": [too_deep]}
    with pytest.raises(ValueError):
        validate_condition(too_deep)
    nested = {"op": "and", "children": [{"op": "or", "children": [leaf()] * 17}] * 2}
    with pytest.raises(ValueError):
        validate_condition(nested)
    cyclic = {"op": "and", "children": []}
    cyclic["children"].append(cyclic)
    with pytest.raises(ValueError):
        validate_condition(cyclic)


def test_nested_groups_compare_fields_and_resolve_shared_indicators_once():
    tree = {
        "op": "and",
        "children": [
            leaf("price", right={"field": "ema", "period": 20}),
            {"op": "or", "children": [leaf("rsi", right=50), leaf("rsi", op="lt", right=30)]},
        ],
    }
    calls = []

    def resolve(ref):
        calls.append(ref)
        return {"price": (101, 99), "ema": (100, 100), "rsi": (55, 45)}[ref["field"]]

    result = evaluate_condition(tree, resolve, "15m")
    assert result["ready"] and result["matched"] is True
    assert result["previous_matched"] is False
    assert len(calls) == 3
    assert len(result["values"]) == 3


def test_unknown_branch_cannot_be_hidden_by_true_or_false_and_branch():
    for op in ("and", "or"):
        tree = {"op": op, "children": [leaf(), leaf("rsi")]}
        result = evaluate_condition(
            tree, lambda ref: (101, 90) if ref["field"] == "price" else (None, 20), "1m"
        )
        assert result["ready"] is False and result["matched"] is None


@pytest.mark.parametrize(
    "op,pair,expected",
    [
        ("crossed_above", (101, 100), True),
        ("crossed_above", (100, 99), False),
        ("crossed_below", (99, 100), True),
        ("crossed_below", (101, 102), False),
    ],
)
def test_crossings_require_a_real_transition_with_equality_boundary(op, pair, expected):
    result = evaluate_condition(leaf(op=op), lambda _: pair, "1m")
    assert result["ready"] and result["matched"] is expected
    assert result["previous_matched"] is False


def test_crossing_without_previous_observation_is_unknown():
    result = evaluate_condition(leaf(op="crossed_above"), lambda _: (101, None), "1m")
    assert result["ready"] is False


def test_field_to_field_crossing_uses_both_previous_values():
    result = evaluate_condition(
        leaf("ema", op="crossed_above", period=10, right={"field": "ema", "period": 20}),
        lambda ref: (101, 98) if ref["period"] == 10 else (100, 99),
        "5m",
    )
    assert result["matched"] is True


def test_zero_values_and_negative_williams_values_are_valid():
    tree = {
        "op": "and",
        "children": [leaf("volume", op="eq", right=0), leaf("wr", op="lte", right=-80)],
    }
    result = evaluate_condition(
        tree, lambda ref: (0, 0) if ref["field"] == "volume" else (-90, -70), "1h"
    )
    assert result["ready"] and result["matched"] is True
    assert result["value"] == 0
