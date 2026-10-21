"""Prepared operand identities save work without caching price or account state."""

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from types import MappingProxyType, SimpleNamespace

import pytest

from application.services.advanced_alarm_conditions import (
    PreparedCustomReference,
    field_key,
    prepare_condition,
)
from application.services.advanced_alarm_market_data import AdvancedMarketData
from application.services.custom_indicators import catalog
from tests.test_custom_indicator_bootstrap import configured, quote, witness
from tests.test_custom_indicator_data import rule


def prepared_hub():
    clock, provider, service, selected, key = configured("smi_votes", all_timeframes=True)
    settings = SimpleNamespace(
        database_path="unused-offline.sqlite3",
        advanced_alarm_cache_path=None,
        advanced_alarm_market_enabled=True,
        advanced_alarm_quote_stale_seconds=30,
    )
    hub = AdvancedMarketData(settings, provider=provider, cache=object(), clock=lambda: clock[0])
    hub._custom, hub._epoch = service, provider.generation
    hub.configure([selected])
    service.process(*service._next_job())
    witness(service, key, clock)
    quote(service, key, clock, 200)
    assert hub.snapshot(selected, selected["symbols"][0])["ready"]
    return clock, provider, service, hub, selected, key


def test_prepared_reference_identity_is_immutable_and_independent_of_raw_inputs():
    selected = rule()
    plan = prepare_condition(selected["condition"], selected["timeframe"])
    ref = plan.fields[0]
    assert isinstance(ref, PreparedCustomReference)
    raw = {**ref, "inputs": dict(ref["inputs"])}
    assert field_key(ref, "1d") == field_key(raw, "1d") == plan.keys[0]
    assert ref.configuration_id == catalog.config_key(ref["indicator"], raw["inputs"], "1D")
    selected["condition"]["left"]["inputs"]["len1"] = 200
    raw["inputs"]["len1"] = 199
    assert ref["inputs"]["len1"] not in {199, 200}
    with pytest.raises(TypeError):
        ref["inputs"]["len1"] = 198
    with pytest.raises(TypeError):
        ref["output"] = "sell_signal"
    with pytest.raises(FrozenInstanceError):
        ref.configuration_id = "changed"


def test_same_config_different_outputs_share_identity_but_keep_distinct_field_keys():
    selected = rule()
    other = deepcopy(selected["condition"])
    other["left"]["output"] = "sell_signal"
    plan = prepare_condition({"op": "or", "children": [selected["condition"], other]}, "1d")
    first, second = plan.fields
    assert first.configuration_id == second.configuration_id
    assert first.cache_key != second.cache_key


def test_every_new_quote_reuses_only_validated_identity_not_snapshot(monkeypatch):
    clock, _provider, service, hub, selected, key = prepared_hub()
    member = selected["symbols"][0]
    prior = hub.snapshot(selected, member)
    refs = hub._plans[(selected["id"], selected["revision"])][2].fields

    def no_revalidation(*_args, **_kwargs):
        pytest.fail("A prepared snapshot must not repeat config validation or hashing")

    monkeypatch.setattr(catalog, "config_key", no_revalidation)
    monkeypatch.setattr(catalog, "validate_config", no_revalidation)
    for price in (20, 150, 75):
        quote(service, key, clock, price)
        result = hub.snapshot(selected, member)
        assert result["ready"]
        assert result["observation_id"] != prior["observation_id"]
        assert result["source_timestamp"] != prior["source_timestamp"]
        assert (
            result["values"][refs[0].cache_key]
            == service._results[key]["points"][-1]["outputs"]["buy_signal"]
        )
        prior = result


def test_prepared_and_revalidated_refs_produce_identical_mixed_snapshots():
    clock, _provider, service, hub, selected, key = prepared_hub()
    base = deepcopy(selected["condition"]["left"])
    selected["condition"] = {
        "op": "and",
        "children": [
            {"op": "crossed_above", "left": {**base, "output": "buy_votes"}, "right": 5},
            {"op": "lt", "left": {**base, "output": "sell_votes"}, "right": 10},
            {"op": "gt", "left": {"field": "price"}, "right": 0},
        ],
    }
    selected["revision"] += 1
    hub.configure([selected])
    plan_key = (selected["id"], selected["revision"])
    cached = hub._plans[plan_key]
    # Plain immutable mappings reproduce the previous per-read validation path.
    previous_plan = replace(
        cached[2], fields=tuple(MappingProxyType(dict(ref)) for ref in cached[2].fields)
    )
    for price in (20, 175, 25, 160):
        quote(service, key, clock, price)
        prepared = hub.snapshot(selected, selected["symbols"][0])
        hub._plans[plan_key] = (*cached[:2], previous_plan)
        try:
            revalidated = hub.snapshot(selected, selected["symbols"][0])
        finally:
            hub._plans[plan_key] = cached
        assert prepared == revalidated
        assert prepared["ready"]
    clock[0] += 31
    prepared = hub.snapshot(selected, selected["symbols"][0])
    hub._plans[plan_key] = (*cached[:2], previous_plan)
    assert prepared == hub.snapshot(selected, selected["symbols"][0])
    assert not prepared["ready"]


@pytest.mark.parametrize("change", ["stale", "account", "refused", "missing_seed", "gap"])
def test_prepared_identity_never_bypasses_unknown_or_freshness_guards(change, monkeypatch):
    clock, provider, service, hub, selected, key = prepared_hub()
    monkeypatch.setattr(
        catalog, "config_key", lambda *_args, **_kwargs: pytest.fail("Unexpected config rebuild")
    )
    if change == "stale":
        clock[0] += 31
    elif change == "account":
        provider.generation += 1
    elif change == "refused":
        service.live._refused.add((*key[:2], "2D"))
        quote(service, key, clock, 150)
    elif change == "missing_seed":
        service.live._compiled.pop(key)
        quote(service, key, clock, 150)
    else:
        service.live_gap("Synthetic source gap", key[:2])
    assert not hub.snapshot(selected, selected["symbols"][0])["ready"]


def test_in_place_rule_mutation_cannot_reuse_old_identity_before_reconfigure():
    clock, _provider, service, hub, selected, key = prepared_hub()
    old_plan = hub._plans[(selected["id"], selected["revision"])][2]
    old_inputs = dict(old_plan.fields[0]["inputs"])
    selected["condition"]["left"]["inputs"]["len1"] = old_inputs["len1"] + 1
    assert dict(old_plan.fields[0]["inputs"]) == old_inputs
    assert not hub.snapshot(selected, selected["symbols"][0])["ready"]
    selected["revision"] += 1
    hub.configure([selected])
    new_plan = hub._plans[(selected["id"], selected["revision"])][2]
    assert new_plan.fields[0].configuration_id != old_plan.fields[0].configuration_id
    new_key = next(iter(service.live._configs))
    assert new_key != key
    service.process(*service._next_job())
    witness(service, new_key, clock)
    quote(service, new_key, clock, 175)
    assert hub.snapshot(selected, selected["symbols"][0])["ready"]


def test_serialized_user_reference_cannot_supply_a_cached_identity():
    selected = rule()
    selected["condition"]["left"]["configuration_id"] = "untrusted-cache-key"
    with pytest.raises(ValueError):
        prepare_condition(selected["condition"], "1d")
