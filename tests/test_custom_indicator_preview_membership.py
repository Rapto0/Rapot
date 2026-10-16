"""Preview renewal cannot continually replan unchanged native subscriptions."""

from application.services.custom_indicators import catalog
from tests.test_custom_indicator_bootstrap import configured


def requested_previews(monkeypatch):
    clock, _, service, _, _ = configured()
    configurations = []
    original = service.live.configure

    def configure(*args, **kwargs):
        configurations.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(service.live, "configure", configure)
    for indicator in catalog.SPECS:
        service.preview(indicator, {}, "THYAO")
    return clock, service, configurations


def test_polling_unchanged_previews_preserves_plan_cursor_and_inflight_queue(monkeypatch):
    clock, service, configurations = requested_previews(monkeypatch)
    before = len(configurations)
    service._job_cursor = 3
    signature = service._live_signature
    preparing = service._seed_queue.popleft()
    service._seed_queued.remove(preparing)
    assert not service.live.has_seed(preparing, service.provider.memory_epoch())
    queued = tuple(service._seed_queue)
    for _ in range(4):
        for indicator in catalog.SPECS:
            clock[0] += 1
            service.preview(indicator, {}, "THYAO")
    assert len(configurations) == before
    assert service._live_signature == signature
    assert service._job_cursor == 3
    assert tuple(service._seed_queue) == queued
    assert preparing not in service._seed_queued


def test_new_preview_membership_still_replans_once(monkeypatch):
    _, service, configurations = requested_previews(monkeypatch)
    before = len(configurations)
    service.preview("rsi_votes", {}, "GARAN")
    assert len(configurations) == before + 1
    assert any(key[:2] == ("BIST", "GARAN") for key in service.live._configs)
    service.preview("rsi_votes", {}, "GARAN")
    assert len(configurations) == before + 1


def test_expired_membership_replans_while_renewed_preview_stays_admitted(monkeypatch):
    clock, service, configurations = requested_previews(monkeypatch)
    before = len(configurations)
    clock[0] += 100
    service.preview("smi_votes", {}, "THYAO")
    assert len(configurations) == before
    active = next(
        key for key, (_, config) in service._previews.items() if config["indicator"] == "smi_votes"
    )
    clock[0] += 21
    service._sync_live()
    assert len(configurations) == before + 1
    assert active in service.live._configs
    assert all(key == active or key[2] in service._configs for key in service.live._configs)
