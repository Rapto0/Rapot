"""Hand-calculated voting, snapshot, boundary and source-input contracts."""

import hashlib
import re
from dataclasses import replace
from pathlib import Path

import pytest

from application.services.custom_indicators.core import Bar
from application.services.custom_indicators.live import compile_live
from application.services.custom_indicators.votes import SPECS, evaluate_votes


def bars(closes, *, start=0, span=1, high=None, low=None):
    return tuple(
        Bar(
            time=start + index * span,
            end=start + (index + 1) * span,
            open=close,
            high=close + 1 if high is None else high,
            low=close - 1 if low is None else low,
            close=close,
            confirmed=True,
        )
        for index, close in enumerate(closes)
    )


def single(**overrides):
    return {
        "en3": False,
        "requiredBuyVotes": 1,
        "requiredSellVotes": 1,
        "len1": 2,
        **overrides,
    }


def smi_single(**overrides):
    return single(len1=1, smoothA1=1, smoothB1=1, **overrides)


def live_bars(closes=(10, 8, 9, 9), *, span=10, end_known=True):
    result = list(bars(closes, span=span))
    result[-1] = replace(result[-1], confirmed=False, end=result[-1].end if end_known else None)
    return tuple(result)


def test_live_rsi_all_native_frames_use_the_same_tick_without_waiting_for_close():
    daily = live_bars()
    three_day = live_bars((20, 18, 19, 19), span=8)
    compiler = compile_live("rsi_votes", {"len1": 2, "len3": 2}, {"1D": daily, "3D": three_day})
    point = compiler.evaluate(price=8, as_of=31, buckets={"1D": daily[-1], "3D": three_day[-1]})
    assert point["ready"]
    assert point["outputs"]["buy_votes"] == 2
    assert point["outputs"]["buy_signal"] == 1
    assert point["rows"][0]["rsi"] == pytest.approx(20)
    assert point["rows"][2]["rsi"] == pytest.approx(4)
    assert {row["observed_at"] for row in point["rows"] if row["enabled"]} == {31}
    assert not daily[-1].confirmed and not three_day[-1].confirmed


def test_live_rsi_each_tick_rolls_back_to_closed_seed_and_duplicate_is_idempotent():
    native = live_bars()
    compiler = compile_live("rsi_votes", single(), {"1D": native})
    first = compiler.evaluate(price=8, as_of=31)
    second = compiler.evaluate(price=10, as_of=32)
    third = compiler.evaluate(price=8, as_of=33)
    assert first["rows"][0]["value"] == pytest.approx(20)
    assert second["rows"][0]["value"] == pytest.approx(60)
    assert third["rows"][0]["value"] == first["rows"][0]["value"]
    assert compiler.evaluate(price=8, as_of=33) is third


def test_live_only_first_is_a_tick_edge_and_gap_reentry_is_baselined():
    native = live_bars()
    compiler = compile_live("rsi_votes", single(onlyFirst=True), {"1D": native})
    assert compiler.evaluate(price=8, as_of=31)["outputs"]["buy_signal"] == 0
    assert compiler.evaluate(price=10, as_of=32)["outputs"]["buy_signal"] == 0
    entry = compiler.evaluate(price=8, as_of=33)
    assert entry["outputs"]["buy_signal"] == 1
    assert compiler.evaluate(price=8, as_of=33) is entry
    assert compiler.evaluate(price=8, as_of=34)["outputs"]["buy_signal"] == 0
    assert not compiler.evaluate(price=8, as_of=35, buckets={})["ready"]
    assert compiler.evaluate(price=8, as_of=36)["outputs"]["buy_signal"] == 0
    compiler.reset()
    assert compiler.evaluate(price=8, as_of=37)["outputs"]["buy_signal"] == 0


def test_live_native_boundary_identity_and_unknown_end_are_not_calendar_guesses():
    native = live_bars(end_known=False)
    compiler = compile_live("rsi_votes", single(tf1="3D"), {"3D": native}, "3D")
    assert not compiler.evaluate(price=8, as_of=31)["ready"]
    assert compiler.evaluate(price=8, as_of=31, buckets={"3D": native[-1]})["ready"]
    next_bucket = replace(native[-1], time=31, end=51)
    result = compiler.evaluate(price=8, as_of=32, buckets={"3D": next_bucket})
    assert not result["ready"]
    assert result["rows"][0]["reason"] == "native_seed_recompile_required"
    assert not compiler.evaluate(price=8, as_of=29, buckets={"3D": native[-1]})["ready"]


