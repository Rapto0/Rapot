"""Configuration isolation and persistent alarm/API contracts for supplied indicators."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import advanced_alarm_routes as routes
from application.services.advanced_alarm_conditions import (
    field_key,
    prepare_condition,
    validate_condition,
)
from application.services.custom_indicators.catalog import (
    canonical_timeframe,
    catalog,
    config_key,
    requirements,
    validate_config,
)


def condition(indicator="rsi_votes", output="buy_signal", **inputs):
    return {
        "op": "eq",
        "left": {"field": "custom", "indicator": indicator, "output": output, "inputs": inputs},
        "right": 1,
    }


def test_all_five_sources_have_every_input_and_detached_catalog():
    result = catalog()
    assert {row["id"]: len(row["inputs"]) for row in result["indicators"]} == {
        "htf_rsi_score": 24,
        "rsi_snapshot": 73,
        "rsi_votes": 54,
        "smi_votes": 74,
        "rmi_votes": 64,
    }
    result["indicators"][0]["inputs"][0]["default"] = -1
    assert validate_config("htf_rsi_score", {})["rsiLength"] == 14


def test_frontend_fixture_tracks_the_actual_server_catalog():
    path = (
        Path(__file__).resolve().parents[1]
        / "frontend/tests/fixtures/custom-indicator-catalog.json"
    )
    assert json.loads(path.read_text(encoding="utf-8")) == catalog()


def test_canonical_plan_detaches_inputs_and_shares_visual_variants_only():
    left = condition(showTable=True)
    right = condition(showTable=False)
    plan = prepare_condition({"op": "or", "children": [left, right]}, "1d")
    assert len(plan.fields) == 1
    left["left"]["inputs"]["requiredBuyVotes"] = 9
    assert plan.fields[0]["inputs"]["requiredBuyVotes"] == 2
    with pytest.raises(TypeError):
        plan.fields[0]["inputs"]["requiredBuyVotes"] = 9
    assert config_key("rsi_votes", {"requiredBuyVotes": 3}) != config_key("rsi_votes", {})
    assert config_key("rsi_votes", {"dipThr1": 20}) == config_key("rsi_votes", {"dipThr1": 20.0})
    assert field_key(condition(output="buy_votes")["left"], "1d") != field_key(
        condition()["left"], "1d"
    )


@pytest.mark.parametrize("value", [True, "14", None, float("nan"), float("inf"), 10**400])
def test_non_numeric_and_unbounded_inputs_rejected(value):
    with pytest.raises(ValueError):
        validate_config("rsi_votes", {"len1": value})


def test_unknown_fields_and_output_cannot_enter_alarm_plan():
    for value in [condition(extra=True), condition(output="execute"), condition(output={})]:
        with pytest.raises(ValueError):
            validate_condition(value)


def test_minimum_exact_tf_and_snapshot_daily_contract():
    with pytest.raises(ValueError, match="en küçük"):
        prepare_condition(condition(), "5m")
    with pytest.raises(ValueError, match="günlük"):
        prepare_condition(condition("rsi_snapshot"), "1wk")
    with pytest.raises(ValueError, match="küçük"):
        prepare_condition(condition(dipThr1=90), "1d")
    # 7D has the same duration as 1W, but is not the same native candle grid.
    with pytest.raises(ValueError, match="en küçük"):
        prepare_condition(condition(tf1="7D", en3=False), "1wk")
    prepare_condition(condition(tf1="7D", en3=False), "7D")


def test_empty_row_tf_resolves_against_actual_alarm_base():
    plan = prepare_condition(condition(tf1="", en3=False), "5m")
    assert plan.fields[0]["inputs"]["tf1"] == "5"
    assert plan.fields[0]["timeframe"] == "5"


def test_native_requirements_share_duplicates_preserve_long_settings_and_bound_work():
    inputs = validate_config("rmi_votes", {"tf3": "1D", "mom1": 5000})
    needed = requirements("rmi_votes", inputs)
    assert needed == [{"timeframe": "1D", "bars": 5514}]
    assert requirements("smi_votes", {"len1": 5000})[0]["bars"] == 5501
    assert requirements("rmi_votes", {"len1": 5000, "mom1": 5000})[0]["bars"] == 10000
    with pytest.raises(ValueError, match="sağlayıcı sınırı"):
        requirements("rmi_votes", {"len1": 5001, "mom1": 5000})
    assert canonical_timeframe("1m") == "1"
    assert canonical_timeframe("1M") == "1M"
    for invalid in ["0D", "2Q", "1s", "500D", "10000", "7S"]:
        with pytest.raises(ValueError):
            canonical_timeframe(invalid)


def test_custom_base_does_not_enable_unsupported_standard_history():
    with pytest.raises(ValueError, match="Standart"):
        prepare_condition({"op": "gt", "left": {"field": "rsi"}, "right": 30}, "3D")


def test_smi_minute_primary_requests_complete_daily_developing_range():
    inputs = {"tf1": "1", "tf3": "1D"}
    needed = {row["timeframe"]: row["bars"] for row in requirements("smi_votes", inputs, "1")}
    assert needed["1"] > 24 * 60
    assert needed["1D"] >= 500


def test_smi_monthly_coverage_budget_remains_bounded():
    inputs = {"tf1": "1", "tf3": "1M"}
    needed = {row["timeframe"]: row["bars"] for row in requirements("smi_votes", inputs, "1")}
    assert needed["1"] == catalog()["max_history_bars"] == 10000
    assert all(bars <= 10000 for bars in needed.values())
    # A 31-day month needs 124 six-hour bars; this is a history budget,
    # never a replacement for the provider's real monthly start/end.
    wider_base = requirements("smi_votes", {"tf1": "360", "tf3": "1M"}, "360")
    assert next(row["bars"] for row in wider_base if row["timeframe"] == "360") >= 124 + 500


def test_smi_disabled_timeframes_do_not_increase_primary_history():
    inputs = {"tf1": "1", "tf3": "1D", "tf10": "12M", "en10": False}
    assert requirements("smi_votes", inputs, "1") == requirements(
        "smi_votes", {"tf1": "1", "tf3": "1D"}, "1"
    )


def test_alarm_write_normalizes_native_alias_and_requires_source_signal_close():
    payload = {
        "name": "Liste göstergesi",
        "category": "watchlist",
        "scope": "watchlist",
        "watchlist_id": "saved-list",
        "timeframe": "1D",
        "trigger": "bar_close",
        "condition": condition(),
    }
    saved = routes.AlarmWrite(**payload)
    assert saved.timeframe == "1d" and len(saved.condition["left"]["inputs"]) == 54
    with pytest.raises(ValueError, match="Yalnız kapanmış"):
        routes.AlarmWrite(**{**payload, "trigger": "intrabar"})
    routes.AlarmWrite(
        **{**payload, "trigger": "intrabar", "condition": condition(output="buy_votes")}
    )
    routes.AlarmWrite(**{**payload, "trigger": "intrabar", "condition": condition("htf_rsi_score")})


@pytest.fixture
def custom_client(api_auth_users, monkeypatch):
    calls = []

    def preview(**kwargs):
        calls.append(kwargs)
        return {"state": "waiting", "points": [], "latest": None}

    monkeypatch.setattr(
        routes,
        "get_advanced_alarm_engine",
        lambda: SimpleNamespace(hub=SimpleNamespace(custom=SimpleNamespace(preview=preview))),
    )
    app = FastAPI()
    app.include_router(routes.router)
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer " + api_auth_users.create_access_token(
            {"sub": "admin"}
        )
        yield client, calls


def test_private_catalog_and_preview_cannot_save_or_activate_an_alarm(custom_client):
    client, calls = custom_client
    response = client.get("/advanced-alarms/indicators/catalog")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert len(response.json()["indicators"]) == 5
    body = {
        "indicator": "rsi_votes",
        "inputs": {},
        "symbol": "GARAN",
        "market_type": "BIST",
        "chart_timeframe": "1d",
    }
    response = client.post("/advanced-alarms/indicators/preview", json=body)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    assert len(calls) == 1 and calls[0]["chart_timeframe"] == "1D"
    assert len(calls[0]["inputs"]) == 54
    assert (
        client.post(
            "/advanced-alarms/indicators/preview", json={**body, "chart_timeframe": "1m"}
        ).status_code
        == 422
    )
    assert len(calls) == 1
    client.headers.clear()
    assert client.get("/advanced-alarms/indicators/catalog").status_code == 401
    assert client.post("/advanced-alarms/indicators/preview", json=body).status_code == 401


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"inputs": {"len1": 0}}, "geçersiz değer"),
        ({"chart_timeframe": "1m"}, "en küçük etkin"),
        ({"inputs": {"len1": "PRIVATE_SESSION_SECRET"}}, "geçersiz değer"),
    ],
)
def test_preview_validation_returns_only_safe_bounded_messages(custom_client, change, message):
    client, calls = custom_client
    body = {
        "indicator": "rsi_votes",
        "inputs": {},
        "symbol": "GARAN",
        "market_type": "BIST",
        **change,
    }
    result = client.post("/advanced-alarms/indicators/preview", json=body)
    assert result.status_code == 422
    assert result.headers["cache-control"] == "private, no-store"
    details = result.json()["detail"]
    assert 1 <= len(details) <= 3
    assert all(set(item) == {"msg"} and len(item["msg"]) <= 300 for item in details)
    assert message in details[0]["msg"]
    assert "PRIVATE_SESSION_SECRET" not in result.text
    assert not calls


def test_alarm_close_validation_reaches_the_form_without_payload_echo(custom_client):
    from tests.test_advanced_alarm_backend import payload

    client, _ = custom_client
    result = client.post(
        "/advanced-alarms",
        json=payload(category="technical", timeframe="1d", condition=condition()),
    )
    assert result.status_code == 422
    assert "Yalnız kapanmış mum" in result.json()["detail"][0]["msg"]
    assert result.headers["cache-control"] == "private, no-store"


def test_standard_history_rejects_custom_timeframe_without_scheduling(custom_client):
    client, calls = custom_client
    response = client.get("/advanced-alarms/history?symbol=GARAN&timeframe=3D")
    assert response.status_code == 422
    assert response.headers["cache-control"] == "private, no-store"
    assert not calls


def test_first_compound_rule_cannot_exceed_custom_configuration_capacity(
    custom_client, monkeypatch
):
    from application.services import custom_indicator_data as data_service
    from infrastructure.repositories import advanced_alarm_repository as repository
    from tests.test_advanced_alarm_backend import payload

    monkeypatch.setattr(data_service, "MAX_CONFIGS", 1)
    client, _ = custom_client
    body = payload(
        category="technical",
        timeframe="1d",
        trigger="bar_close",
        condition={"op": "and", "children": [condition(len1=14), condition(len1=15)]},
    )
    response = client.post("/advanced-alarms", json=body)
    assert response.status_code == 409
    assert repository.list_rules("admin") == []


def test_custom_capacity_is_transactional_shared_and_excludes_the_updated_rule(
    custom_client, monkeypatch
):
    from application.services import custom_indicator_data as data_service
    from infrastructure.repositories import advanced_alarm_repository as repository
    from tests.test_advanced_alarm_backend import payload

    monkeypatch.setattr(data_service, "MAX_CONFIGS", 2)
    client, _ = custom_client

    def body(length, **changes):
        return payload(
            category="technical",
            timeframe="1d",
            trigger="bar_close",
            condition=condition(len1=length, en3=False),
            **changes,
        )

    first = client.post("/advanced-alarms", json=body(14)).json()
    second = client.post("/advanced-alarms", json=body(15)).json()
    shared = body(14)
    shared["condition"]["left"]["inputs"]["showTable"] = False
    shared["condition"]["left"]["output"] = "sell_signal"
    shared_result = client.post("/advanced-alarms", json=shared)
    assert shared_result.status_code == 201
    rejected = client.post("/advanced-alarms", json=body(16))
    assert rejected.status_code == 409 and "2 farklı etkin ayar" in rejected.json()["detail"]
    assert rejected.headers["cache-control"] == "private, no-store"
    paused = client.post("/advanced-alarms", json=body(16, enabled=False))
    assert paused.status_code == 201

    # Replacement frees only its own distinct configuration, atomically.
    updated = client.put(f"/advanced-alarms/{second['id']}", json=body(16, revision=1))
    assert updated.status_code == 200, updated.text
    assert (
        client.put(f"/advanced-alarms/{paused.json()['id']}", json=body(16, revision=1)).status_code
        == 200
    )
    assert (
        client.put(f"/advanced-alarms/{first['id']}", json=body(17, revision=1)).status_code == 409
    )
    # Failed update did not invalidate the stored revision; shared old settings
    # continue to count until every consumer is paused/deleted.
    assert (
        next(row for row in repository.list_rules("admin") if row["id"] == first["id"])["revision"]
        == 1
    )
    assert client.delete(f"/advanced-alarms/{shared_result.json()['id']}").status_code == 200
    assert (
        client.put(f"/advanced-alarms/{first['id']}", json=body(17, revision=1)).status_code == 200
    )
    with pytest.raises(repository.Conflict, match="etkin ayar"):
        repository.save_rule("another-owner", body(18))
    assert client.post("/advanced-alarms", json=payload()).status_code == 201
