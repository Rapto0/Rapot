"""Private bounded readiness diagnostics never request data or evaluate alarms."""

from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import advanced_alarm_routes as routes
from application.services import advanced_alarm_service as engine_service
from application.services import custom_indicator_data as module
from application.services.advanced_alarm_market_data import AdvancedMarketData
from application.services.custom_indicator_data import CustomIndicatorData
from tests.test_custom_indicator_data import NOW, Provider, inputs, rule
from tests.test_custom_indicator_live_data import quote, ready_service


def ready():
    clock, provider, service, selected, key, ref = ready_service()
    clock[0] = NOW + 1
    quote(service, clock, 20)
    service.live.process_event()
    return clock, provider, service, selected, key, ref


def test_reports_current_selected_outputs_and_native_requirements_without_values():
    clock, _, service, _, _, _ = ready()
    value = service.coverage()
    row = value["rows"][0]
    assert value["scope"] == "configured_rule_selected_outputs"
    assert value["ready_members"] == 1 and row["ready"]
    assert row["configured_configurations"] == row["ready_configurations"] == 1
    assert row["requested_timeframes"] == ["1D"]
    assert row["refused_timeframes"] == [] and row["reasons"] == []
    assert row["source_timestamp"] == module._iso(clock[0])
    assert row["received_at"] == module._iso(clock[0])
    assert value["values_included"] is False
    assert "live_price" not in str(value) and "current" not in row


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), -float("inf")])
def test_missing_or_nonfinite_selected_output_is_never_ready(value):
    _, _, service, _, key, ref = ready()
    service._results[key]["points"][-1]["outputs"][ref["output"]] = value
    row = service.coverage()["rows"][0]
    assert not row["ready"] and row["pending_configurations"] == 1
    assert row["reasons"] in (["output_unavailable"], ["output_or_native_witness_unavailable"])


@pytest.mark.parametrize("value", [0, 0.0, False, True])
def test_finite_zero_and_boolean_are_available_not_missing(value):
    _, _, service, _, key, ref = ready()
    service._results[key]["points"][-1]["outputs"][ref["output"]] = value
    assert service.coverage()["rows"][0]["ready"]


def test_selected_output_and_trigger_memberships_do_not_bleed_between_symbols():
    _, _, service, selected, key, _ = ready()
    other = deepcopy(selected)
    other["id"] = "other"
    other["symbols"] = [{"symbol": "GARAN", "market_type": "BIST"}]
    other["condition"]["left"]["output"] = "sell_signal"
    service.configure([selected, other])
    # The other symbol's missing output is not part of THYAO's demand.
    service._results[key]["points"][-1]["outputs"].pop("sell_signal", None)
    rows = {r["symbol"]: r for r in service.coverage()["rows"]}
    assert rows["THYAO"]["ready"]
    assert not rows["GARAN"]["ready"]


def test_shared_configuration_requires_every_selected_output():
    _, _, service, selected, key, _ = ready()
    other = deepcopy(selected)
    other["id"] = "other"
    other["condition"]["left"]["output"] = "sell_signal"
    service.configure([selected, other])
    service._results[key]["points"][-1]["outputs"].pop("sell_signal", None)
    result = service.coverage()
    assert result["inspected_config_member_pairs"] == 1
    assert not result["rows"][0]["ready"]
    assert len(service._coverage_scopes) == 1


def test_close_only_reads_confirmed_output_and_intrabar_waits_for_live_quote():
    service = CustomIndicatorData(provider=Provider(), clock=lambda: NOW)
    closed = rule()
    service.configure([closed])
    service.process(*service._next_job())
    service.live._enabled = True
    assert service.coverage()["rows"][0]["ready"]
    intrabar = {**closed, "trigger": "intrabar"}
    service.configure([intrabar])
    row = service.coverage()["rows"][0]
    assert not row["ready"] and row["reasons"] == ["live_quote_wait"]


def test_stale_native_quote_refusal_epoch_and_missing_seed_are_distinct():
    clock, provider, service, _, key, _ = ready()
    clock[0] += 31
    assert service.coverage()["rows"][0]["reasons"] == ["quote_stale"]
    service.live._refused.add((*key[:2], "1D"))
    row = service.coverage()["rows"][0]
    assert row["refused_timeframes"] == ["1D"]
    service.live._compiled.pop(key)
    assert service.coverage()["rows"][0]["reasons"] == ["native_refused"]
    service.live._refused.clear()
    assert service.coverage()["rows"][0]["reasons"] == ["seed_wait"]
    service.live._enabled = False
    provider.generation += 1
    assert service.coverage()["rows"][0]["reasons"] == ["account_or_transport_changed"]


def test_read_has_no_provider_calls_wake_lru_queue_or_state_changes(monkeypatch):
    _, provider, service, _, _, _ = ready()

    def forbidden(*_a, **_k):
        pytest.fail("read-only coverage attempted work")

    for name in ("custom_indicator_history", "data_epoch"):
        monkeypatch.setattr(provider, name, forbidden)
    for name in ("_sync_live", "_queue_seed", "start", "preview", "process"):
        monkeypatch.setattr(service, name, forbidden)
    monkeypatch.setattr(service._wake, "set", forbidden)
    before = (
        list(service._results),
        list(service._native),
        list(service._previews),
        list(service._seed_queue),
        set(service._seed_queued),
        set(service._seed_due),
        deepcopy(service._results),
        len(provider.calls),
        service._generation,
    )
    for _ in range(5):
        assert service.coverage()["ready_members"] == 1
    after = (
        list(service._results),
        list(service._native),
        list(service._previews),
        list(service._seed_queue),
        set(service._seed_queued),
        set(service._seed_due),
        deepcopy(service._results),
        len(provider.calls),
        service._generation,
    )
    assert before == after