def test_live_missing_enabled_frame_blocks_consensus_instead_of_lowering_votes():
    compiler = compile_live("rsi_votes", {"len1": 2, "len3": 2}, {"1D": live_bars()})
    point = compiler.evaluate(price=8, as_of=31)
    assert not point["ready"]
    assert point["outputs"]["buy_signal"] is None
    assert point["rows"][0]["ready"]
    assert not point["rows"][2]["ready"]


def test_live_rmi_rolls_back_momentum_native_rma_and_uses_current_price():
    native = live_bars((10, 9, 8, 10, 9, 9))
    compiler = compile_live("rmi_votes", single(mom1=2), {"1D": native})
    # Momentum changes -2,+1,+1 seed to gain .75/loss .5; current reference=10.
    assert compiler.evaluate(price=8, as_of=51)["rows"][0]["rmi"] == pytest.approx(23.0769230769)
    assert compiler.evaluate(price=12, as_of=52)["rows"][0]["rmi"] == pytest.approx(84.6153846154)
    assert compiler.evaluate(price=8, as_of=53)["rows"][0]["rmi"] == pytest.approx(23.0769230769)


def test_live_smi_uses_native_running_extremes_but_never_compounds_tick_ema():
    native = live_bars((10, 10))
    current = replace(native[-1], high=12, low=8)
    compiler = compile_live(
        "smi_votes", single(len1=1, smoothA1=3, smoothB1=3), {"1D": (*native[:-1], current)}
    )
    assert compiler.evaluate(price=11, as_of=11)["rows"][0]["smi"] == pytest.approx(20)
    assert compiler.evaluate(price=9, as_of=12)["rows"][0]["smi"] == pytest.approx(-20)
    assert compiler.evaluate(price=11, as_of=13)["rows"][0]["smi"] == pytest.approx(20)
    compiler.evaluate(price=15, as_of=14)
    assert compiler.evaluate(price=11, as_of=15)["rows"][0]["smi"] == pytest.approx(-100 / 13)


def test_live_smi_native_bucket_does_not_need_primary_range_reconstruction():
    native = live_bars((10, 8, 9, 9), span=8)
    compiler = compile_live("smi_votes", smi_single(tf1="3D"), {"3D": native}, "3D")
    point = compiler.evaluate(price=9.5, as_of=25)
    assert point["ready"] and point["outputs"]["sell_signal"] == 1
    assert point["rows"][0]["smi"] == pytest.approx(50)


def test_live_recompile_retains_only_verified_continuity_and_rejects_bad_native_seed():
    native = live_bars()
    first = compile_live("rsi_votes", single(onlyFirst=True), {"1D": native})
    first.evaluate(price=10, as_of=31)
    continued = compile_live(
        "rsi_votes", single(onlyFirst=True), {"1D": native}, previous=first, continuity=True
    )
    assert continued.evaluate(price=8, as_of=32)["outputs"]["buy_signal"] == 1
    reset = compile_live("rsi_votes", single(onlyFirst=True), {"1D": native}, previous=first)
    assert reset.evaluate(price=8, as_of=32)["outputs"]["buy_signal"] == 0
    corrupted = (*native[:1], replace(native[1], confirmed=False), *native[2:])
    invalid = compile_live("rsi_votes", single(), {"1D": corrupted})
    assert not invalid.evaluate(price=8, as_of=32)["ready"]


def test_live_pause_preserves_observed_native_extremes_and_timestamp_order():
    native = live_bars((10, 10))
    evaluator = compile_live("smi_votes", smi_single(onlyFirst=True), {"1D": native})
    assert evaluator.current_range("1D") == (11, 9)
    assert evaluator.current_range("3D") is None
    evaluator.evaluate(price=15, as_of=11)
    assert evaluator.current_range("1D") == (15, 9)
    evaluator.pause_signal_baseline()
    assert evaluator.current_range("1D") == (15, 9)
    assert evaluator.evaluate(price=15, as_of=12)["outputs"]["sell_signal"] == 0
    assert evaluator.evaluate(price=10, as_of=11)["reason"] == "out_of_order_observation"


