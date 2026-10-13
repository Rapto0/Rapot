"""Native rollover state commits match full history without calendar guesses."""

import math
from dataclasses import replace

import pytest

from application.services.custom_indicators.catalog import SPECS, requirements
from application.services.custom_indicators.core import Bar
from application.services.custom_indicators.live import compile_live, estimate_live_cells


def history(count=80):
    return tuple(
        Bar(
            i * 10.0,
            (i + 1) * 10.0,
            (close := 100 + math.sin(i / 3) * 8),
            close + 2,
            close - 2,
            close,
            True,
        )
        for i in range(count)
    )


def single(indicator):
    if indicator == "htf_rsi_score":
        return {
            item["key"]: item["key"] == "en_1d"
            for item in SPECS[indicator]["inputs"]
            if item["key"].startswith("en_")
        }
    return {f"en{i}": i == 1 for i in range(1, 11)}


def reference_wilder(closes, length, momentum=1, *, initial_zero=False):
    """Independent full-prefix reference, including the initial SMA sample."""
    changes = [closes[i] - closes[i - momentum] for i in range(momentum, len(closes))]
    if initial_zero:
        changes.insert(0, 0.0)
    if len(changes) < length:
        return None
    gains = [max(value, 0.0) for value in changes]
    losses = [max(-value, 0.0) for value in changes]
    gain, loss = math.fsum(gains[:length]) / length, math.fsum(losses[:length]) / length
    for up, down in zip(gains[length:], losses[length:]):
        gain += (up - gain) / length
        loss += (down - loss) / length
    if loss == 0:
        return 100.0 if gain > 0 and not initial_zero else None
    return 100.0 - 100.0 / (1.0 + gain / loss)


@pytest.mark.parametrize(
    ("indicator", "length", "momentum"),
    (("rsi_votes", 5, 1), ("rmi_votes", 5, 3), ("rsi_votes", 9999, 1), ("rmi_votes", 5000, 5000)),
)
def test_first_live_wilder_seed_and_rollover_match_independent_full_prefix(
    indicator, length, momentum
):
    first = length + momentum - 1
    native = history(first + 5)
    settings = single(indicator) | {"len1": length}
    if indicator == "rmi_votes":
        settings["mom1"] = momentum
    assert requirements(indicator, settings)[0]["bars"] <= 10000
    too_early = compile_live(
        indicator,
        settings,
        {"1D": (*native[: first - 1], replace(native[first - 1], confirmed=False))},
    )
    assert not too_early.evaluate(price=native[first - 1].close, as_of=native[first - 1].time + 1)[
        "ready"
    ]
    evaluator = compile_live(
        indicator, settings, {"1D": (*native[:first], replace(native[first], confirmed=False))}
    )
    cells = evaluator.retained_cells
    for index in range(first, first + 3):
        for tick, delta in enumerate((0.0, -1.0, 1.0, 0.0)):
            price = native[index].close + delta
            point = evaluator.evaluate(price=price, as_of=native[index].time + 1 + tick)
            assert point["ready"]
            assert point["rows"][0]["value"] == pytest.approx(
                reference_wilder([bar.close for bar in native[:index]] + [price], length, momentum),
                abs=1e-11,
            )
        assert evaluator.advance_native(
            "1D", native[index], replace(native[index + 1], confirmed=False)
        )
        assert evaluator.retained_cells == cells


def test_snapshot_first_live_manual_seed_does_not_require_a_completed_closed_seed():
    native = history(10)
    settings = single("rsi_snapshot") | {"len1": 5}
    current = replace(native[4], confirmed=False)
    evaluator = compile_live("rsi_snapshot", settings, {"1D": (*native[:4], current)})
    for tick, price in enumerate((99.0, 95.0, 99.0)):
        value = evaluator.evaluate(price=price, as_of=current.time + 1 + tick)
        assert value["ready"]
        assert value["rows"][0]["value"] == pytest.approx(
            reference_wilder([bar.close for bar in native[:4]] + [price], 5, initial_zero=True)
        )


