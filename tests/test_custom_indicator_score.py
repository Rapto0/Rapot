"""Hand-computed native-bucket fixtures for the supplied Pine score scripts."""

import ast
import re
from pathlib import Path

import pytest

from application.services.custom_indicators.core import Bar
from application.services.custom_indicators.score import SPECS, evaluate_score

ROOT = Path(__file__).resolve().parents[1]


def bar(time, close, *, end=None, confirmed=True):
    return Bar(
        time=float(time),
        end=float(end) if end is not None else None,
        open=float(close),
        high=float(close),
        low=float(close),
        close=float(close),
        confirmed=confirmed,
    )


def native(closes=(10, 8, 9, 7, 6, 8), duration=30):
    return tuple(bar(i * duration, value, end=(i + 1) * duration) for i, value in enumerate(closes))


def weighted_inputs(**changes):
    values = {field["key"]: field["default"] for field in SPECS[0]["inputs"]}
    for field in values:
        if field.startswith("en_"):
            values[field] = False
    values.update(en_1d=True, rsiLength=2)
    values.update(changes)
    return values


def snapshot_inputs(**changes):
    values = {field["key"]: field["default"] for field in SPECS[1]["inputs"]}
    for index in range(1, 11):
        values[f"en{index}"] = False
    values.update(en1=True, len1=2, tfPts1=4.0, serialPts1=1.5, dipTargetScore=5.0)
    values.update(changes)
    return values


def calculate(kind, inputs, primary, frames, **kwargs):
    return evaluate_score(kind, inputs, tuple(primary), frames, **kwargs)


def _pine_inputs(source):
    """Parse only literal input declarations; no Pine code is executed."""
    constants = dict(re.findall(r'(?m)^\s*(?:const\s+string\s+)?(\w+)\s*=\s*"([^"\n]*)"', source))
    declarations = []
    for match in re.finditer(
        r"(?m)^\s*(?:(?:int|float|bool|string)\s+)?(\w+)\s*=\s*input\.(\w+)\(", source
    ):
        quoted = escaped = False
        depth = 1
        stop = match.end()
        while depth:
            char = source[stop]
            if char == '"' and not escaped:
                quoted = not quoted
            if not quoted:
                depth += (char == "(") - (char == ")")
            escaped = char == "\\" and not escaped
            stop += 1
        body = source[match.end() : stop - 1]
        args = re.split(r",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", body)

        def literal(value):
            value = value.strip()
            if value in {"true", "false"}:
                return value == "true"
            return ast.literal_eval(value)

        entry = {
            "key": match[1],
            "type": match[2],
            "default": literal(args[0]),
            "label": literal(args[1]),
        }
        for arg in args[2:]:
            key, value = (part.strip() for part in arg.split("=", 1))
            if key in {"minval", "maxval", "step"}:
                entry[{"minval": "min", "maxval": "max"}.get(key, key)] = literal(value)
            if key == "group":
                entry["group"] = constants[value]
        declarations.append(entry)
    return declarations


@pytest.mark.parametrize("spec,count", [(SPECS[0], 24), (SPECS[1], 73)])
def test_every_input_matches_original_pine_metadata(spec, count):
    source = (ROOT / "indicators" / "pine" / f"{spec['id']}.pine").read_text(encoding="utf-8")
    parsed = _pine_inputs(source)
    assert len(parsed) == len(spec["inputs"]) == count
    assert parsed == [
        {key: value for key, value in field.items() if key != "visual"} for field in spec["inputs"]
    ]
    assert [item["key"] for item in spec["inputs"] if item.get("visual")] == (
        ["showTable"] if spec["id"] == "htf_rsi_score" else []
    )


def test_snapshot_seventh_timeframe_really_is_seven_days():
    fields = {field["key"]: field for field in SPECS[1]["inputs"]}
    assert fields["tf7"]["default"] == "7D"
    assert "max" not in fields["len1"]
    assert "max" not in fields["serialPts1"]


def test_weighted_historical_waits_until_native_htf_close():
    result = calculate(
        "htf_rsi_score",
        weighted_inputs(),
        [bar(120, 6, end=130), bar(140, 6, end=150)],
        {"1D": native()},
    )
    # At t130 the native t90..120 bar is the latest confirmed close: RSI=100/7.
    assert result[0]["outputs"]["score"] == pytest.approx(100 / 7)
    # At t150 the t120..150 native bar becomes visible: gain=.125, loss=1.25.
    assert result[1]["outputs"]["score"] == pytest.approx(100 / 11)
    assert [item["outputs"]["buy_signal"] for item in result] == [1.0, 0.0]