@pytest.mark.parametrize(
    ("indicator_id", "expected_count", "digest"),
    [
        ("rsi_votes", 54, "1343c102018a4bddb26eb42555e605cc27dfdb69d453bbb3e3cc8aa928e0ad17"),
        ("smi_votes", 74, "a697e7913d839e48bdbfc5055058d91f904f4e4bc749f2af6b1fe6d62b43c3c7"),
        ("rmi_votes", 64, "ebd27a8fd6c65e7870aef11ebb3c0d42572d3f3799a2361c85632c0747ee68b6"),
    ],
)
def test_every_input_matches_retained_pine_source(indicator_id, expected_count, digest):
    path = Path(__file__).resolve().parents[1] / "indicators" / "pine" / f"{indicator_id}.pine"
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest
    text = raw.decode("utf-8")
    groups = dict(re.findall(r'const string (G\d+) = "([^"]+)"', text))
    declared = {}
    for line in text.splitlines():
        match = re.match(r'\w+ (\w+) = input\.(\w+)\(([^,]+), "([^"]+)"(.*)\)', line)
        if not match:
            continue
        key, kind, default, label, rest = match.groups()
        value = (
            default.strip('"')
            if kind == "timeframe"
            else default == "true"
            if kind == "bool"
            else int(default)
            if kind == "int"
            else float(default)
        )
        entry = {
            "key": key,
            "type": kind,
            "default": value,
            "label": label,
            "group": groups[re.search(r"group=(G\d+)", rest).group(1)],
        }
        for source_key, metadata_key in (("minval", "min"), ("maxval", "max"), ("step", "step")):
            bound = re.search(rf"\b{source_key}=(-?[\d.]+)", rest)
            if bound:
                entry[metadata_key] = float(bound.group(1))
        if key == "showTable":
            entry["visual"] = True
        declared[key] = entry
    spec = next(spec for spec in SPECS if spec["id"] == indicator_id)
    assert len(declared) == expected_count
    assert {item["key"]: item for item in spec["inputs"]} == declared
    assert spec["base_policy"] == "minimum"


def test_rsi_seed_preserves_first_missing_change_and_exact_thresholds():
    result = evaluate_votes("rsi_votes", single(dipThr1=50, topThr1=80), bars([10, 12, 10]), {})
    assert [r["rows"][0]["value"] for r in result] == [None, None, 50.0]
    assert result[-1]["outputs"]["buy_votes"] == 1
    assert result[-1]["outputs"]["buy_signal"] == 1


@pytest.mark.parametrize("indicator_id", ["rsi_votes", "rmi_votes"])
def test_flat_wilder_series_is_unknown_not_zero(indicator_id):
    result = evaluate_votes(indicator_id, single(mom1=1), bars([10] * 8), {})
    assert result[-1]["rows"][0]["value"] is None
    assert result[-1]["outputs"]["buy_signal"] is None
    assert not result[-1]["ready"]


@pytest.mark.parametrize(("closes", "expected"), [([1, 2, 3, 4], 100), ([4, 3, 2, 1], 0)])
def test_rmi_momentum_one_has_rsi_monotone_endpoints(closes, expected):
    rmi = evaluate_votes("rmi_votes", single(mom1=1), bars(closes), {})
    rsi = evaluate_votes("rsi_votes", single(), bars(closes), {})
    assert rmi[-1]["rows"][0]["value"] == expected
    assert rmi[-1]["rows"][0]["value"] == rsi[-1]["rows"][0]["value"]


