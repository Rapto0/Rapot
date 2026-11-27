"""Closed history prepared without demand and read across an API restart."""

import asyncio
import json
import sqlite3
from contextlib import closing
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.borsapy_market_routes import router
from api.runtime import tracker_history
from application.services import advanced_alarm_market_data
from application.services.bist_share_universe import share_universe
from application.services.custom_indicators.core import rsi_values
from application.services.rsi_tracker import NATIVE_TIMEFRAMES
from infrastructure.persistence import rsi_tracker_history as history

NOW = 1_795_777_200
SOURCE = "licensed-fixture"


def series(symbol="THYAO", period="1D", market="BIST", count=240, end=NOW - 1, adjustment="raw"):
    bars = [
        [end - (count - index) * 60, end - (count - index - 1) * 60, 90 + (index * 3) % 13]
        for index in range(count)
    ]
    return {
        "market": market,
        "symbol": symbol,
        "period": period,
        "adjustment": adjustment,
        "complete": True,
        "bars": bars,
    }


def pack(path, rows, revision=1, source=SOURCE):
    data = [{"version": 1, "source": source, "revision": revision}, *rows]
    temporary = path.with_suffix(".tmp")
    temporary.write_text("".join(json.dumps(row) + "\n" for row in data), encoding="utf-8")
    temporary.replace(path)


def empty_snapshot(symbols, periods=("1D",), status="waiting", now=NOW):
    return {
        "snapshot_version": 2,
        "observed_at": now,
        "rows": {
            symbol: {
                "cells": {period: {"value": None, "status": status} for period in periods},
                "price": None,
                "source_time": None,
            }
            for symbol in symbols
        },
    }


