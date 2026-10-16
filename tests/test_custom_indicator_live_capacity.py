"""Admission arithmetic, not a claim about upstream or production throughput."""

import pytest

from application.services.custom_indicator_data import CustomIndicatorData
from tests.test_custom_indicator_data import NOW, Provider, rule


@pytest.mark.parametrize("all_timeframes", [False, True])
def test_five_indicators_for_631_symbols_report_actual_provider_capacity(all_timeframes):
    provider = Provider()
    service = CustomIndicatorData(provider=provider, clock=lambda: NOW)
    rules = []
    for index, indicator in enumerate(
        ("htf_rsi_score", "rsi_snapshot", "rsi_votes", "smi_votes", "rmi_votes")
    ):
        current = rule(index)
        current.update(scope="all_bist", symbols=[], trigger="intrabar")
        current["condition"]["left"].update(indicator=indicator, inputs={})
        if all_timeframes and indicator != "htf_rsi_score":
            current["condition"]["left"]["inputs"] = {f"en{slot}": True for slot in range(1, 11)}
        rules.append(current)
    universe = [{"symbol": f"T{index:04}"} for index in range(631)]
    service.configure(rules, universe=universe)
    status = service.status()
    assert status["requested_rule_symbols"] == 3155
    assert len(service.live._configs) == 180 * 5
    # The union includes Snapshot's distinct 7D plus the ten default frames.
    assert len(service.live._wanted) == 180 * 11
    assert status["native_subscriptions_requested"] == 631 * 11
    assert status["blocked_rule_symbols"] == (631 - 180) * 5
    assert 0 < service.live._admitted_cells <= 2_000_000
    assert not service.live._compiled and not service.live._threads
    assert provider.calls == []


def test_large_watchlist_admits_whole_symbols_without_resetting_existing_members():
    service = CustomIndicatorData(provider=Provider(), clock=lambda: NOW)
    selected = rule()
    selected.update(scope="all_bist", symbols=[], trigger="intrabar")
    selected["condition"]["left"].update(
        indicator="smi_votes", inputs={f"en{slot}": True for slot in range(1, 11)}
    )
    universe = [{"symbol": f"T{index:04}"} for index in range(805)]
    service.configure([selected], universe=universe)
    slots = service.live._member_slots.copy()
    original = service.live._wanted.copy()
    status = service.status()
    assert len(slots) == 200
    assert status["native_subscriptions_requested"] == 8050
    assert status["native_subscriptions_admitted"] == 2000
    assert status["native_subscriptions_blocked"] == 6050
    assert status["blocked_rule_symbols"] == 605
    assert all(sum(slots[key[:2]] == slot for key in original) == 500 for slot in range(4))
    # A new earlier-sorting symbol cannot displace a running member or move its
    # bars away from the socket carrying its ordered price observations.
    service.configure([selected], universe=[{"symbol": "AAAA"}, *universe])
    assert service.live._member_slots == slots
    assert service.live._wanted == original
    assert service.status()["blocked_rule_symbols"] == 606
    assert not service.live._threads and not service.provider.calls


def test_same_config_many_rules_does_not_multiply_native_subscriptions():
    service = CustomIndicatorData(provider=Provider(), clock=lambda: NOW)
    selected = rule()
    selected.update(scope="all_bist", symbols=[], trigger="intrabar")
    service.configure(
        [{**selected, "id": str(index)} for index in range(3000)],
        universe=[{"symbol": f"T{index:04}"} for index in range(631)],
    )
    assert len(service.live._configs) == 631
    assert len(service.live._wanted) == 631
    assert service.status()["blocked_rule_symbols"] == 0
