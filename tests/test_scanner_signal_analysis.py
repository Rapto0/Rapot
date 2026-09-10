"""Saved-signal identity and optional AI enrichment, using only isolated test storage."""

from itertools import count

import pandas as pd
import pytest

import ai_analyst
import market_scanner
from application.scanner.scan_history import track_scan
from db_session import get_session
from infrastructure.persistence.signal_repository import save_signal, set_signal_special_tag
from models import AIAnalysis, Signal
from tests.test_api_market_analysis import _analysis_json


@pytest.fixture
def special_scan(monkeypatch):
    frame = pd.DataFrame({"Close": [10.0] * 30})
    monkeypatch.setattr(
        market_scanner, "TIMEFRAMES", [(tf, tf) for tf in ("1D", "W-FRI", "3W-FRI")]
    )
    monkeypatch.setattr(market_scanner, "resample_market_data", lambda df, *_args: df)
    signal = {
        "buy": True,
        "sell": False,
        "details": {"Score": "+4/-0", "DipScore": "7/7", "TopScore": "0/10", "PRICE": 10},
    }
    monkeypatch.setattr(market_scanner, "calculate_combo_signal", lambda *_args: signal)
    monkeypatch.setattr(market_scanner, "calculate_hunter_signal", lambda *_args: signal)
    monkeypatch.setattr(market_scanner, "_publish_realtime_signal", lambda _payload: True)
    monkeypatch.setattr(market_scanner, "increment_signal_count", lambda: None)
    monkeypatch.setattr(market_scanner, "get_bist_data_secondary", lambda *_args, **_kw: frame)
    monkeypatch.setattr(market_scanner, "_verify_bist_second_source", lambda **_kw: (True, "ok"))
    monkeypatch.setattr(market_scanner, "send_message", lambda _message: True)
    monkeypatch.setattr(market_scanner, "fetch_market_news", lambda *_args: "")
    monkeypatch.setattr(
        market_scanner,
        "inspect_strategy_dataframe",
        lambda **kw: {"strategy": kw["strategy"], "timeframes": []},
    )
    monkeypatch.setattr(
        market_scanner,
        "build_strategy_ai_payload",
        lambda **kw: {"strategy": kw["report"]["strategy"], "special_tag": kw["special_tag"]},
    )
    monkeypatch.setattr(market_scanner, "_derive_technical_levels", lambda *_args: {})
    monkeypatch.setattr(market_scanner, "format_ai_message_for_telegram", lambda *_a, **_kw: "AI")
    return frame, signal


@pytest.mark.parametrize("market_type", ["BIST", "Kripto"])
def test_each_special_tag_and_ai_use_the_saved_strategy_direction_timeframe_id(
    monkeypatch, special_scan, market_type
):
    frame, signal = special_scan
    signal["sell"] = True
    monkeypatch.setattr(
        market_scanner,
        "TIMEFRAMES",
        [(tf, tf) for tf in ("1D", "W-FRI", "2W-FRI", "3W-FRI", "ME")],
    )
    ids = count(101)
    saved = {}
    tagged = []
    analyzed = []

    def save(**kwargs):
        signal_id = next(ids)
        saved[(kwargs["strategy"], kwargs["signal_type"], kwargs["timeframe"])] = signal_id
        return signal_id

    monkeypatch.setattr(market_scanner, "db_save_signal", save)
    monkeypatch.setattr(
        market_scanner, "db_set_signal_special_tag", lambda **kw: tagged.append(kw) or True
    )
    monkeypatch.setattr(
        market_scanner, "analyze_with_gemini", lambda **kw: analyzed.append(kw) or "{}"
    )

    with track_scan(markets={market_type}, mode="sync") as progress:
        assert market_scanner.process_symbol(frame, "SAME", market_type) is None

    assert progress.signals_found == 20
    assert progress.errors_count == 0
    assert len(tagged) == len(analyzed) == 8
    for tag, analysis in zip(tagged, analyzed, strict=True):
        identity = (tag["strategy"], tag["signal_type"], tag["timeframe"])
        assert tag["signal_id"] == analysis["signal_id"] == saved[identity]
        assert tag["market_type"] == analysis["market_type"] == market_type
        assert analysis["technical_data"]["special_tag"] == tag["special_tag"]


@pytest.mark.parametrize("save_result", [0, None, "raise"])
def test_missing_target_insert_does_not_tag_old_rows_or_start_ai(
    monkeypatch, special_scan, save_result
):
    frame, _signal = special_scan
    old_ids = [
        save_signal("SAME", "Kripto", strategy, "AL", "3W-FRI") for strategy in ("COMBO", "HUNTER")
    ]
    counted = []
    analyzed = []

    def save(**kwargs):
        if kwargs["timeframe"] == "3W-FRI":
            if save_result == "raise":
                raise RuntimeError("injected persistence error")
            return save_result
        return save_signal(**kwargs)

    monkeypatch.setattr(market_scanner, "db_save_signal", save)
    monkeypatch.setattr(market_scanner, "increment_signal_count", lambda: counted.append(1))
    monkeypatch.setattr(market_scanner, "analyze_with_gemini", lambda **kw: analyzed.append(kw))

    with track_scan(markets={"Kripto"}, mode="sync") as progress:
        market_scanner.process_symbol(frame, "SAME", "Kripto")

    assert len(counted) == progress.signals_found == 4
    assert progress.errors_count == (1 if save_result == "raise" else 0)
    assert analyzed == []
    with get_session() as session:
        assert session.query(Signal).count() == 6
        assert all(session.get(Signal, signal_id).special_tag is None for signal_id in old_ids)
        assert session.query(AIAnalysis).count() == 0


