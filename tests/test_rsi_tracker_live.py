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
from application.services.rsi_tracker import (
    DISPLAY_SECONDS,
    DISPLAY_SYMBOLS,
    LEASE_SECONDS,
    MAX_TRACKER_SYMBOLS,
    NATIVE_TIMEFRAMES,
    TrackerSeed,
)
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
    seed = service.tracker.seeds[(*job[:2], "1D")]
    clock[0] += 120
    service._sync_live()
    assert service.tracker.seeds[(*job[:2], "1D")] is seed
    service.tracker_snapshot("tab", job[0], [job[1]], ["1D", "15m"])
    clock[0] += LEASE_SECONDS + 1
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


def test_display_survives_lease_and_reconnect_without_fabricating_live_rsi():
    clock = [NOW + 0.2]
    service = CustomIndicatorData(provider=Provider(), clock=lambda: clock[0])
    member = ("BIST", "THYAO")
    key = (*member, "1D")
    service.tracker_snapshot("first", "BIST", ["THYAO"], ["1D"])
    service._sync_live()
    service.live._connection = SimpleNamespace(connected=True)
    bars = native_bars(frame(count=22), "1D", "BIST", clock[0])
    service.live._buckets[key] = (bars[-2:], clock[0])
    service.tracker.install(key, TrackerSeed.build(bars, 1, clock[0]))
    expected = rsi_values([bar.close for bar in bars], 14)[-1]
    quote(service, member, clock, 165)

    clock[0] += LEASE_SECONDS + 1
    service._sync_live()
    assert not service.tracker.seeds and not service.tracker.rows
    response = service.tracker_snapshot("second", "BIST", ["THYAO", "GARAN"], ["1D"])
    assert response["snapshot_version"] == 2
    saved = response["rows"]["THYAO"]
    assert saved["price"] is None and saved["last_price"]["value"] == 165
    cell = saved["cells"]["1D"]
    assert cell["status"] == "waiting" and cell["value"] is None
    assert cell["last"] == {
        "kind": "candle",
        "bar_time": bars[-1].time,
        "received_at": NOW + 0.2,
        "value": pytest.approx(expected),
    }
    assert "last" not in response["rows"]["GARAN"]["cells"]["1D"]
    service._wake.clear()
    service.tracker_snapshot("second", "BIST", ["THYAO", "GARAN"], ["1D"])
    assert not service._wake.is_set()
    assert not service.provider.calls

    quote_only = service.tracker_snapshot("second", "Kripto", ["THYAO"], ["1D"])["rows"]["THYAO"]
    assert "last_price" not in quote_only and "last" not in quote_only["cells"]["1D"]
    clock[0] += DISPLAY_SECONDS
    expired = service.tracker_snapshot("third", "BIST", ["THYAO"], ["1D"])["rows"]["THYAO"]
    assert "last_price" not in expired and "last" not in expired["cells"]["1D"]


def test_display_only_labels_witnessed_rollover_closed_and_is_bounded():
    clock = [NOW + 0.2]
    service = CustomIndicatorData(provider=Provider(), clock=lambda: clock[0])
    key = ("BIST", "THYAO", "1D")
    bars = native_bars(frame(count=22), "1D", "BIST", clock[0])
    seed = TrackerSeed.build(bars, 1, clock[0])
    service.tracker.install(key, seed)
    closed = replace(bars[-1], close=190)
    service.advance_tracker(key, closed, replace(closed, time=closed.time + 86400))
    service.tracker.install(key, seed)
    snapshot = service.tracker_snapshot("view", "BIST", ["THYAO"], ["1D"])
    last = snapshot["rows"]["THYAO"]["cells"]["1D"]["last"]
    assert last["kind"] == "closed"
    assert last["value"] == pytest.approx(seed.state.value(190))

    service.provider.generation += 1
    snapshot = service.tracker_snapshot("view", "BIST", ["THYAO"], ["1D"])
    assert "last" not in snapshot["rows"]["THYAO"]["cells"]["1D"]
    for index in range(DISPLAY_SYMBOLS):
        service.tracker.install(("Kripto", f"COIN{index}USDT", "1D"), seed)
    assert len(service.tracker.display) == DISPLAY_SYMBOLS
    assert key[:2] not in service.tracker.display


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
            client.post(path, json={**payload, "symbols": [f"S{i}" for i in range(26)]}).status_code
            == 422
        )
        assert client.post(path, json={**payload, "periods": ["60d"]}).status_code == 422
        assert client.post(path, json={**payload, "symbols": ["NOTREAL"]}).status_code == 422
        assert calls == []
        response = client.post(path, json=payload)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "private, no-store"
        assert calls == [(("admin", payload["view"]), "BIST", ["THYAO"], ["2M"])]


def test_full_page_demand_is_shared_bounded_and_released_without_provider_io():
    clock = [NOW + 0.2]
    provider = Provider()
    service = CustomIndicatorData(provider=provider, clock=lambda: clock[0])
    symbols = [f"COIN{i}USDT" for i in range(MAX_TRACKER_SYMBOLS)]
    periods = tuple(NATIVE_TIMEFRAMES)
    service.tracker_snapshot("first", "Kripto", symbols, periods)
    service._sync_live()
    assert len(service.live._tracker_wanted) == 25 * 16
    assert not service.live._tracker_refused
    assert provider.calls == []
    service.tracker_snapshot("shared", "Kripto", symbols, periods)
    service._sync_live()
    assert len(service.live._tracker_wanted) == 400
    blocked = service.tracker_snapshot("overflow", "Kripto", ["OTHERUSDT"], periods)
    assert {cell["status"] for cell in blocked["rows"]["OTHERUSDT"]["cells"].values()} == {
        "capacity"
    }
    service.tracker_snapshot("first", "Kripto", [], periods)
    service.tracker_snapshot("shared", "Kripto", [], periods)
    service._sync_live()
    assert len(service.live._tracker_wanted) == 16
    clock[0] += LEASE_SECONDS + 1
    service._sync_live()
    assert not service.live._tracker_wanted
    assert not provider.calls


def test_full_page_fits_alongside_631_alarm_symbols_without_moving_them():
    from application.services.bist_share_universe import share_universe
    from infrastructure.providers.custom_indicator_leases import persistent_keys
    from infrastructure.providers.custom_indicator_stream import (
        MAX_LIVE_SERIES,
        plan_native_subscriptions,
    )

    alarm_periods = [*(f"{n}D" for n in range(1, 7)), "1W", "2W", "3W", "1M"]
    alarms = {("BIST", symbol, tf) for symbol in share_universe().symbols for tf in alarm_periods}
    _, old_slots, refused = plan_native_subscriptions(alarms)
    assert not refused
    tracker = {
        ("Kripto", f"COIN{i}USDT", tf) for i in range(25) for tf in NATIVE_TIMEFRAMES.values()
    }
    groups, new_slots, refused = plan_native_subscriptions(alarms | tracker, old_slots)
    assert not refused
    assert len(alarms | tracker) <= MAX_LIVE_SERIES
    assert all(new_slots[member] == slot for member, slot in old_slots.items())
    assert all(len(persistent_keys(keys)) + 32 <= 500 for keys in groups.values())
