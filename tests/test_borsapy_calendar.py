"""Offline calendar auth, bounded concurrency, freshness and source semantics."""

import inspect
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import calendar_service as module
from api.routes import calendar_routes as routes
from application.services.borsapy_gateway import BorsapyGatewayError


@pytest.fixture
def clock(monkeypatch):
    current = [datetime(2026, 10, 4, 12, tzinfo=UTC)]
    monkeypatch.setattr(module, "_utc_now", lambda: current[0])
    return current


@pytest.fixture
def source(monkeypatch, clock):
    import borsapy

    state = {
        "calls": [],
        "frame": pd.DataFrame(
            [
                {
                    "Date": pd.Timestamp("2026-10-04"),
                    "Time": "9:30",
                    "Country": "Türkiye",
                    "Importance": "mid",
                    "Event": "Enflasyon",
                    "Actual": "64.77%",
                    "Forecast": None,
                    "Previous": 0,
                }
            ]
        ),
    }

    def events(**kwargs):
        inspect.signature(borsapy.EconomicCalendar.events).bind(None, **kwargs)
        state["calls"].append(kwargs)
        if "block" in state:
            state["entered"].set()
            assert state["block"].wait(3)
        if "error" in state:
            raise state["error"]
        return state["frame"].copy()

    def run_public(callback):
        return callback(SimpleNamespace(EconomicCalendar=lambda: SimpleNamespace(events=events)))

    monkeypatch.setattr(
        module, "get_borsapy_gateway", lambda: SimpleNamespace(run_public=run_public)
    )
    return state


def test_preserves_strings_null_zero_mid_and_unzoned_source_time(source):
    service = module.CalendarService()
    payload = service.get_economic_calendar("2026-10-04", "2026-10-06")
    event = payload["events"][0]
    assert event["actual"] == "64.77%"
    assert event["estimate"] is None
    assert event["previous"] == 0
    assert event["impact"] == "mid"
    assert event["source_time"] == "09:30"
    assert event["date"] == "2026-10-04"
    assert event["time"] is event["timestamp"] is None
    assert payload["meta"]["source_timezone"] is None
    assert payload["meta"]["fetched_at"] == "2026-10-04T12:00:00Z"
    assert payload["meta"]["provider_cache_seconds"] == 3600
    assert source["calls"] == [
        {"start": "2026-10-04", "end": "2026-10-06", "country": ["TR", "US"], "importance": None}
    ]


@pytest.mark.parametrize("value", [None, "", "Açıklanacak", "25:00"])
def test_unknown_event_clock_does_not_discard_event(source, value):
    source["frame"].loc[0, "Time"] = value
    result = module.CalendarService().get_economic_calendar()
    assert len(result["events"]) == 1
    assert result["events"][0]["source_time"] is None


def test_range_filters_rows_and_preserves_last_day(source):
    source["frame"] = pd.concat([source["frame"]] * 3, ignore_index=True)
    source["frame"]["Date"] = pd.to_datetime(["2026-10-03", "2026-10-06", "2026-10-07"])
    result = module.CalendarService().get_economic_calendar("2026-10-04", "2026-10-06")
    assert [event["date"] for event in result["events"]] == ["2026-10-06"]


@pytest.mark.parametrize(
    "params",
    [
        {"from_date": "20261004"},
        {"from_date": "bad"},
        {"from_date": "2026-09-26"},
        {"to_date": "2026-11-04"},
        {"from_date": "2026-10-05", "to_date": "2026-10-04"},
        {"from_date": "2026-09-27", "to_date": "2026-10-31"},
        {"country": "TR,US,GB,DE"},
        {"country": "ZZ"},
        {"importance": "critical"},
    ],
)
def test_invalid_or_unbounded_input_never_calls_provider(source, params):
    with pytest.raises(BorsapyGatewayError) as error:
        module.CalendarService().get_economic_calendar(**params)
    assert error.value.status_code == 422
    assert source["calls"] == []


def test_default_day_uses_istanbul_across_utc_midnight(source, clock):
    clock[0] = datetime(2026, 10, 4, 22, 30, tzinfo=UTC)
    result = module.CalendarService().get_economic_calendar()
    assert result["meta"]["from_date"] == "2026-10-05"
    assert result["meta"]["to_date"] == "2026-10-19"


