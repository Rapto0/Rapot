"""Repeated unusable quote packets must not starve a bounded history recovery."""

import pytest

from tests.test_custom_indicator_data import NOW
from tests.test_custom_indicator_live_data import observation, quote, ready_service
from tests.test_custom_indicator_live_leases import leased_service, native_event


@pytest.mark.parametrize("price,source", [(150, NOW - 31), (float("nan"), NOW)])
def test_repeated_invalid_quotes_do_not_cancel_a_new_seed_or_restore_a_signal(price, source):
    clock, provider, service, selected, key, ref = ready_service()
    clock[0] = NOW + 1
    quote(service, clock, 20)
    service.live.process_event()
    assert observation(service, selected, ref, clock)["ready"]
    prior_epoch = service.publication_token(key[:2])
    quote(service, clock, price, source=source)
    service.live.process_event()
    epoch = service.publication_token(key[:2])
    assert epoch != prior_epoch
    assert not observation(service, selected, ref, clock)["ready"]
    assert key not in service.live._compiled
    service.process(*service._next_job())
    prepared = service.live._compiled[key]
    native = dict(service._native)
    count = len(provider.calls)
    for _ in range(100):
        quote(service, clock, price, source=source)
        service.live.process_event()
    assert service.publication_token(key[:2]) == epoch
    assert service.live._compiled[key] is prepared
    assert service._native == native
    assert len(provider.calls) == count
    assert service._next_job() is None
    assert not observation(service, selected, ref, clock)["ready"]
    clock[0] += 1
    quote(service, clock, 21)
    service.live.process_event()
    assert observation(service, selected, ref, clock)["ready"]
    assert service._results[key]["previous"] is None
    assert key[:2] not in service.live._invalid_quote_members
    # A later, genuinely separate invalid period breaks continuity again.
    quote(service, clock, price, source=source)
    service.live.process_event()
    assert service.publication_token(key[:2]) != epoch
    assert key not in service.live._compiled


def test_invalid_quote_wait_is_bounded_to_configured_members_and_transport_generation():
    clock, _, service, _, key, _ = ready_service()
    quote(service, clock, 0)
    service.live.process_event()
    assert service.live._invalid_quote_members == {key[:2]}
    service.live.invalidate()
    assert not service.live._invalid_quote_members
    quote(service, clock, 0)
    service.live.process_event()
    service.configure([])
    assert not service.live._invalid_quote_members
    quote(service, clock, 0)
    service.live.process_event()
    assert not service.live._invalid_quote_members


def test_rejected_subscription_recovers_only_after_semantically_valid_current_witness():
    clock, service, _, key, _, connection = leased_service()
    native_key = (*key[:2], "2D")
    service.live._refused.add(native_key)
    assert not service.live.history_ready(key[:2], {"1D", "2D"})
    event = native_event(service, "2D", clock[0] + 1)
    connection.accepted = False
    service.live._bars(event)
    assert native_key in service.live._refused
    connection.accepted = True
    malformed = {**event, "rows": [event["rows"][0], (NOW, 100, 50, 90, 100)]}
    service.live._bars(malformed)
    assert native_key in service.live._refused
    service.live._bars(event)
    assert native_key not in service.live._refused
    assert service.live.history_ready(key[:2], {"1D", "2D"})
