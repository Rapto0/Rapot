"""Admission arithmetic, not a claim about upstream or production throughput."""

import pytest

from application.services.custom_indicator_data import CustomIndicatorData
from tests.test_custom_indicator_data import NOW, Provider, rule


@pytest.mark.parametrize("all_timeframes", [False, True])
def test_five_indicators_for_631_symbols_fit_shared_native_admission(all_timeframes):
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
    assert len(service.live._configs) == 3155
    # The union includes Snapshot's distinct 7D plus the ten default frames.
    assert len(service.live._wanted) == 631 * 11
    assert status["blocked_rule_symbols"] == 0
    assert 0 < service.live._admitted_cells <= 2_000_000
    assert not service.live._compiled and not service.live._threads
    assert provider.calls == []


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