def test_cache_copy_expiry_stale_failure_cooldown_and_hard_limit(source, clock):
    service = module.CalendarService()
    service.cache_ttl_seconds = 60
    first = service.get_economic_calendar()
    first["events"].clear()
    clock[0] += timedelta(seconds=59)
    cached = service.get_economic_calendar()
    assert len(cached["events"]) == 1
    assert cached["meta"]["cache_hit"] is True
    clock[0] += timedelta(seconds=1)
    source["error"] = RuntimeError("synthetic-secret-provider-error")
    stale = service.get_economic_calendar()
    assert stale["meta"]["state"] == "stale"
    assert stale["meta"]["fetched_at"] == cached["meta"]["fetched_at"]
    assert "synthetic-secret" not in str(stale)
    assert service.get_economic_calendar()["meta"]["state"] == "stale"
    assert len(source["calls"]) == 2
    clock[0] += timedelta(seconds=service.stale_seconds)
    with pytest.raises(BorsapyGatewayError, match="Takvim kaynağına erişilemedi"):
        service.get_economic_calendar()
    assert len(source["calls"]) == 3


def test_successful_empty_differs_from_failure_and_invalid_shape(source):
    source["frame"] = source["frame"].iloc[:0]
    assert module.CalendarService().get_economic_calendar()["meta"]["state"] == "empty"
    source["frame"] = pd.DataFrame([{"wrong": "schema"}])
    with pytest.raises(BorsapyGatewayError, match="alanları"):
        module.CalendarService().get_economic_calendar()
    source["error"] = RuntimeError("private-error")
    with pytest.raises(BorsapyGatewayError, match="Takvim kaynağına erişilemedi"):
        module.CalendarService().get_economic_calendar()


def test_overlapping_identical_requests_share_one_fetch_and_other_keys_are_bounded(source):
    service = module.CalendarService()
    source["block"], source["entered"] = threading.Event(), threading.Event()
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(service.get_economic_calendar)
        assert source["entered"].wait(2)
        second = pool.submit(service.get_economic_calendar)
        with pytest.raises(BorsapyGatewayError) as error:
            service.get_economic_calendar(country="DE")
        assert error.value.status_code == 503
        source["block"].set()
        assert first.result(timeout=3)["events"] == second.result(timeout=3)["events"]
    assert len(source["calls"]) == 1


def test_cache_lru_is_bounded_and_country_order_is_canonical(source):
    service = module.CalendarService()
    service.max_cache_entries = 2
    service.get_economic_calendar(country="US,TR")
    service.get_economic_calendar(country="TR,US")
    service.get_economic_calendar(country="DE")
    service.get_economic_calendar(country="FR")
    assert len(service._cache) == 2
    assert len(source["calls"]) == 3
    service.get_economic_calendar(country="TR,US")
    assert len(source["calls"]) == 4


@pytest.fixture
def client(api_auth_users, monkeypatch, source):
    app = FastAPI()
    app.include_router(routes.router)
    monkeypatch.setattr(routes, "calendar_service", module.CalendarService())
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("path", ["/calendar", "/api/calendar"])
def test_both_aliases_require_admin_and_never_cache_private_responses(
    client, api_auth_users, source, path
):
    for username, status in [(None, 401), ("user", 403), ("admin", 200)]:
        headers = (
            {}
            if username is None
            else {
                "Authorization": "Bearer " + api_auth_users.create_access_token({"sub": username})
            }
        )
        response = client.get(path, headers=headers)
        assert response.status_code == status
        assert response.headers["Cache-Control"] == "private, no-store"
        if status == 200:
            assert response.json()["meta"]["source"] == "borsapy_dovizcom"
        else:
            assert not source["calls"]


def test_validation_and_provider_failures_are_private_and_do_not_leak(
    client, api_auth_users, source
):
    client.headers["Authorization"] = "Bearer " + api_auth_users.create_access_token(
        {"sub": "admin"}
    )
    bad = client.get("/calendar?country=TR,US,GB,DE")
    assert bad.status_code == 422
    assert bad.headers["Cache-Control"] == "private, no-store"
    source["error"] = RuntimeError("sensitive-provider-response")
    failed = client.get("/calendar")
    assert failed.status_code == 502
    assert failed.headers["Cache-Control"] == "private, no-store"
    assert "sensitive" not in failed.text


def _day_html(day, title, clock="15:30"):
    return (
        f'<div class="text-center mt-8 mb-8 text-bold">{day} Ekim 2026</div>'
        '<div class="table-wrapper"><table><tr><th>Saat</th></tr><tr>'
        f'<td>{clock}</td><td>ABD</td><td><span class="importance high"></span></td>'
        f"<td>{title}</td><td>0</td><td></td><td>1</td></tr></table></div>"
    )


@pytest.fixture
def dated_provider(monkeypatch):
    monkeypatch.setattr(module, "_calendar_provider", None)
    provider = module._dated_calendar_provider()
    yield provider
    provider.close()