def test_rsi_snapshot_restarts_from_same_closed_anchor_and_exact_close_not_twice():
    native = bars([10, 12, 11, 9], start=-9, span=3)
    primary = bars([13, 10, 9])
    result = evaluate_votes("rsi_votes", {"len1": 2, "len3": 2}, primary, {"3D": native})
    values = [r["rows"][2]["value"] for r in result]
    assert values == pytest.approx([100 * 1.5 / 1.75, 40, 100 * 0.5 / 1.75])
    changed_future = native[:-1] + (replace(native[-1], close=100000),)
    altered = evaluate_votes("rsi_votes", {"len1": 2, "len3": 2}, primary, {"3D": changed_future})
    assert [r["rows"][2]["value"] for r in altered[:2]] == values[:2]


def test_rmi_snapshot_uses_momentum_of_native_bars_not_primary_bars():
    native = bars([10, 20, 12, 18, 14], start=-12, span=3)
    result = evaluate_votes(
        "rmi_votes",
        {"len1": 2, "mom1": 2, "len3": 2, "mom3": 2},
        bars([16, 8, 14]),
        {"3D": native},
    )
    assert [r["rows"][2]["value"] for r in result] == pytest.approx(
        [100 * 2.5 / 3, 100 * 0.5 / 3, 75]
    )


def test_smi_first_sample_ema_seed_and_hand_calculated_double_smoothing():
    primary = (
        Bar(0, 1, 8, 10, 0, 8, True),
        Bar(1, 2, 9, 12, 2, 9, True),
    )
    result = evaluate_votes("smi_votes", single(len1=2, smoothA1=2, smoothB1=2), primary, {})
    assert result[0]["rows"][0]["value"] == 60
    # Numerator remains 3. Width EMA1=34/3, EMA2=98/9.
    assert result[1]["rows"][0]["value"] == pytest.approx(5400 / 98)


def test_smi_snapshot_uses_running_high_low_and_native_tail_without_future_highs():
    native = (
        Bar(-6, -3, 8, 10, 0, 8, True),
        Bar(-3, 0, 9, 12, 2, 9, True),
        Bar(0, 3, 10, 14, 6, 7, True),
    )
    primary = (
        Bar(0, 1, 10, 11, 7, 10, True),
        Bar(1, 2, 9, 14, 8, 9, True),
        Bar(2, 3, 7, 9, 6, 7, True),
    )
    settings = {"len1": 1, "smoothA1": 1, "smoothB1": 1, "len3": 2, "smoothA3": 1, "smoothB3": 1}
    result = evaluate_votes("smi_votes", settings, primary, {"3D": native})
    assert [r["rows"][2]["value"] for r in result] == pytest.approx([60, 100 / 6, -100 / 6])
    altered_native = native[:-1] + (replace(native[-1], high=9999, low=-9999, close=123),)
    altered = evaluate_votes("smi_votes", settings, primary, {"3D": altered_native})
    assert [r["rows"][2]["value"] for r in altered[:2]] == [
        r["rows"][2]["value"] for r in result[:2]
    ]


def test_smi_partial_and_crossing_buckets_stay_unknown_until_exact_native_close():
    native = bars([5, 6, 7, 8], start=-6, span=3, high=10, low=0)
    primary = (
        Bar(1, 2, 7, 10, 0, 7, True),
        Bar(2, 4, 8, 10, 0, 8, True),
        Bar(4, 5, 8, 10, 0, 8, True),
        Bar(5, 6, 8, 10, 0, 8, True),
    )
    settings = {"len1": 1, "smoothA1": 1, "smoothB1": 1, "len3": 1, "smoothA3": 1, "smoothB3": 1}
    result = evaluate_votes("smi_votes", settings, primary, {"3D": native})
    assert [r["rows"][2]["reason"] for r in result[:3]] == ["timeframe_boundary"] * 3
    assert result[-1]["rows"][2]["value"] == 60


def test_smi_zero_width_does_not_generate_a_buy_vote():
    result = evaluate_votes("smi_votes", smi_single(), bars([5, 5], high=5, low=5), {})
    assert result[-1]["rows"][0]["value"] is None
    assert result[-1]["outputs"]["buy_votes"] == 0


def test_only_first_is_independent_per_direction_and_rearms_after_condition_breaks():
    result = evaluate_votes(
        "smi_votes", smi_single(onlyFirst=True), bars([2, 2, 5, 8, 8, 2], high=10, low=0), {}
    )
    assert [r["outputs"]["buy_signal"] for r in result] == [1, 0, 0, 0, 0, 1]
    assert [r["outputs"]["sell_signal"] for r in result] == [0, 0, 0, 1, 0, 0]


