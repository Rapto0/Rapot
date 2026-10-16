"""Application-side lease certificates and same-price native daily range fencing."""

from copy import deepcopy
from dataclasses import replace

import pytest

from application.services.advanced_alarm_conditions import condition_fields
from application.services.custom_indicator_data import CustomIndicatorData
from tests.test_custom_indicator_data import NOW, SESSION, Provider, rule
from tests.test_custom_indicator_live_data import quote


class Certificates:
    connected = True

    def __init__(self):
        self.current = (1, 1, 1)
        self.accepted = True
        self.invalidated = False
        self.calls = []

    def member_ready(self, _member):
        return True

    def status(self):
        return {}

    def witness_valid(self, _key, certificate):
        return certificate == self.current

    def confirm_native_witness(self, event):
        self.calls.append(event)
        return {"accepted": self.accepted, "invalidated": self.invalidated}


def leased_service():
    clock = [NOW + 0.2]
    provider = Provider()
    service = CustomIndicatorData(provider=provider, clock=lambda: clock[0])
    selected = rule()
    selected["trigger"] = "intrabar"
    selected["condition"]["left"]["indicator"] = "smi_votes"
    selected["condition"]["left"]["inputs"]["en2"] = True
    service.configure([selected])
    service.process(*service._next_job())
    service.live._enabled = True
    key = next(iter(service.live._configs))
    for timeframe in ("1D", "2D"):
        bars = service._native[("BIST", "THYAO", timeframe)].bars
        service.live._buckets[("BIST", "THYAO", timeframe)] = (
            (replace(bars[-2], confirmed=True), replace(bars[-1], confirmed=False)),
            clock[0],
        )
    connection = Certificates()
    service.live._connection = connection
    service.live._witness_certificates[("BIST", "THYAO", "2D")] = connection.current
    service.preview("smi_votes", selected["condition"]["left"]["inputs"], "THYAO")
    ref = condition_fields(selected["condition"], "1d")[0]
    return clock, service, selected, key, ref, connection


def native_event(service, timeframe, received, *, high=None):
    bars = service.live._buckets[("BIST", "THYAO", timeframe)][0]
    rows = [
        (bar.time, bar.open, high if index == 1 and high else bar.high, bar.low, bar.close)
        for index, bar in enumerate(bars)
    ]
    return {
        "kind": "bars",
        "key": ("BIST", "THYAO", timeframe),
        "rows": rows,
        "metadata": SESSION,
        "received_at": received,
        "native_stream_generation": 1,
        "native_day_generation": 1,
        "native_lease_id": 1,
    }


def test_native_daily_range_updates_certified_long_smi_at_safe_source_time():
    clock, service, _, key, _, _ = leased_service()
    reference = deepcopy(service.live._compiled[key]["evaluator"])
    clock[0] = NOW + 2.2
    service.live._bars(native_event(service, "1D", clock[0], high=2000))
    quote(service, clock, 150, source=NOW + 2)
    service.live.process_event()
    assert not service._results[key]["points"][-1]["ready"]
    assert service.live._compiled[key]["buckets"]["2D"].high < 2000
    clock[0] = NOW + 3
    quote(service, clock, 160)
    service.live.process_event()
    actual = service._preview_results[key]["points"][-1]
    assert actual["ready"]
    buckets = service.live._compiled[key]["buckets"]
    assert buckets["1D"].high == buckets["2D"].high == 2000
    expected = reference.evaluate(price=160, as_of=clock[0], buckets=buckets)
    assert [row["value"] for row in actual["rows"] if row["value"] is not None] == pytest.approx(
        [row["value"] for row in expected["rows"] if row["value"] is not None]
    )


def test_new_pool_certificate_cannot_authorize_old_application_bucket():
    clock, service, selected, key, ref, connection = leased_service()
    assert service.live.history_ready(("BIST", "THYAO"), {"1D", "2D"})
    connection.current = (1, 2, 2)
    assert not service.live.history_ready(("BIST", "THYAO"), {"1D", "2D"})
    clock[0] = NOW + 2
    quote(service, clock, 150)
    service.live.process_event()
    assert not service.observation(ref, selected["symbols"][0], "intrabar", clock[0])["ready"]
    assert service.live._compiled[key]  # Native seed alone is not a valid certificate.


def test_daily_revision_clears_all_long_witnesses_and_published_signal_baseline():
    clock, service, _, key, _, connection = leased_service()
    clock[0] = NOW + 2
    quote(service, clock, 150)
    service.live.process_event()
    assert service._results[key]["points"][-1]["ready"]
    connection.invalidated = True
    service.live._bars(native_event(service, "1D", clock[0] + 0.1, high=200))
    assert key not in service.live._compiled
    assert ("BIST", "THYAO", "2D") not in service.live._buckets
    assert service.live._witness_certificates == {}
    assert service._results[key]["error"]
    assert "previous" not in service._results[key]
    assert not service._native


def test_invalid_or_obsolete_lease_packet_cannot_install_a_native_witness():
    clock, service, _, _, _, connection = leased_service()
    event = native_event(service, "2D", clock[0] + 1)
    old = service.live._buckets[event["key"]]
    connection.accepted = False
    service.live._bars(event)
    assert service.live._buckets[event["key"]] is old
    assert len(connection.calls) == 1
    event["rows"][1] = (NOW, 100, 50, 90, 100)  # Invalid native high.
    service.live._bars(event)
    assert len(connection.calls) == 1  # Semantic validation precedes transport ACK.
    assert service.live._buckets[event["key"]] is old
