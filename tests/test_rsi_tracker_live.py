"""Tracker continuity and admission over the ordered native event path."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.borsapy_market_routes import router
from application.services import advanced_alarm_market_data
from application.services.custom_indicator_data import CustomIndicatorData, native_bars
from application.services.custom_indicators.core import rsi_values
from application.services.rsi_tracker import NATIVE_TIMEFRAMES, TrackerSeed
from tests.test_custom_indicator_bootstrap import configured, quote, witness
from tests.test_custom_indicator_data import NOW, Provider, frame


def test_intrabar_rsi_uses_same_price_for_all_16_periods_without_compounding_quotes():
    clock = [NOW + 0.2]
    service = CustomIndicatorData(provider=Provider(), clock=lambda: clock[0])
    periods = tuple(NATIVE_TIMEFRAMES)
    member = ("BIST", "THYAO")
    service.tracker_snapshot("tab", "BIST", ["THYAO"], periods)
    assert service.provider.calls == []
    service._sync_live()
    assert len(service.live._tracker_wanted) == 16
    assert not service.live._configs
    service.live._connection = SimpleNamespace(connected=True)
    oracle = {}
    for index, tf in enumerate(NATIVE_TIMEFRAMES.values()):
        raw = frame(tf, count=60 + index)
        bars = native_bars(raw, tf, "BIST", clock[0])
        # The fixture's short bars open at the session open. The observed tick
        # must instead belong to a provider-witnessed current intraday bucket.
        if tf.isdigit():
            bars = (*bars[:-1], replace(bars[-1], time=NOW - 30, end=NOW + 600))
        key = (*member, tf)
        service.tracker.seeds[key] = TrackerSeed.build(bars, 1, clock[0])
        service.live._buckets[key] = (bars[-2:], clock[0])
        oracle[tf] = list(raw.Close.iloc[:-1])

    for price in (100, 190, 105):
        quote(service, member, clock, price)
        row = service.tracker_snapshot("tab", "BIST", ["THYAO"], periods)["rows"]["THYAO"]
        assert row["source_time"] == clock[0]
        assert row["price"] == price
        for ui, tf in NATIVE_TIMEFRAMES.items():
            assert row["cells"][ui]["status"] == "ready"
            assert row["cells"][ui]["value"] == pytest.approx(
                rsi_values([*oracle[tf], price], 14)[-1]
            )

    clock[0] += 31
    row = service.tracker_snapshot("tab", "BIST", ["THYAO"], periods)["rows"]["THYAO"]
    assert {cell["status"] for cell in row["cells"].values()} == {"stale"}
    service.provider.generation += 1
    row = service.tracker_snapshot("tab", "BIST", ["THYAO"], periods)["rows"]["THYAO"]
    assert all(cell["value"] is None for cell in row["cells"].values())


def test_shared_history_lease_and_rejection_do_not_reseed_existing_alarm():
    clock, provider, service, _, job = configured("htf_rsi_score", all_timeframes=True)
    service.process(*service._next_job())
    witness(service, job, clock)
    service.live._connection = SimpleNamespace(connected=True)
    service.tracker_snapshot("tab", job[0], [job[1]], ["1D", "15m"])
    existing = len(provider.calls)
    service._sync_live()
    service._tracker_history_step()
    assert len(provider.calls) == existing
    assert (*job[:2], "1D") in service.tracker.seeds
    state = service.publication_token(job[:2])
    service.live.enqueue({"kind": "rejected", "key": (*job[:2], "15")})
    service.live.process_event()
    assert service.publication_token(job[:2]) == state
    assert (*job[:2], "15") in service.live._refused
    assert service.live.has_seed(job, provider.generation)
    clock[0] += 16
    service._sync_live()
    assert not service.live._tracker_wanted and not service.tracker.seeds
    assert service.live.admitted(job)


def test_rollover_commits_only_the_provider_close():
    bars = native_bars(frame(count=22), "1D", "BIST", NOW)
    seed = TrackerSeed.build(bars, 1, NOW)
    closed = replace(seed.current, close=190)
    current = replace(closed, time=closed.time + 86400)
    rolled = seed.advance(closed, current)
    result = rolled.state.value(130)
    expected = rsi_values([*(bar.close for bar in bars[:-1]), 190, 130], 14)[-1]
    assert result == pytest.approx(expected)
    assert rolled.advance(closed, current) is None


def test_private_route_rejects_unauthorized_or_excess_demand(monkeypatch, api_auth_users):
    app = FastAPI()
    app.include_router(router)
    calls = []

    def snapshot(*args):
        calls.append(args)
        return {"rows": {}}

    monkeypatch.setattr(
        advanced_alarm_market_data,
        "get_advanced_market_data",
        lambda: SimpleNamespace(custom=SimpleNamespace(tracker_snapshot=snapshot)),
    )
    path = "/borsapy/market/rsi-tracker"
    payload = {
        "view": "test-view-12345678",
        "market": "BIST",
        "symbols": ["THYAO"],
        "periods": ["2M"],
    }
    with TestClient(app) as client:
        assert client.post(path, json=payload).status_code == 401
        client.headers["Authorization"] = "Bearer " + api_auth_users.create_access_token(
            {"sub": "user"}
        )
        assert client.post(path, json=payload).status_code == 403
        client.headers["Authorization"] = "Bearer " + api_auth_users.create_access_token(
            {"sub": "admin"}
        )
        assert (
            client.post(path, json={**payload, "symbols": ["THYAO", "GARAN", "AKBNK"]}).status_code
            == 422
        )
        assert client.post(path, json={**payload, "periods": ["60d"]}).status_code == 422
        assert client.post(path, json={**payload, "symbols": ["NOTREAL"]}).status_code == 422
        assert calls == []
        response = client.post(path, json=payload)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "private, no-store"
        assert calls == [(("admin", payload["view"]), "BIST", ["THYAO"], ["2M"])]