@pytest.mark.parametrize("failure_stage", ["report", "news", "ai", "tag", "format", "send"])
def test_enrichment_failure_preserves_signals_and_allows_next_special(
    monkeypatch, special_scan, failure_stage
):
    frame, _signal = special_scan
    function_name = {
        "report": "inspect_strategy_dataframe",
        "news": "fetch_market_news",
        "ai": "analyze_with_gemini",
        "tag": "db_set_signal_special_tag",
        "format": "format_ai_message_for_telegram",
        "send": "send_message",
    }[failure_stage]
    analyzed = []
    monkeypatch.setattr(
        market_scanner, "analyze_with_gemini", lambda **kw: analyzed.append(kw) or "{}"
    )
    original = getattr(market_scanner, function_name)
    calls = []

    def fail_once(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("injected enrichment error")
        return original(*args, **kwargs)

    monkeypatch.setattr(market_scanner, function_name, fail_once)
    with track_scan(markets={"Kripto"}, mode="sync") as progress:
        market_scanner.process_symbol(frame, "SAME", "Kripto")

    assert len(calls) >= 2
    assert progress.signals_found == 6
    assert progress.errors_count == 0
    assert progress.status == "success"
    assert analyzed[-1]["technical_data"]["strategy"] == "HUNTER"
    with get_session() as session:
        assert session.query(Signal).count() == 6


@pytest.mark.parametrize("ai_state", ["disabled", "success", "invalid_json"])
def test_scanner_ai_persistence_is_visible_only_on_the_target_signal_api(
    monkeypatch, special_scan, authenticated_api_client, ai_state
):
    frame, _signal = special_scan
    # A historical row with the same symbol must never receive the new analysis/tag.
    old_id = save_signal("SAME", "BIST", "COMBO", "AL", "3W-FRI")
    legacy_id = ai_analyst.save_analysis_to_db(
        "SAME", "BIST", "legacy unlinked", "AL", _analysis_json()
    )
    assert legacy_id is not None
    monkeypatch.setattr(ai_analyst.settings, "ai_enabled", ai_state != "disabled")
    monkeypatch.setattr(ai_analyst.settings, "ai_provider", "gemini")
    monkeypatch.setattr(ai_analyst.settings, "ai_enable_fallback", False)
    monkeypatch.setattr(ai_analyst, "gemini_client", object())
    monkeypatch.setattr(ai_analyst, "_ensure_gemini_backend", lambda: ("test-key", "google.genai"))
    monkeypatch.setattr(
        ai_analyst,
        "_generate_model_response",
        lambda *_args: "not-json" if ai_state == "invalid_json" else _analysis_json(),
    )

    with track_scan(markets={"Kripto"}, mode="sync") as progress:
        market_scanner.process_symbol(frame, "SAME", "Kripto")

    assert progress.signals_found == 6
    assert progress.status == "success"
    with get_session() as session:
        signals = [row.to_dict() for row in session.query(Signal).all()]
        assert session.query(AIAnalysis).count() == (3 if ai_state == "success" else 1)
    assert len(signals) == 7
    for row in signals:
        response = authenticated_api_client.get(f"/signals/{row['id']}/analysis")
        assert response.status_code == 200
        is_target = row["id"] != old_id and row["timeframe"] == "3W-FRI"
        assert row["special_tag"] == ("COK_UCUZ" if is_target else None)
        if ai_state == "success" and is_target:
            analysis = response.json()
            assert analysis["id"] != legacy_id
            assert analysis["signal_id"] == row["id"]
            assert analysis["market_type"] == "Kripto"
            assert analysis["symbol"] == "SAME"
            assert "Momentum destekliyor" in analysis["analysis_text"]
        else:
            assert response.json() is None
    missing_response = authenticated_api_client.get("/signals/99999/analysis")
    assert missing_response.status_code == 200
    assert missing_response.json() is None


def test_special_tag_exact_id_does_not_select_a_newer_matching_row():
    target_id = save_signal("SAME", "Kripto", "COMBO", "AL", "3W-FRI")
    newer_id = save_signal("SAME", "Kripto", "COMBO", "AL", "3W-FRI")
    assert set_signal_special_tag(
        "SAME", "Kripto", "COMBO", "AL", "3W-FRI", "COK_UCUZ", signal_id=target_id
    )
    with get_session() as session:
        assert session.get(Signal, target_id).special_tag == "COK_UCUZ"
        assert session.get(Signal, newer_id).special_tag is None


@pytest.mark.parametrize(
    ("field", "mismatch"),
    [
        ("symbol", "OTHER"),
        ("market_type", "BIST"),
        ("strategy", "HUNTER"),
        ("signal_type", "SAT"),
        ("timeframe", "ME"),
        ("signal_id", 0),
        ("signal_id", -1),
        ("signal_id", 99999),
    ],
)
def test_special_tag_exact_id_requires_all_identity_fields(field, mismatch):
    target_id = save_signal("SAME", "Kripto", "COMBO", "AL", "3W-FRI")
    kwargs = {
        "symbol": "SAME",
        "market_type": "Kripto",
        "strategy": "COMBO",
        "signal_type": "AL",
        "timeframe": "3W-FRI",
        "signal_id": target_id,
    }
    kwargs[field] = mismatch
    assert not set_signal_special_tag(**kwargs, special_tag="COK_UCUZ")
    with get_session() as session:
        assert session.get(Signal, target_id).special_tag is None