@pytest.mark.parametrize("indicator", tuple(SPECS))
def test_closed_market_seed_is_unknown_then_commits_pending_bar_exactly_once(indicator):
    native = history()
    settings = single(indicator)
    evaluator = compile_live(indicator, settings, {"1D": native[:31]})
    before = evaluator.rows
    point = evaluator.evaluate(price=native[30].close, as_of=native[30].time + 1)
    assert not point["ready"]
    assert point["rows"][0]["reason"] == "current_native_bucket_missing"
    assert evaluator.rows is before
    cells = evaluator.retained_cells
    for index in (30, 31):
        following = replace(native[index + 1], confirmed=False)
        assert evaluator.advance_native("1D", native[index], following)
        after = evaluator.rows
        assert not evaluator.advance_native("1D", native[index], following)
        assert evaluator.rows is after
        expected = compile_live(indicator, settings, {"1D": (*native[: index + 1], following)})
        quote = {"price": following.close - 0.5, "as_of": following.time + 1}
        actual, full = evaluator.evaluate(**quote), expected.evaluate(**quote)
        assert actual["ready"] and full["ready"]
        assert actual["rows"][0]["value"] == pytest.approx(full["rows"][0]["value"], abs=1e-11)
        assert evaluator.retained_cells == cells


@pytest.mark.parametrize("indicator", tuple(SPECS))
def test_native_incremental_rollovers_match_full_history_after_each_tick(indicator):
    native = history()
    settings = single(indicator)
    current = replace(native[30], confirmed=False)
    evaluator = compile_live(indicator, settings, {"1D": (*native[:30], current)})
    cells = evaluator.retained_cells
    for index in range(30, 60):
        current = replace(native[index], confirmed=False)
        reference = compile_live(indicator, settings, {"1D": (*native[:index], current)})
        for tick, delta in enumerate((0, 0.5, -0.5)):
            point = evaluator.evaluate(
                price=current.close + delta, as_of=current.time + 1 + tick / 10
            )
            expected = reference.evaluate(
                price=current.close + delta, as_of=current.time + 1 + tick / 10
            )
            assert point["ready"] == expected["ready"]
            assert point["rows"][0]["value"] == pytest.approx(
                expected["rows"][0]["value"], abs=1e-11
            )
            for field in ("dip_score", "top_score", "buy_votes", "sell_votes", "score"):
                if field in point["outputs"]:
                    assert point["outputs"][field] == pytest.approx(
                        expected["outputs"][field], abs=1e-11
                    )
        assert evaluator.advance_native(
            "1D", native[index], replace(native[index + 1], confirmed=False)
        )
        assert evaluator.retained_cells == cells
        assert not evaluator.advance_native(
            "1D", native[index], replace(native[index + 1], confirmed=False)
        )


@pytest.mark.parametrize("family", ("rmi_votes", "smi_votes"))
def test_native_incremental_long_tail_matches_full_prefix_and_is_bounded(family):
    native = history(240)
    settings = single(family) | (
        {"mom1": 31, "len1": 7}
        if family == "rmi_votes"
        else {"len1": 47, "smoothA1": 7, "smoothB1": 4}
    )
    evaluator = compile_live(
        family, settings, {"1D": (*native[:70], replace(native[70], confirmed=False))}
    )
    for index in range(70, 190):
        current = replace(native[index], confirmed=False)
        expected = compile_live(family, settings, {"1D": (*native[:index], current)})
        quote = current.close + 0.25
        assert evaluator.evaluate(price=quote, as_of=current.time + 1)["rows"][0][
            "value"
        ] == pytest.approx(
            expected.evaluate(price=quote, as_of=current.time + 1)["rows"][0]["value"], abs=1e-11
        )
        assert evaluator.retained_cells == estimate_live_cells(family, settings)
        assert evaluator.advance_native(
            "1D", native[index], replace(native[index + 1], confirmed=False)
        )