def test_preview_only_member_and_disabled_rule_are_excluded():
    service = CustomIndicatorData(provider=Provider(), clock=lambda: NOW)
    service.configure([{**rule(), "enabled": False}])
    service.preview("rsi_votes", inputs(), "THYAO")
    assert service.coverage()["row_count"] == 0
    assert service.coverage()["requested_config_member_pairs"] == 0


def test_mixed_crypto_and_all_bist_use_current_universe_and_exact_scopes():
    service = CustomIndicatorData(provider=Provider(), clock=lambda: NOW)
    all_bist = {**rule(), "scope": "all_bist", "symbols": []}
    crypto = rule(2, market="Kripto")
    service.configure([all_bist, crypto], universe=[{"symbol": "GARAN"}])
    rows = service.coverage()["rows"]
    assert {(r["market_type"], r["symbol"]) for r in rows} == {
        ("BIST", "GARAN"),
        ("Kripto", "BTCUSDT"),
    }
    service.set_universe([{"symbol": "THYAO"}])
    assert {r["symbol"] for r in service.coverage()["rows"]} == {"THYAO", "BTCUSDT"}


def test_symbol_and_pair_bounds_are_visible_never_false_ready(monkeypatch):
    service = CustomIndicatorData(provider=Provider(), clock=lambda: NOW)
    selected = {
        **rule(),
        "symbols": [{"symbol": s, "market_type": "BIST"} for s in ("THYAO", "GARAN", "AKBNK")],
    }
    service.configure([selected])
    monkeypatch.setattr(module, "MAX_COVERAGE_SYMBOLS", 2)
    first = service.coverage()
    assert first["rows_truncated"] and first["row_count"] == 2
    assert first["ready_members"] == 0
    assert all(r["state"] == "not_inspected" for r in first["rows"])
    monkeypatch.setattr(module, "MAX_COVERAGE_SYMBOLS", 4000)
    monkeypatch.setattr(module, "MAX_COVERAGE_PAIRS", 1)
    second = service.coverage()
    assert second["pairs_truncated"] and second["inspected_config_member_pairs"] == 1
    assert all(r["configured_configurations"] is None for r in second["rows"])


def test_metadata_capacity_never_drops_an_output_and_reports_ready(monkeypatch):
    _, _, service, selected, _, _ = ready()
    other = deepcopy(selected)
    other["id"] = "other"
    other["condition"]["left"]["output"] = "sell_signal"
    monkeypatch.setattr(module, "MAX_COVERAGE_PAIRS", 1)
    service.configure([selected, other])
    result = service.coverage()
    assert result["metadata_truncated"]
    assert result["rows"][0]["state"] == "not_inspected"
    assert result["rows"][0]["reasons"] == ["metadata_capacity"]


def test_many_same_scope_rules_share_one_membership_set():
    service = CustomIndicatorData(provider=Provider(), clock=lambda: NOW)
    selected = rule()
    service.configure([{**selected, "id": str(i)} for i in range(100)])
    assert len(service._coverage_scopes) == 1
    assert sum(map(len, service._coverage_demands.values())) == 1
    assert service.coverage()["inspected_config_member_pairs"] == 1


def test_market_coverage_exposes_separate_ordinary_and_custom_freshness(tmp_path):
    clock, _, custom, _, _, _ = ready()
    settings = SimpleNamespace(
        database_path=str(tmp_path / "main.db"),
        advanced_alarm_cache_path=None,
        advanced_alarm_market_enabled=True,
        advanced_alarm_max_symbols=2000,
        advanced_alarm_quote_stale_seconds=120,
    )
    hub = AdvancedMarketData(
        settings,
        provider=SimpleNamespace(memory_epoch=lambda: 1),
        cache=object(),
        clock=lambda: clock[0],
    )
    hub._custom = custom
    result = hub.coverage()
    assert result["quote_freshness_policy_seconds"] == 120
    assert result["custom_indicators"]["intrabar_source_and_receipt_stale_seconds"] == 30
    assert result["custom_indicators"]["ready_members"] == 1


def test_custom_coverage_remains_admin_private(api_auth_users, monkeypatch):
    _, _, custom, _, _, _ = ready()
    monkeypatch.setattr(
        engine_service,
        "_engine",
        SimpleNamespace(
            hub=SimpleNamespace(coverage=lambda: {"custom_indicators": custom.coverage()})
        ),
    )
    app = FastAPI()
    app.include_router(routes.router)
    with TestClient(app) as client:
        assert client.get("/advanced-alarms/coverage").status_code == 401
        assert (
            client.get(
                "/advanced-alarms/coverage",
                headers={
                    "Authorization": "Bearer " + api_auth_users.create_access_token({"sub": "user"})
                },
            ).status_code
            == 403
        )
        response = client.get(
            "/advanced-alarms/coverage",
            headers={
                "Authorization": "Bearer " + api_auth_users.create_access_token({"sub": "admin"})
            },
        )
        assert response.status_code == 200
        assert response.headers["cache-control"] == "private, no-store"
        assert response.json()["custom_indicators"]["ready_members"] == 1