def test_weighted_realtime_uses_current_price_not_future_native_close():
    primary = [bar(130, 8, end=140, confirmed=False)]
    result = calculate("htf_rsi_score", weighted_inputs(), primary, {"1D": native()})
    changed = calculate(
        "htf_rsi_score", weighted_inputs(), primary, {"1D": native((10, 8, 9, 7, 900000, 1))}
    )
    # Prior RSI RMA is gain=.25/loss=1.5, current +1 makes .625/.75.
    assert result[0]["outputs"]["score"] == pytest.approx(500 / 11)
    assert result == changed


def test_weighted_realtime_lower_timeframe_uses_observation_not_primary_open():
    primary = [bar(90, 8, end=180, confirmed=False)]
    frame = {"1D": native((10, 8, 9, 7, 900000, 1))}
    result = calculate("htf_rsi_score", weighted_inputs(), primary, frame, as_of=130)[0]
    assert result["outputs"]["score"] == pytest.approx(500 / 11)
    without_observation = calculate("htf_rsi_score", weighted_inputs(), primary, frame)[0]
    assert without_observation["ready"] is False


@pytest.mark.parametrize("kind", ["htf_rsi_score", "rsi_snapshot"])
@pytest.mark.parametrize(
    "primary,as_of",
    [
        (bar(120, 6, end=130), 125),
        (bar(120, 6, end=130, confirmed=False), 119),
        (bar(120, 6, end=130, confirmed=False), 135),
    ],
)
def test_future_or_stale_primary_confirmation_is_not_consumed(kind, primary, as_of):
    settings = weighted_inputs() if kind == "htf_rsi_score" else snapshot_inputs()
    result = calculate(kind, settings, [primary], {"1D": native()}, as_of=as_of)[0]
    assert result["ready"] is False
    assert result["outputs"]["buy_signal"] is None
    assert result["outputs"]["sell_signal"] is None


def test_weighted_partial_history_renormalizes_and_reports_counts():
    inputs = weighted_inputs(en_2d=True, en_3d=True, w_1d=1.0, w_2d=3.0, w_3d=100.0)
    primary = [bar(90, 10, end=100)]
    result = calculate(
        "htf_rsi_score", inputs, primary, {"1D": native((10, 8, 9)), "2D": native((10, 12, 11))}
    )[0]
    # Two valid series RSI 100/3 and 200/3, absent 3D excluded from divisor.
    assert result["outputs"]["score"] == pytest.approx(175 / 3)
    assert result["outputs"]["active_count"] == 3
    assert result["outputs"]["ready_count"] == 2
    assert result["ready"] is True


@pytest.mark.parametrize("changes", [{"w_1d": 0.0}, {"en_1d": False}])
def test_weighted_zero_effective_weight_is_unknown(changes):
    result = calculate(
        "htf_rsi_score", weighted_inputs(**changes), [bar(90, 10, end=100)], {"1D": native()}
    )[0]
    assert result["outputs"]["score"] is None
    assert result["ready"] is False
    assert result["outputs"]["buy_signal"] == result["outputs"]["sell_signal"] == 0


def test_inclusive_zones_can_overlap_and_visual_setting_has_no_effect():
    inputs = weighted_inputs(dipThresh=100.0, tepeThresh=0.0)
    frame = {"1D": native()}
    primary = [bar(90, 10, end=100)]
    result = calculate("htf_rsi_score", inputs, primary, frame)
    assert result[0]["outputs"]["buy_zone"] == result[0]["outputs"]["sell_zone"] == 1
    assert result == calculate("htf_rsi_score", {**inputs, "showTable": False}, primary, frame)


def test_weighted_equal_threshold_and_exit_reentry():
    primary = [bar(80, 9, end=90), bar(110, 7, end=120), bar(170, 8, end=180)]
    result = calculate("htf_rsi_score", weighted_inputs(dipThresh=40.0), primary, {"1D": native()})
    assert [value["outputs"]["buy_signal"] for value in result] == [1, 0, 0]
    assert result[-1]["outputs"]["buy_zone"] == 0
    exact = result[0]["outputs"]["score"]
    at_equality = calculate(
        "htf_rsi_score",
        weighted_inputs(dipThresh=exact, tepeThresh=exact),
        primary[:1],
        {"1D": native()},
    )[0]
    assert at_equality["outputs"]["buy_zone"] == at_equality["outputs"]["sell_zone"] == 1


def test_snapshot_manual_seed_and_confirmed_streak_are_distinct():
    result = calculate("rsi_snapshot", snapshot_inputs(), [bar(120, 6, end=130)], {"1D": native()})[
        0
    ]
    # Manual RMA includes initial zero: previous gain=.25/loss=1.25.
    # The current -1 produces .125/1.125 => RSI10, unlike standard RSI=100/11.
    assert result["rows"][0]["rsi"] == pytest.approx(10.0)
    assert result["rows"][0]["dip_streak"] == 2
    assert result["outputs"]["dip_score"] == 5.5
    assert result["outputs"]["buy_signal"] == 1