def test_native_incremental_duplicate_slots_share_seed_but_snapshot_thresholds_are_independent():
    native = history()
    settings = single("rsi_snapshot") | {
        "en2": True,
        "tf2": "1D",
        "dipThr1": 60.0,
        "dipThr2": 80.0,
        "len1": 5,
        "len2": 5,
    }
    evaluator = compile_live(
        "rsi_snapshot", settings, {"1D": (*native[:30], replace(native[30], confirmed=False))}
    )
    assert evaluator.rows[0].seed is evaluator.rows[1].seed
    assert evaluator.retained_cells == estimate_live_cells("rsi_snapshot", settings)
    for index in range(30, 60):
        assert evaluator.advance_native(
            "1D", native[index], replace(native[index + 1], confirmed=False)
        )
        expected = compile_live(
            "rsi_snapshot",
            settings,
            {"1D": (*native[: index + 1], replace(native[index + 1], confirmed=False))},
        )
        assert evaluator.rows[0].seed is evaluator.rows[1].seed
        assert [(row.dip_streak, row.top_streak) for row in evaluator.rows] == [
            (row.dip_streak, row.top_streak) for row in expected.rows
        ]


def test_native_rollover_rejects_revision_gap_identity_and_partial_mutation():
    native = history()
    settings = single("smi_votes")
    current, following = replace(native[30], confirmed=False), replace(native[31], confirmed=False)
    evaluator = compile_live("smi_votes", settings, {"1D": (*native[:30], current)})
    evaluator.evaluate(price=current.high + 5, as_of=current.time + 1)
    before = evaluator.rows
    for closed, new in (
        (native[30], following),  # Closed range excludes an observed live high.
        (replace(native[30], time=301), following),
        (replace(native[30], open=native[30].open + 1), following),
        (replace(native[30], confirmed=False), following),
        (native[30], replace(following, time=299)),
        (native[30], replace(following, confirmed=True)),
    ):
        assert not evaluator.advance_native("1D", closed, new)
        assert evaluator.rows is before
    enlarged = replace(native[30], high=current.high + 5)
    assert evaluator.advance_native("1D", enlarged, following)
    assert evaluator.current_range("1D") == (following.high, following.low)


def test_unknown_native_end_rollover_uses_provider_pair_without_duration_inference():
    native = history()
    current = replace(native[30], end=None, confirmed=False)
    settings = single("rsi_votes") | {"tf1": "3D"}
    evaluator = compile_live("rsi_votes", settings, {"3D": (*native[:30], current)}, "3D")
    evaluator.evaluate(price=current.close, as_of=301, buckets={"3D": current})
    following = replace(native[31], time=427, end=None, confirmed=False)
    assert evaluator.advance_native("3D", replace(current, confirmed=True), following)
    assert evaluator.evaluate(price=following.close, as_of=428, buckets={"3D": following})["ready"]


def test_verified_rollover_preserves_live_edge_baseline_and_uncertain_future_does_not_commit():
    native = history()
    settings = single("rsi_votes") | {"onlyFirst": True, "dipThr1": 45.0}
    current = replace(native[30], confirmed=False)
    evaluator = compile_live("rsi_votes", settings, {"1D": (*native[:30], current)})
    evaluator.evaluate(price=current.close, as_of=301)
    prior = evaluator._previous_zones
    assert evaluator.advance_native("1D", native[30], replace(native[31], confirmed=False))
    assert evaluator._previous_zones == prior
    unknown_end = replace(native[31], end=None, confirmed=False)
    evaluator = compile_live("rsi_votes", settings, {"1D": (*native[:31], unknown_end)})
    evaluator.evaluate(price=unknown_end.close, as_of=321, buckets={"1D": unknown_end})
    assert not evaluator.advance_native(
        "1D", replace(unknown_end, confirmed=True), replace(native[32], confirmed=False)
    )


@pytest.mark.parametrize("indicator", tuple(SPECS))
def test_estimated_cell_budget_bounds_compiled_state_for_all_enabled_frames(indicator):
    native = history()
    frames = dict.fromkeys(
        ("1D", "2D", "3D", "4D", "5D", "6D", "7D", "1W", "2W", "3W", "1M"),
        (*native[:-1], replace(native[-1], confirmed=False)),
    )
    settings = {} if indicator == "htf_rsi_score" else {f"en{i}": True for i in range(1, 11)}
    evaluator = compile_live(indicator, settings, frames)
    assert evaluator.retained_cells == estimate_live_cells(indicator, settings)
    missing = compile_live(indicator, settings, {})
    assert missing.retained_cells <= estimate_live_cells(indicator, settings)
