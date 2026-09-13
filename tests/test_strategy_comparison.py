"""Characterize the actual Python/TypeScript calculators on one literal input set.

These tests deliberately do not assert engine equivalence or reproduce indicator
formulas. 1D/ME select scoring policies over the same daily observations; they do
not resample candles. Root conftest supplies the normal offline pytest isolation.
"""

import hashlib
import importlib.metadata
import json
import math
import os
import platform
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import FrameType
from typing import Any

import numpy as np
import pandas as pd
import pytest

import signals

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/strategy_ohlcv.json"
PREFIXES = [0, 1, 2, 7, 8, 12, 13, 14, 15, 19, 20, 21, 25, 26, 27, 28, 29, 30, 40, 80]
CASES = {
    "flat_zero_range",
    "flat_range",
    "rising",
    "falling",
    "alternating",
    "reversal",
    "gap_spike",
}
CALCULATORS = {"combo": signals.calculate_combo_signal, "hunter": signals.calculate_hunter_signal}
COMPONENTS = {
    "combo": ("macd", "rsi", "wr", "cci"),
    "hunter": (
        "rsi",
        "rsi_fast",
        "cmo",
        "bop",
        "macd",
        "wr",
        "cci",
        "ult",
        "bbp",
        "roc",
        "dem",
        "psy",
        "z",
        "kpb",
        "rsi2",
    ),
}
SERIES_LOCALS = {"macd": "macd_line", "z": "zscore"}
TOLERANCE = {"relative": 1e-9, "absolute": 1e-8}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def metric(value: Any = None) -> dict[str, Any]:
    if value is None:
        return {"state": "not_computed", "value": None}
    number = float(value)
    state = (
        "finite"
        if math.isfinite(number)
        else "nan"
        if math.isnan(number)
        else "positive_infinity"
        if number > 0
        else "negative_infinity"
    )
    return {"state": state, "value": number if state == "finite" else None}