def test_default_repeat_and_unconfirmed_bar_never_emits():
    primary = bars([2, 2, 2], high=10, low=0)
    primary = primary[:-1] + (replace(primary[-1], confirmed=False),)
    result = evaluate_votes("smi_votes", smi_single(), primary, {})
    assert [r["outputs"]["buy_signal"] for r in result] == [1, 1, 0]
    assert result[-1]["outputs"]["buy_zone"] == 1


def test_duplicate_timeframes_are_separate_votes_and_missing_rows_do_not_lower_n():
    settings = {
        "tf3": "1D",
        "len1": 2,
        "len3": 2,
        "en2": True,
        "tf2": "2D",
        "len2": 2,
    }
    result = evaluate_votes("rsi_votes", settings, bars([3, 2, 1]), {})[-1]
    assert result["outputs"]["active_count"] == 3
    assert result["outputs"]["ready_count"] == 2
    assert result["outputs"]["buy_votes"] == 2
    assert result["outputs"]["buy_signal"] == 1
    unreachable = evaluate_votes(
        "rsi_votes", settings | {"requiredBuyVotes": 3}, bars([3, 2, 1]), {}
    )[-1]
    assert unreachable["outputs"]["buy_signal"] == 0


def test_both_directions_can_signal_from_different_rows():
    settings = smi_single(
        en3=True,
        tf3="1D",
        len3=1,
        smoothA3=1,
        smoothB3=1,
        dipThr1=0,
        topThr1=1,
        dipThr3=-1,
        topThr3=0,
    )
    result = evaluate_votes("smi_votes", settings, bars([5], high=10, low=0), {})[-1]
    assert result["outputs"]["buy_signal"] == result["outputs"]["sell_signal"] == 1


def test_unreachable_buy_target_does_not_block_sell_target():
    result = evaluate_votes("rsi_votes", single(requiredBuyVotes=2), bars([1, 2, 3]), {})[-1]
    assert result["outputs"]["buy_reachable"] == 0
    assert result["outputs"]["sell_signal"] == 1


@pytest.mark.parametrize(
    "settings", [{"en1": False}, {"dipThr1": 80, "topThr1": 80}, {"tf1": "10T"}]
)
def test_invalid_settings_fail_closed(settings):
    result = evaluate_votes("rsi_votes", single(**settings), bars([1, 2, 3]), {})[-1]
    assert not result["ready"]
    assert result["reason"] == "invalid_chart"


def test_equal_duration_different_calendars_require_first_active_timeframe():
    settings = single(tf1="7D", en3=True, tf3="1W", len3=2)
    primary = bars([1, 2, 3])
    invalid = evaluate_votes("rsi_votes", settings, primary, {}, chart_timeframe="1W")[-1]
    valid = evaluate_votes("rsi_votes", settings, primary, {}, chart_timeframe="7D")[-1]
    assert invalid["reason"] == "invalid_chart"
    assert valid["ready"]


def test_empty_timeframe_and_alias_resolve_to_chart():
    result = evaluate_votes("rsi_votes", single(tf1=""), bars([1, 2, 3]), {}, chart_timeframe="D")[
        -1
    ]
    assert result["ready"]
    assert result["rows"][0]["timeframe"] == "1D"


def test_missing_boundary_and_as_of_future_cannot_signal():
    primary = bars([1, 2, 3])
    result = evaluate_votes("rsi_votes", single(), primary, {}, as_of=2)[-1]
    assert result["reason"] == "future_bar"
    assert result["outputs"]["sell_signal"] is None
    unknown = primary[:-1] + (replace(primary[-1], end=None),)
    result = evaluate_votes("rsi_votes", single(), unknown, {})[-1]
    assert result["reason"] == "native_boundary_unknown"
    assert result["outputs"]["sell_signal"] is None


def test_unconfirmed_historical_bar_cannot_supply_a_seed():
    primary = bars([1, 2, 3])
    primary = (replace(primary[0], end=None, confirmed=False),) + primary[1:]
    result = evaluate_votes("rsi_votes", single(), primary, {})[-1]
    assert result["rows"][0]["value"] is None


