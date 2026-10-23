"""The account-protection stop must stay idle and never return cached signals."""

from copy import deepcopy
from types import SimpleNamespace

from application.services.advanced_alarm_conditions import condition_fields
from application.services.custom_indicator_data import CustomIndicatorData
from tests.test_custom_indicator_bootstrap import configured, quote, witness
from tests.test_custom_indicator_data import NOW, Provider, rule


def forbidden(*_args, **_kwargs):
    raise AssertionError("Paused provider must not plan or access data")


def test_paused_universe_preserves_definitions_without_native_planning(monkeypatch):
    provider = Provider()
    provider.tradingview_enabled = False
    provider.data_epoch = forbidden
    provider.custom_indicator_history = forbidden
    provider.refresh_custom_indicator_auth = forbidden
    service = CustomIndicatorData(provider=provider, clock=lambda: NOW)
    monkeypatch.setattr(service.live, "configure", forbidden)
    selected = rule()
    selected.update(scope="all_bist", symbols=[], trigger="intrabar")
    before = deepcopy(selected)
    service.configure([selected], universe=[{"symbol": f"TEST{i}"} for i in range(631)])
    for _ in range(3):
        service.live.control_step()
        assert service._next_job() is None
    assert selected == before
    assert service._jobs_requested == 631
    assert not service.live._wanted and not service._job_order and not service._seed_queue
    coverage = service.coverage()
    assert coverage["pending_members"] == 631
    assert all(row["reasons"] == ["provider_paused"] for row in coverage["rows"])
    assert service.status()["provider_paused"]
    assert "duraklatıldı" in service.status()["last_error"]


def test_pause_hides_ready_values_and_does_not_consume_history_job():
    clock, provider, service, selected, key = configured()
    service.process(*service._next_job())
    witness(service, key, clock)
    quote(service, key, clock, 151)
    ref = condition_fields(selected["condition"], "1d")[0]
    assert service.observation(ref, selected["symbols"][0], "intrabar", clock[0])["ready"]
    calls = len(provider.calls)
    provider.tradingview_enabled = False
    provider.data_epoch = forbidden
    result = service.observation(ref, selected["symbols"][0], "intrabar", clock[0])
    assert result["current"] is None and not result["ready"]
    assert "duraklatıldı" in result["reason"]
    assert service._read(key, clock[0])[0] is None
    service.process(key, service.live._configs[key], service._generation)
    assert len(provider.calls) == calls
    preview = service.preview("rsi_votes", ref["inputs"], key[1])
    assert preview["latest"] is None and "duraklatıldı" in preview["reason"]


def test_pause_closes_existing_stream_once_without_auth_retry():
    _, provider, service, _, _ = configured()
    provider.tradingview_enabled = False
    provider.data_epoch = forbidden
    provider.refresh_custom_indicator_auth = forbidden
    closed = []
    service.live._connection = SimpleNamespace(close=lambda: closed.append(True))
    for _ in range(3):
        service.live.control_step()
    assert closed == [True]
    assert service.live._connection is None and not service.live._subscribed
    assert service.live._failures == 0