def test_snapshot_same_htf_streak_does_not_increment_each_day():
    primary = [bar(120, 6, end=130), bar(130, 6.5, end=140), bar(140, 7, end=150)]
    result = calculate("rsi_snapshot", snapshot_inputs(), primary, {"1D": native()})
    assert [value["rows"][0]["dip_streak"] for value in result] == [2, 2, 2]
    assert [value["outputs"]["dip_score"] for value in result] == [5.5, 5.5, 5.5]
    # Every qualifying confirmed daily bar signals, not only the first crossing.
    assert [value["outputs"]["buy_signal"] for value in result] == [1, 1, 1]


def test_snapshot_duplicate_timeframes_keep_independent_row_points():
    settings = snapshot_inputs(en2=True, tf2="1D", len2=2, tfPts2=3.0, serialPts2=0.5)
    result = calculate("rsi_snapshot", settings, [bar(120, 6, end=130)], {"1D": native()})[0]
    assert [row["dip_score"] for row in result["rows"][:2]] == [5.5, 3.5]
    assert result["outputs"]["dip_score"] == 9
    assert result["outputs"]["active_count"] == result["outputs"]["ready_count"] == 2


def test_snapshot_historical_values_ignore_future_htf_final_close():
    primary = [bar(120, 6, end=130), bar(130, 6.5, end=140)]
    first = calculate("rsi_snapshot", snapshot_inputs(), primary, {"1D": native()})
    revised_future = calculate(
        "rsi_snapshot", snapshot_inputs(), primary, {"1D": native((10, 8, 9, 7, 100000, 3))}
    )
    assert first == revised_future


def test_snapshot_is_strict_at_threshold_and_requires_primary_confirmation():
    primary = [bar(120, 6, end=130)]
    base = calculate("rsi_snapshot", snapshot_inputs(), primary, {"1D": native()})[0]
    exact = base["rows"][0]["rsi"]
    equal = calculate(
        "rsi_snapshot", snapshot_inputs(dipThr1=exact, topThr1=exact), primary, {"1D": native()}
    )[0]
    assert equal["rows"][0]["dip_streak"] == equal["rows"][0]["top_streak"] == 0
    developing = calculate(
        "rsi_snapshot", snapshot_inputs(), [bar(120, 6, end=130, confirmed=False)], {"1D": native()}
    )[0]
    assert developing["outputs"]["dip_score"] == 5.5
    assert developing["outputs"]["buy_signal"] == 0


@pytest.mark.parametrize(
    "changes,points",
    [
        ({"maxStreak": 1}, 4.0),
        ({"tfPts1": 0.0}, 1.5),
        ({"serialPts1": 0.0}, 4.0),
        ({"maxStreak": 0}, 5.5),
    ],
)
def test_snapshot_streak_cap_and_fractional_independent_points(changes, points):
    result = calculate(
        "rsi_snapshot", snapshot_inputs(**changes), [bar(120, 6, end=130)], {"1D": native()}
    )[0]
    assert result["outputs"]["dip_score"] == points


@pytest.mark.parametrize("closes", [(10, 11, 12, 13, 14), (10, 10, 10, 10, 10)])
def test_snapshot_raw_division_with_zero_loss_stays_unavailable(closes):
    result = calculate(
        "rsi_snapshot", snapshot_inputs(), [bar(120, 14, end=130)], {"1D": native(closes)}
    )[0]
    assert result["rows"][0]["rsi"] is None
    assert result["outputs"]["dip_score"] == result["outputs"]["top_score"] == 0
    assert result["ready"] is False


def test_snapshot_rejects_non_daily_chart():
    with pytest.raises(ValueError, match="1D"):
        calculate("rsi_snapshot", {}, [], {}, chart_timeframe="60")


@pytest.mark.parametrize(
    "kind,settings", [("htf_rsi_score", weighted_inputs()), ("rsi_snapshot", snapshot_inputs())]
)
def test_unwitnessed_current_bucket_end_is_not_guessed(kind, settings):
    no_ends = tuple(
        bar(value.time, value.close, confirmed=index < len(native()) - 1)
        for index, value in enumerate(native())
    )
    # No following native bucket or observation time proves the final bucket's
    # membership. Earlier confirmed buckets may still be valid seed history.
    result = calculate(kind, settings, [bar(150, 6, end=160)], {"1D": no_ends})[0]
    assert result["ready"] is False


def test_snapshot_never_silently_uses_a_lower_timeframe_state():
    result = calculate(
        "rsi_snapshot",
        snapshot_inputs(tf1="60"),
        [bar(120, 6, end=150)],
        {"60": native(duration=10)},
    )[0]
    assert result["ready"] is False


def test_unknown_id_rejected():
    with pytest.raises(ValueError, match="Bilinmeyen"):
        calculate("made_up", {}, [], {})