def capture(
    function: Callable[[pd.DataFrame, str], dict[str, Any] | None],
    frame: pd.DataFrame,
    policy: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Observe only this exact function's return locals; always restore profiling."""
    observed = {}
    previous = sys.getprofile()

    def on_return(call_frame: FrameType, event: str, _argument: Any) -> None:
        if event == "return" and call_frame.f_code is function.__code__:
            observed.update(call_frame.f_locals)

    try:
        sys.setprofile(on_return)
        public = function(frame, policy)
    finally:
        sys.setprofile(previous)
    return public, observed


def frame_from(candles: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(candles).rename(columns=str.title)
    frame.index = pd.to_datetime(frame.pop("Time"), utc=True)
    return frame


def normalize(
    public: dict[str, Any] | None, observed: dict[str, Any], strategy: str
) -> dict[str, Any]:
    components = {name: metric(observed.get("v_" + name)) for name in COMPONENTS[strategy]}
    computed = any(value["state"] != "not_computed" for value in components.values())
    scores = None
    if computed:
        score_names = ("buy_score", "sell_score") if strategy == "combo" else ("dip_c", "top_c")
        scores = dict(zip(("buy", "sell"), (int(observed[name]) for name in score_names)))
    return {
        "public_available": public is not None,
        "public_unavailable_reason": None
        if public is not None
        else "no_active_components"
        if computed
        else "minimum_history",
        "decisions": {key: bool(public[key]) for key in ("buy", "sell")} if public else None,
        "scores": scores,
        "active_count": observed.get("active_count"),
        "public_details": {
            key: value.item() if isinstance(value, np.generic) else value
            for key, value in public["details"].items()
        }
        if public
        else None,
        "components": components,
    }


def same_metric(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return left["state"] == right["state"] and (
        left["state"] != "finite"
        or math.isclose(
            left["value"],
            right["value"],
            rel_tol=TOLERANCE["relative"],
            abs_tol=TOLERANCE["absolute"],
        )
    )


def summarize(python_rows: list[dict[str, Any]], ts_rows: list[dict[str, Any]]) -> dict[str, Any]:
    python_index = {
        (row["case"], row["prefix"], row["policy"], row["strategy"]): row for row in python_rows
    }
    groups = {}
    for ts_row in ts_rows:
        profile, strategy = ts_row["profile"], ts_row["strategy"]
        python_policy = "1D" if profile == "native" else profile
        py = python_index[(ts_row["case"], ts_row["prefix"], python_policy, strategy)]
        key = profile + "/" + strategy
        if key not in groups:
            groups[key] = {
                "python_policy": python_policy,
                "rows": 0,
                "both_public_available": 0,
                "public_availability_differences": 0,
                "score_differences": 0,
                "decision_differences": 0,
                "components": {},
                "examples": [],
            }
        group = groups[key]
        group["rows"] += 1
        both = py["public_available"] and ts_row["public_available"]
        group["both_public_available"] += int(both)
        group["public_availability_differences"] += int(
            py["public_available"] != ts_row["public_available"]
        )
        if both:
            group["score_differences"] += int(py["scores"] != ts_row["scores"])
            group["decision_differences"] += int(py["decisions"] != ts_row["decisions"])
        changed = []
        for component in COMPONENTS[strategy]:
            left, right = py["components"][component], ts_row["components"][component]
            counts = group["components"].setdefault(
                component,
                {
                    "both_computed": 0,
                    "both_finite": 0,
                    "computation_gate_differences": 0,
                    "availability_differences": 0,
                    "finite_value_differences": 0,
                    "max_absolute_difference": None,
                },
            )
            computed = left["state"] != "not_computed" and right["state"] != "not_computed"
            counts["both_computed"] += int(computed)
            counts["computation_gate_differences"] += int(
                (left["state"] == "not_computed") != (right["state"] == "not_computed")
            )
            if computed:
                counts["availability_differences"] += int(left["state"] != right["state"])
                if left["state"] == right["state"] == "finite":
                    counts["both_finite"] += 1
                    delta = abs(left["value"] - right["value"])
                    counts["max_absolute_difference"] = max(
                        counts["max_absolute_difference"] or 0, delta
                    )
                    counts["finite_value_differences"] += int(not same_metric(left, right))
                if not same_metric(left, right):
                    changed.append(component)
        if (
            both
            and (
                changed
                or py["scores"] != ts_row["scores"]
                or py["decisions"] != ts_row["decisions"]
            )
            and len(group["examples"]) < 8
        ):
            group["examples"].append(
                {
                    "case": ts_row["case"],
                    "prefix": ts_row["prefix"],
                    "components": changed,
                    "python_scores": py["scores"],
                    "typescript_scores": ts_row["scores"],
                    "python_decisions": py["decisions"],
                    "typescript_decisions": ts_row["decisions"],
                }
            )
    return groups


@pytest.fixture(scope="module")
def comparison() -> dict[str, Any]:
    fixture = json.loads(FIXTURE.read_bytes())
    assert fixture["prefixes"] == PREFIXES
    node = os.environ.get("NODE_BINARY") or shutil.which("node")
    assert node, "Node20 is required: select the project runtime or set NODE_BINARY"
    # No NODE_OPTIONS/preload, provider credentials or application environment reach Node.
    child_env = {
        key: os.environ[key] for key in ("PATH", "SystemRoot", "WINDIR") if key in os.environ
    }
    process = subprocess.run(
        [node, str(ROOT / "frontend/tests/strategy-export.mjs")],
        cwd=ROOT / "frontend",
        env=child_env,
        capture_output=True,
        timeout=20,
    )
    assert process.returncode == 0, process.stderr.decode("utf-8", errors="replace")[:3000]
    assert len(process.stdout) < 4 * 1024**2, "Bounded TS characterization output exceeded"
    ts = json.loads(process.stdout)
    assert ts["node"].split(".")[0] == "20"
    assert ts["source_sha256"] == sha256(ROOT / "frontend/src/lib/indicators.ts")
    assert ts["fixture_sha256"] == sha256(FIXTURE)
    rows, seed_observations = [], {}
    causal_comparisons = 0
    for case in fixture["cases"]:
        frame = frame_from(case["candles"])
        original = frame.copy(deep=True)
        for policy in ("1D", "ME"):
            for strategy, function in CALCULATORS.items():
                _, complete = capture(function, frame, policy)
                if strategy == "hunter" and policy == "1D":
                    seed_observations[case["id"]] = {
                        index: metric(complete["ke_base"].iloc[index])
                        for index in (0, 1, 12, 19, 20, 25, 79)
                    }
                for prefix in PREFIXES:
                    public, observed = capture(function, frame.iloc[:prefix].copy(), policy)
                    row = {
                        "case": case["id"],
                        "prefix": prefix,
                        "policy": policy,
                        "strategy": strategy,
                        **normalize(public, observed, strategy),
                    }
                    for component, value in row["components"].items():
                        if value["state"] != "not_computed":
                            series = complete[SERIES_LOCALS.get(component, component)]
                            assert same_metric(value, metric(series.iloc[prefix - 1])), (
                                case["id"],
                                policy,
                                strategy,
                                prefix,
                                component,
                            )
                            causal_comparisons += 1
                    rows.append(row)
        pd.testing.assert_frame_equal(frame, original)
    return {
        "schema": "rapot-strategy-comparison-v1",
        "status": "characterized_not_equivalence_asserted",
        "hash_normalization": "UTF-8 text with CRLF normalized to LF before SHA256",
        "fixture": {
            "sha256": sha256(FIXTURE),
            "cases": len(fixture["cases"]),
            "candles_per_case": 80,
            "prefixes": PREFIXES,
        },
        "sources_sha256": {
            name: sha256(ROOT / name)
            for name in (
                "signals.py",
                "config.py",
                "frontend/src/lib/indicators.ts",
                "frontend/tests/strategy-export.mjs",
                "tests/test_strategy_comparison.py",
            )
        },
        "versions": {
            "python": platform.python_version(),
            "node": ts["node"],
            "typescript": ts["typescript"],
            **{name: importlib.metadata.version(name) for name in ("numpy", "pandas", "ta")},
        },
        "backend_adapter": "ta compatibility accessor"
        if hasattr(signals, "TAAccessor")
        else "pandas_ta",
        "frontend_package_lock_sha256": ts["package_lock_sha256"],
        "profiles": ts["profiles"],
        "numeric_tolerance": TOLERANCE,
        "public_minimum_history": {
            "python": {"1D": 30, "ME": 8},
            "typescript": {"combo": 26, "hunter": 30},
        },
        "prefix_causality": {
            "python_component_comparisons": causal_comparisons,
            "typescript_public_row_comparisons": ts["prefix_causality_comparisons"],
        },
        "ema20_seed_observations": {
            "python": seed_observations,
            "typescript": ts["ema20_seed_observations"],
        },
        "summary": summarize(rows, ts["rows"]),
        "python_rows": rows,
        "typescript_rows": ts["rows"],
        "limitations": [
            "1D/ME are backend scoring-policy labels applied to identical closed daily candles, not monthly resampling or HTF equivalence.",
            "Matched TS profiles change minimum scores and BOP thresholds only in this probe; production defaults are untouched. Strict TS comparisons versus inclusive Python comparisons remain distinct.",
            "Python raw values are observed from the exact public function return frame before rounded/public fallback representation; below its history gate they were not computed.",
            "TS exposes one final AL/SAT/null signal; Python exposes independent buy/sell booleans. Decision comparisons retain that public contract distinction.",
            "The seven synthetic cases are characterization examples, not market backtests or complete equivalence proof. No Pine runtime, TradingView delivery, broker or order was exercised.",
        ],
    }


def row(
    report: dict[str, Any], engine: str, case: str, prefix: int, strategy: str, profile: str = "1D"
) -> dict[str, Any]:
    field = "policy" if engine == "python" else "profile"
    return next(
        value
        for value in report[engine + "_rows"]
        if value["case"] == case
        and value["prefix"] == prefix
        and value["strategy"] == strategy
        and value[field] == profile
    )


def test_literal_fixture_has_seven_closed_utc_daily_sequences() -> None:
    fixture = json.loads(FIXTURE.read_bytes())
    assert {case["id"] for case in fixture["cases"]} == CASES
    for case in fixture["cases"]:
        assert len(case["candles"]) == 80
        dates = pd.to_datetime([candle["time"] for candle in case["candles"]], utc=True)
        assert dates[0] == pd.Timestamp("2025-01-01T00:00:00Z")
        assert dates[-1] == pd.Timestamp("2025-03-21T00:00:00Z")
        assert all((dates[1:] - dates[:-1]) == pd.Timedelta(days=1))
        for candle in case["candles"]:
            assert set(candle) == {"time", "open", "high", "low", "close", "volume"}
            assert all(
                math.isfinite(candle[key]) for key in ("open", "high", "low", "close", "volume")
            )
            assert candle["low"] <= min(candle["open"], candle["close"])
            assert candle["high"] >= max(candle["open"], candle["close"])
            assert candle["volume"] >= 0


def test_scoped_return_probe_restores_previous_profiler_even_on_exception() -> None:
    previous = sys.getprofile()

    def marker(*_args: Any) -> None:
        return None

    def broken(_frame: pd.DataFrame, _policy: str) -> dict[str, Any] | None:
        raise RuntimeError("synthetic failure")

    try:
        sys.setprofile(marker)
        with pytest.raises(RuntimeError, match="synthetic failure"):
            capture(broken, pd.DataFrame(), "1D")
        assert sys.getprofile() is marker
    finally:
        sys.setprofile(previous)


def test_history_gates_are_distinct_from_nan_components(comparison: dict[str, Any]) -> None:
    assert not row(comparison, "python", "rising", 29, "combo")["public_available"]
    assert row(comparison, "typescript", "rising", 26, "combo")["public_available"]
    for engine in ("python", "typescript"):
        assert not row(comparison, engine, "rising", 29, "hunter")["public_available"]
        assert row(comparison, engine, "rising", 30, "hunter")["public_available"]
    assert (
        row(comparison, "python", "rising", 8, "combo", "ME")["public_unavailable_reason"]
        == "no_active_components"
    )
    assert (
        row(comparison, "python", "rising", 7, "combo", "ME")["components"]["rsi"]["state"]
        == "not_computed"
    )
    assert (
        row(comparison, "python", "rising", 8, "combo", "ME")["components"]["rsi"]["state"] == "nan"
    )


@pytest.mark.parametrize("case,rsi", [("rising", 100), ("falling", 0)])
def test_literal_directional_rsi_and_zero_are_preserved(
    comparison: dict[str, Any], case: str, rsi: int
) -> None:
    for engine in ("python", "typescript"):
        actual = row(comparison, engine, case, 80, "combo")
        assert actual["components"]["rsi"] == {"state": "finite", "value": rsi}
        assert (
            actual["components"]["macd"]["value"] > 0
            if case == "rising"
            else actual["components"]["macd"]["value"] < 0
        )


def test_flat_series_documents_real_fallback_and_raw_public_difference(
    comparison: dict[str, Any],
) -> None:
    py = row(comparison, "python", "flat_zero_range", 80, "combo")
    ts = row(comparison, "typescript", "flat_zero_range", 80, "combo")
    assert py["components"]["rsi"]["value"] == 100
    assert ts["components"]["rsi"]["value"] == 50
    assert py["components"]["cci"]["state"] == "nan"
    assert py["public_details"]["CCI"] == 0
    assert ts["components"]["cci"] == {"state": "finite", "value": 0}
    assert py["components"]["wr"]["state"] == "nan"
    assert ts["components"]["wr"]["value"] == -50
    assert row(comparison, "python", "flat_range", 80, "combo")["components"]["wr"]["value"] == -50


def test_actual_ema20_seed_boundaries_are_observed_without_formula_copy(
    comparison: dict[str, Any],
) -> None:
    ts = comparison["ema20_seed_observations"]["typescript"]["rising"]
    py = comparison["ema20_seed_observations"]["python"]["rising"]
    assert ts["0"]["value"] == 100
    assert ts["1"]["value"] == 100.5
    assert ts["19"]["value"] == 109.5
    assert ts["20"]["value"] == 110.5
    assert py[0]["state"] == py[12]["state"] == "nan"
    assert py[19]["state"] == "finite"
    assert py[19]["value"] != pytest.approx(ts["19"]["value"])


def test_report_covers_all_profiles_and_does_not_claim_equivalence(
    comparison: dict[str, Any],
) -> None:
    assert len(comparison["python_rows"]) == 7 * 20 * 2 * 2
    assert len(comparison["typescript_rows"]) == 7 * 20 * 3 * 2
    assert set(comparison["summary"]) == {
        f"{profile}/{strategy}" for profile in ("native", "1D", "ME") for strategy in CALCULATORS
    }
    assert comparison["prefix_causality"]["python_component_comparisons"] > 0
    assert comparison["prefix_causality"]["typescript_public_row_comparisons"] > 0
    for summary in comparison["summary"].values():
        assert summary["rows"] == 140
        assert len(summary["examples"]) <= 8
        assert summary["both_public_available"] > 0
    target = os.environ.get("RAPOT_STRATEGY_REPORT")
    if target:
        destination = Path(target)
        assert destination.is_absolute() and destination.suffix == ".json"
        assert not destination.is_symlink() and destination.resolve() != FIXTURE.resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(comparison, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
