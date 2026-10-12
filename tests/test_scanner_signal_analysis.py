"""Preserved historical signal identity and exact-row tagging contracts."""

import pytest

from ai_analyst import save_analysis_to_db
from db_session import get_session
from infrastructure.persistence.signal_repository import save_signal, set_signal_special_tag
from models import Signal
from tests.test_api_market_analysis import _analysis_json


def test_archived_ai_analysis_remains_linked_to_only_its_exact_signal(authenticated_api_client):
    old_id = save_signal("SAME", "BIST", "COMBO", "AL", "3W-FRI")
    target_id = save_signal("SAME", "Kripto", "COMBO", "AL", "3W-FRI")
    other_id = save_signal("SAME", "Kripto", "HUNTER", "AL", "3W-FRI")
    unlinked_id = save_analysis_to_db("SAME", "BIST", "legacy unlinked", "AL", _analysis_json())
    linked_id = save_analysis_to_db(
        "SAME", "Kripto", "legacy linked", "AL", _analysis_json(), signal_id=target_id
    )
    assert unlinked_id is not None and linked_id is not None
    for signal_id in (old_id, target_id, other_id, 99999):
        response = authenticated_api_client.get(f"/signals/{signal_id}/analysis")
        assert response.status_code == 200
        if signal_id == target_id:
            analysis = response.json()
            assert analysis["id"] == linked_id
            assert analysis["signal_id"] == target_id
            assert analysis["market_type"] == "Kripto"
            assert "Momentum destekliyor" in analysis["analysis_text"]
        else:
            assert response.json() is None
    analyses = authenticated_api_client.get("/analyses").json()
    assert {row["id"] for row in analyses} == {unlinked_id, linked_id}


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