def test_400_cells_are_ready_on_first_read_after_restart_and_independent_restore(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(history, "time", lambda: NOW)
    symbols = share_universe().symbols[:25]
    members = history.pilot_members(",".join(f"BIST:{symbol}" for symbol in symbols))
    worker = history.TrackerHistory(tmp_path, SOURCE, members)
    pack(
        worker.inbox, [series(symbol, period) for symbol in symbols for period in NATIVE_TIMEFRAMES]
    )
    worker.refresh()

    first = history.TrackerHistory(tmp_path, SOURCE, members)
    first.inbox.unlink()
    first.load()
    saved = first.enrich(empty_snapshot(symbols, NATIVE_TIMEFRAMES, now=NOW + 180), "BIST")
    assert saved["closed_source"] == SOURCE
    assert len(saved["rows"]) == 25
    cells = [cell for row in saved["rows"].values() for cell in row["cells"].values()]
    expected = rsi_values([bar[2] for bar in series()["bars"]], 14)[-1]
    assert len(cells) == 400
    assert all(cell["status"] == "waiting" and cell["value"] is None for cell in cells)
    assert cells[0]["last"]["value"] == pytest.approx(expected)
    assert all(
        cell["last"]["kind"] == "closed" and cell["last"]["bar_end"] == NOW - 1 for cell in cells
    )

    (tmp_path / "restore").mkdir()
    restored = history.TrackerHistory(tmp_path / "restore", SOURCE, members)
    with (
        closing(sqlite3.connect(first.path)) as original,
        closing(sqlite3.connect(restored.path)) as copy,
    ):
        original.backup(copy)
        assert copy.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    restored.load()
    assert (
        restored.enrich(empty_snapshot(symbols, NATIVE_TIMEFRAMES, now=NOW + 180), "BIST") == saved
    )
    assert first.path.stat().st_size < 128 * 1024


def test_bad_batch_or_older_revision_cannot_replace_last_good_values(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "time", lambda: NOW)
    cache = history.TrackerHistory(tmp_path, SOURCE, history.pilot_members("BIST:THYAO,BIST:GARAN"))
    pack(cache.inbox, [series(), series("GARAN")], revision=3)
    cache.refresh()
    original = cache.enrich(empty_snapshot(["THYAO", "GARAN"]), "BIST")

    for invalid, revision, source in [
        ([series(end=NOW - 120)], 2, SOURCE),
        ([series(end=NOW - 120)], 3, SOURCE),
        ([series(), series(end=NOW + 120)], 4, SOURCE),
        ([series(), series()], 4, SOURCE),
        ([series(), series("ASELS")], 4, SOURCE),
        ([series()], 4, "foreign-source"),
        ([], 4, SOURCE),
        ([series(end=NOW - 120)], 4, SOURCE),
    ]:
        pack(cache.inbox, invalid, revision=revision, source=source)
        cache.refresh()
        assert cache.enrich(empty_snapshot(["THYAO", "GARAN"]), "BIST") == original

    changed = series(adjustment="split")
    changed["bars"][-1][2] = 555
    pack(cache.inbox, [changed], revision=5)
    cache.refresh()
    updated = cache.enrich(empty_snapshot(["THYAO", "GARAN"]), "BIST")["rows"]
    assert updated["THYAO"]["cells"]["1D"]["last"]["adjustment"] == "split"
    assert (
        updated["THYAO"]["cells"]["1D"]["last"]["value"]
        != original["rows"]["THYAO"]["cells"]["1D"]["last"]["value"]
    )
    assert "last_price" not in updated["THYAO"]
    assert updated["GARAN"] == original["rows"]["GARAN"]


def test_closed_data_never_overwrites_live_or_crosses_market_source_or_expiry(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(history, "time", lambda: NOW)
    members = history.pilot_members("BIST:THYAO,Kripto:BTCUSDT")
    cache = history.TrackerHistory(tmp_path, SOURCE, members)
    crypto = series("BTCUSDT", market="Kripto", count=9)
    broken = series("BTCUSDT", market="Kripto")
    broken["bars"].pop(2)
    pack(cache.inbox, [series(), broken])
    cache.refresh()
    assert not cache.path.exists()
    pack(cache.inbox, [series(), crypto])
    cache.refresh()
    opening = cache.enrich(empty_snapshot(["BTCUSDT"]), "Kripto")["rows"]["BTCUSDT"]
    assert opening["cells"]["1D"]["closed_status"] == "insufficient"
    assert opening["last_price"]["kind"] == "closed"
    assert "last" not in opening["cells"]["1D"]

    live = empty_snapshot(["THYAO"], status="ready")
    live["rows"]["THYAO"].update(price=110, source_time=NOW)
    live["rows"]["THYAO"]["cells"]["1D"]["value"] = 25
    assert cache.enrich(live, "BIST")["rows"]["THYAO"]["cells"]["1D"] == {
        "status": "ready",
        "value": 25,
    }
    wrong_market = empty_snapshot(["THYAO"])
    assert "closed_source" not in cache.enrich(wrong_market, "Kripto")
    wrong_source = history.TrackerHistory(tmp_path, "other-source", members)
    wrong_source.load()
    assert "closed_source" not in wrong_source.enrich(empty_snapshot(["THYAO"]), "BIST")
    expiry = empty_snapshot(["THYAO"], now=NOW + history.DISPLAY_SECONDS + 1)
    assert "closed_source" not in cache.enrich(expiry, "BIST")


@pytest.mark.asyncio
async def test_worker_applies_pack_without_any_http_view_and_loads_it_before_startup_yield(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(history, "time", lambda: NOW)
    monkeypatch.setattr(tracker_history, "REFRESH_SECONDS", 0.01)
    parent = SimpleNamespace(state=SimpleNamespace())
    settings = SimpleNamespace(
        cache_database_path=str(tmp_path / "price_cache.db"),
        rsi_tracker_history_source=SOURCE,
        rsi_tracker_history_symbols="BIST:THYAO",
    )
    async with tracker_history.tracker_history_runtime(parent, settings):
        cache = parent.state.rsi_tracker_history
        pack(cache.inbox, [series()])
        async with asyncio.timeout(5):
            while "closed_source" not in cache.enrich(empty_snapshot(["THYAO"]), "BIST"):
                await asyncio.sleep(0.01)
    cache.inbox.unlink()
    async with tracker_history.tracker_history_runtime(parent, settings):
        assert (
            parent.state.rsi_tracker_history.enrich(empty_snapshot(["THYAO"]), "BIST")[
                "closed_source"
            ]
            == SOURCE
        )
    assert parent.state.rsi_tracker_history is None


def test_private_tracker_route_includes_closed_result_only_on_authenticated_read(
    tmp_path, monkeypatch, api_auth_users
):
    monkeypatch.setattr(history, "time", lambda: NOW)
    app = FastAPI()
    app.include_router(router)
    members = history.pilot_members("BIST:THYAO")
    cache = history.TrackerHistory(tmp_path, SOURCE, members)
    pack(cache.inbox, [series()])
    cache.refresh()
    cache.inbox.unlink()
    reopened = history.TrackerHistory(tmp_path, SOURCE, members)
    reopened.load()
    app.state.rsi_tracker_history = reopened
    custom = SimpleNamespace(
        tracker_snapshot=lambda _, market, symbols, periods: empty_snapshot(symbols, periods)
    )
    monkeypatch.setattr(
        advanced_alarm_market_data,
        "get_advanced_market_data",
        lambda: SimpleNamespace(custom=custom),
    )
    body = {
        "view": "tracker-history-test",
        "market": "BIST",
        "symbols": ["THYAO"],
        "periods": ["1D"],
    }
    route = "/borsapy/market/rsi-tracker"
    with TestClient(app) as client:
        assert client.post(route, json=body).status_code == 401
        client.headers["Authorization"] = "Bearer " + api_auth_users.create_access_token(
            {"sub": "admin"}
        )
        response = client.post(route, json=body)
        assert response.status_code == 200 and "no-store" in response.headers["Cache-Control"]
        assert response.json()["rows"]["THYAO"]["cells"]["1D"]["last"]["source"] == SOURCE