def test_visual_settings_do_not_change_calculation_or_outputs():
    primary = bars([1, 2, 3, 2, 1])
    before = evaluate_votes("rsi_votes", single(showTable=True), primary, {})
    after = evaluate_votes("rsi_votes", single(showTable=False), primary, {})
    assert before == after


@pytest.mark.parametrize("indicator_id", ["rsi_votes", "rmi_votes"])
def test_historical_unknown_ends_seed_current_native_bucket_without_future_close(indicator_id):
    known = bars([10, 12, 11, 99999], start=-9, span=3)
    native = tuple(replace(bar, end=None, confirmed=index < 3) for index, bar in enumerate(known))
    settings = (
        {"len1": 2, "len3": 2, "mom1": 1, "mom3": 1}
        if indicator_id == "rmi_votes"
        else {"len1": 2, "len3": 2}
    )
    result = evaluate_votes(indicator_id, settings, bars([13, 10]), {"3D": native}, as_of=2)
    assert [r["rows"][2]["value"] for r in result] == pytest.approx([100 * 1.5 / 1.75, 40])
    unobserved = evaluate_votes(indicator_id, settings, bars([13, 10]), {"3D": native})
    assert unobserved[-1]["rows"][2]["value"] is None


def test_smi_current_unknown_end_uses_only_observed_complete_primary_range():
    native = (
        Bar(-6, None, 8, 10, 0, 8, True),
        Bar(-3, None, 9, 12, 2, 9, True),
        Bar(0, None, 10, 99999, -99999, 9999, False),
    )
    primary = (Bar(0, 1, 10, 11, 7, 10, True), Bar(1, 2, 9, 14, 8, 9, True))
    settings = {"len1": 1, "smoothA1": 1, "smoothB1": 1, "len3": 2, "smoothA3": 1, "smoothB3": 1}
    result = evaluate_votes("smi_votes", settings, primary, {"3D": native}, as_of=2)
    assert [r["rows"][2]["value"] for r in result] == pytest.approx([60, 100 / 6])
    partial = evaluate_votes("smi_votes", settings, primary[1:], {"3D": native}, as_of=2)
    assert partial[-1]["rows"][2]["reason"] == "timeframe_boundary"


def test_unconfirmed_future_primary_is_unknown_and_cannot_supply_votes():
    primary = bars([1, 2, 3]) + (Bar(100, 101, 1, 2, 0.5, 1, False),)
    result = evaluate_votes("rsi_votes", single(), primary, {}, as_of=3)[-1]
    assert result["reason"] == "future_bar"
    assert result["outputs"]["buy_signal"] is None


@pytest.mark.parametrize("indicator_id", ["htf_rsi_score", "rsi_snapshot"])
def test_score_current_unknown_end_and_historical_confirmed_seed(indicator_id):
    from application.services.custom_indicators.score import SPECS as SCORE_SPECS
    from application.services.custom_indicators.score import evaluate_score

    spec = next(spec for spec in SCORE_SPECS if spec["id"] == indicator_id)
    settings = {item["key"]: item["default"] for item in spec["inputs"]}
    for key in settings:
        if key.startswith("en"):
            settings[key] = False
    if indicator_id == "htf_rsi_score":
        settings.update(en_3d=True, rsiLength=2)
    else:
        settings.update(en1=True, tf1="3D", len1=2)
    native = tuple(
        replace(bar, end=None, confirmed=index < 3)
        for index, bar in enumerate(bars([10, 12, 11, 99999], start=-9, span=3))
    )
    primary = (Bar(0, 3, 13, 14, 12, 13, False),)
    value = evaluate_score(indicator_id, settings, primary, {"3D": native}, as_of=1)[-1]
    expected = 100 * 1.5 / 1.75 if indicator_id == "htf_rsi_score" else 100 * 1.25 / 1.5
    row = value["rows"][2] if indicator_id == "htf_rsi_score" else value["rows"][0]
    assert row["rsi"] == pytest.approx(expected)
    assert value["ready"]