def test_real_provider_week_month_blocks_use_each_day_and_deduplicate(dated_provider):
    from borsapy._providers.dovizcom_calendar import DovizcomCalendarProvider

    html = (
        '<div id="calendar-content-0">'
        + _day_html("07", "Petrol stokları", "17:30")
        + '</div><div id="calendar-content-2">'
        + _day_html("05", "Önceki olay")
        + _day_html("07", "Petrol stokları", "17:30")
        + '</div><div id="calendar-content-3">'
        + _day_html("01", "Ay başı")
        + _day_html("02", "İstihdam")
        + _day_html("14", "TÜFE")
        + "</div>"
    )
    old = DovizcomCalendarProvider._parse_html(dated_provider, html, "US")
    assert next(event for event in old if event["event"] == "TÜFE")["date"].day == 1
    events = dated_provider._parse_html(html, "US")
    assert {event["event"]: event["date"].day for event in events} == {
        "Petrol stokları": 7,
        "Önceki olay": 5,
        "Ay başı": 1,
        "İstihdam": 2,
        "TÜFE": 14,
    }
    assert len(events) == 5
    assert all(event["date"].tzinfo is None for event in events)


def test_real_calendar_date_filter_keeps_future_day_without_mutating_upstream(
    dated_provider, monkeypatch, clock
):
    import borsapy
    from borsapy._providers.dovizcom_calendar import get_calendar_provider

    upstream = get_calendar_provider()
    html = '<div id="calendar-content-3">' + _day_html("01", "Ay başı")
    html += _day_html("14", "TÜFE") + "</div>"
    calls = []

    def get(url, **kwargs):
        calls.append(kwargs["params"])
        return SimpleNamespace(json=lambda: {"calendarHTML": html})

    monkeypatch.setattr(dated_provider, "_get", get)
    monkeypatch.setattr(
        module,
        "get_borsapy_gateway",
        lambda: SimpleNamespace(run_public=lambda callback: callback(borsapy)),
    )
    result = module.CalendarService().get_economic_calendar(
        "2026-10-07", "2026-10-21", country="US"
    )
    assert [(e["date"], e["source_time"]) for e in result["events"]] == [("2026-10-14", "15:30")]
    assert result["events"][0]["timestamp"] is None
    assert result["meta"]["source_timezone"] is None
    assert calls == [{"country": "US", "importance": "3,2,1"}]
    assert borsapy.EconomicCalendar()._provider is upstream
    assert dated_provider._cache is not upstream._cache


@pytest.mark.parametrize(
    "html",
    [
        "<div>Unexpected page</div>",
        '<div id="calendar-content-0"><table><tr><td>orphan</td></tr></table></div>',
        '<div id="calendar-content-0">'
        + _day_html("07", "Known day")
        + _day_html("INVALID", "Must not inherit previous day")
        + "</div>",
        "x" * 2_000_001,
    ],
    ids=["missing-container", "missing-day", "invalid-next-day", "oversized"],
)
def test_invalid_calendar_structure_fails_instead_of_assigning_a_day(dated_provider, html):
    with pytest.raises(ValueError):
        dated_provider._parse_html(html, "US")


def test_calendar_parse_cache_is_bounded_copy_safe_and_expires(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(module.time, "monotonic", lambda: now[0])
    cache = module._CalendarCache()
    for index in range(17):
        cache.set(str(index), [{"value": index}], 3600)
    assert len(cache._entries) == 16 and cache.get("0") is None
    copy = cache.get("1")
    copy[0]["value"] = 99
    assert cache.get("1") == [{"value": 1}]
    now[0] += 3600
    assert cache.get("1") is None


def test_period_only_research_calendar_uses_istanbul_day(clock):
    clock[0] = datetime(2026, 10, 7, 22, 30, tzinfo=UTC)
    calls = []

    def events(**kwargs):
        calls.append(kwargs)
        return pd.DataFrame()

    bp = SimpleNamespace(EconomicCalendar=lambda: SimpleNamespace(events=events))
    module.calendar_events(bp, period="1w", country="US")
    assert calls == [{"period": "1w", "country": "US", "start": "2026-10-08"}]


def test_source_clocks_across_us_dst_are_preserved_without_claiming_timezone(source, clock):
    clock[0] = datetime(2026, 11, 1, 12, tzinfo=UTC)
    source["frame"] = pd.DataFrame(
        [
            {"Date": day, "Time": time, "Country": "ABD", "Event": "Synthetic release"}
            for day, time in [("2026-10-30", "15:30"), ("2026-11-06", "16:30")]
        ]
    )
    result = module.CalendarService().get_economic_calendar("2026-10-30", "2026-11-06")
    assert [(e["date"], e["source_time"]) for e in result["events"]] == [
        ("2026-10-30", "15:30"),
        ("2026-11-06", "16:30"),
    ]
    assert all(e["time"] is e["timestamp"] is None for e in result["events"])
    assert result["meta"]["source_timezone"] is None
