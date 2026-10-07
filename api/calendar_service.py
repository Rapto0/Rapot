"""Bounded private borsapy calendar; source event time zones are never inferred."""

import hashlib
import math
import re
import threading
import time
from collections import OrderedDict
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from html import escape
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from application.services.borsapy_gateway import BorsapyGatewayError, get_borsapy_gateway
from settings import settings

COUNTRIES = frozenset({"TR", "US", "EU", "DE", "GB", "JP", "CN", "FR", "IT", "CA", "AU", "CH"})
ISTANBUL = ZoneInfo("Europe/Istanbul")
CalendarKey = tuple[date, date, tuple[str, ...], str]
WARNINGS = [
    "Borsapy / Doviz.com yalnız yayımlanmış olayları döndürür; boş sonuç olay olmadığı kanıtı değildir.",
    "Olay saatlerinin kaynak saat dilimi doğrulanmamıştır; UTC veya İstanbul saatine çevrilmemiştir.",
    "Sağlayıcı önbelleği 1 saattir. Alınma zamanı yeni bir kaynak güncellemesi anlamına gelmez.",
]


class _CalendarCache:
    """Separate, bounded parsed-data cache; never reuse the upstream parser's entries."""

    def __init__(self) -> None:
        self._entries: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Any:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry[0] <= time.monotonic():
                self._entries.pop(key)
                return None
            self._entries.move_to_end(key)
            return deepcopy(entry[1])

    def set(self, key: str, value: Any, ttl: int) -> None:
        with self._lock:
            self._entries[key] = (time.monotonic() + ttl, deepcopy(value))
            self._entries.move_to_end(key)
            while len(self._entries) > 16:
                self._entries.popitem(last=False)


_calendar_provider: Any = None
_calendar_provider_lock = threading.Lock()


def _dated_calendar_provider() -> Any:
    """Fix borsapy 0.11's first-heading-per-tab parser without changing its globals."""
    global _calendar_provider
    with _calendar_provider_lock:
        if _calendar_provider is not None:
            return _calendar_provider
        from borsapy._providers.dovizcom_calendar import DovizcomCalendarProvider
        from bs4 import BeautifulSoup

        class DatedCalendarProvider(DovizcomCalendarProvider):
            def _parse_html(self, html_content: str, country_code: str) -> list[dict[str, Any]]:
                if not isinstance(html_content, str) or len(html_content) > 2_000_000:
                    raise ValueError("Calendar HTML exceeds the supported size")
                soup = BeautifulSoup(html_content, "html.parser")
                containers = soup.find_all(
                    "div", id=lambda value: value and value.startswith("calendar-content-")
                )
                if not containers:
                    raise ValueError("Calendar day containers are missing")
                events = []
                for container in containers:
                    header, rows = None, []

                    def flush(header: Any, rows: list[Any]) -> None:
                        if not rows:
                            return
                        if header is None or self._parse_turkish_date(header.get_text()) is None:
                            raise ValueError("Calendar event rows have no valid day heading")
                        # The original parser now sees exactly one explicit day per fragment.
                        fragment = (
                            '<div id="calendar-content-rapot">'
                            + '<div class="text-center mt-8 mb-8 text-bold">'
                            + escape(header.get_text(strip=True))
                            + "</div>"
                            + "<table>"
                            + "".join(map(str, rows))
                            + "</table></div>"
                        )
                        events.extend(
                            super(DatedCalendarProvider, self)._parse_html(fragment, country_code)
                        )

                    for node in container.find_all(["div", "tr"]):
                        if (
                            node.find_parent(
                                "div",
                                id=lambda value: value and value.startswith("calendar-content-"),
                            )
                            is not container
                        ):
                            continue
                        if node.name == "div" and {
                            "text-center",
                            "mt-8",
                            "mb-8",
                            "text-bold",
                        } <= set(node.get("class", [])):
                            flush(header, rows)
                            header, rows = node, []
                        elif node.name == "tr" and node.find_all("td"):
                            rows.append(node)
                    flush(header, rows)
                # Today/week/month views repeat events; preserve the first source occurrence.
                unique = {}
                for event in events:
                    identity = (event["date"], event["time"], event["country_code"], event["event"])
                    unique.setdefault(identity, event)
                return list(unique.values())

        _calendar_provider = DatedCalendarProvider(cache=_CalendarCache())
        return _calendar_provider


def calendar_events(bp: Any, **kwargs: Any) -> pd.DataFrame:
    """Use native borsapy fields/filtering with each HTML table's actual day heading."""
    from borsapy._providers.dovizcom_calendar import DovizcomCalendarProvider

    if kwargs.get("start") is None:
        kwargs["start"] = _utc_now().astimezone(ISTANBUL).date().isoformat()
    calendar = bp.EconomicCalendar()
    if isinstance(getattr(calendar, "_provider", None), DovizcomCalendarProvider):
        calendar._provider = _dated_calendar_provider()
    return calendar.events(**kwargs)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _text(value: Any, limit: int = 300) -> str | None:
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    return str(value).strip()[:limit] or None


def _metric(value: Any) -> int | float | str | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        return value[:128] or None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _normalize(frame: pd.DataFrame, start: date, end: date) -> tuple[list[dict], int]:
    if not isinstance(frame, pd.DataFrame) or len(frame) > 1000:
        raise BorsapyGatewayError("Takvim yanıtı geçersiz veya çok büyük.", 502)
    if frame.empty:
        return [], 0
    if not {"Date", "Event", "Country"}.issubset(frame.columns):
        raise BorsapyGatewayError("Takvim yanıtı beklenen alanları içermiyor.", 502)
    events, dropped, seen = [], 0, set()
    for row in frame.to_dict("records"):
        try:
            day = pd.Timestamp(row["Date"])
            if pd.isna(day) or day.tzinfo is not None:
                raise ValueError
            day = day.date()
        except (TypeError, ValueError):
            dropped += 1
            continue
        if not start <= day <= end:
            continue
        title = _text(row.get("Event"))
        if not title:
            dropped += 1
            continue
        clock = _text(row.get("Time"), 16)
        if clock and re.fullmatch(r"\d{1,2}:\d{2}(?::00)?", clock):
            hour, minute = map(int, clock.split(":")[:2])
            clock = f"{hour:02d}:{minute:02d}" if hour < 24 and minute < 60 else None
        else:
            clock = None
        country = _text(row.get("Country"), 64)
        identity = "|".join((day.isoformat(), clock or "", country or "", title))
        event_id = hashlib.sha256(identity.encode()).hexdigest()[:24]
        if event_id in seen:
            continue
        seen.add(event_id)
        impact = _text(row.get("Importance"), 16)
        events.append(
            {
                "id": event_id,
                "date": day.isoformat(),
                "source_time": clock,
                "time": None,
                "timestamp": None,
                "country": country,
                "event": title,
                "impact": impact if impact in {"low", "mid", "high"} else None,
                "actual": _metric(row.get("Actual")),
                "estimate": _metric(row.get("Forecast")),
                "previous": _metric(row.get("Previous")),
                "unit": None,
                "currency": None,
            }
        )
    if not events and dropped:
        raise BorsapyGatewayError("Takvim olaylarının tarih veya başlık alanları okunamadı.", 502)
    return sorted(events, key=lambda e: (e["date"], e["source_time"] or "99:99", e["id"])), dropped


class CalendarService:
    """One provider request at a time, bounded LRU and explicitly marked stale data."""

    def __init__(self) -> None:
        self.cache_ttl_seconds = int(settings.calendar_cache_seconds)
        self.stale_seconds = 900
        self.max_cache_entries = 16
        self.wait_seconds = 35
        self._cache: OrderedDict[CalendarKey, dict] = OrderedDict()
        self._failures: OrderedDict[CalendarKey, datetime] = OrderedDict()
        self._lock = threading.Lock()
        self._flight: tuple[CalendarKey, threading.Event] | None = None

    def _validate(
        self, from_date: str | None, to_date: str | None, country: str, importance: str
    ) -> CalendarKey:
        today = _utc_now().astimezone(ISTANBUL).date()
        try:
            start = date.fromisoformat(from_date) if from_date else today
            end = date.fromisoformat(to_date) if to_date else start + timedelta(days=14)
            if (from_date and start.isoformat() != from_date) or (
                to_date and end.isoformat() != to_date
            ):
                raise ValueError
            if not today - timedelta(days=7) <= start <= end <= today + timedelta(days=30):
                raise ValueError
            if (end - start).days > 30:
                raise ValueError
            countries = tuple(sorted({part.strip().upper() for part in country.split(",")}))
            if not 1 <= len(countries) <= 3 or not set(countries) <= COUNTRIES:
                raise ValueError
            if importance not in {"all", "low", "mid", "high"}:
                raise ValueError
        except (TypeError, ValueError, AttributeError):
            raise BorsapyGatewayError(
                "Takvim: en fazla 31 gün, son 7 gün ile gelecek 30 gün ve en fazla 3 ülke seçin.",
                422,
            ) from None
        return start, end, countries, importance

    def _cached(self, key: CalendarKey, now: datetime, *, stale: bool = False) -> dict | None:
        cached = self._cache.get(key)
        if not cached:
            return None
        limit = self.cache_ttl_seconds + (self.stale_seconds if stale else 0)
        if (now - cached["at"]).total_seconds() >= limit:
            return None
        self._cache.move_to_end(key)
        result = deepcopy(cached["result"])
        result["meta"]["cache_hit"] = True
        if stale:
            result["meta"]["state"] = "stale"
            result["meta"]["warnings"].append(
                "Kaynak yenilenemedi. Önceki başarılı yanıt gösteriliyor."
            )
        return result

    def get_economic_calendar(
        self,
        from_date: str | None = None,
        to_date: str | None = None,
        country: str = "TR,US",
        importance: str = "all",
    ) -> dict:
        key = self._validate(from_date, to_date, country, importance)
        start, end, countries, importance = key
        now = _utc_now()
        with self._lock:
            cached = self._cached(key, now)
            if cached:
                return cached
            if self._failures.get(key, datetime.min.replace(tzinfo=UTC)) > now:
                cached = self._cached(key, now, stale=True)
                if cached:
                    return cached
                raise BorsapyGatewayError("Takvim kaynağı geçici olarak kullanılamıyor.", 503)
            if self._flight:
                if self._flight[0] != key:
                    raise BorsapyGatewayError(
                        "Takvim yenileniyor; kısa süre sonra tekrar deneyin.", 503
                    )
                completed, owner = self._flight[1], False
            else:
                completed, owner = threading.Event(), True
                self._flight = (key, completed)
        if not owner:
            if not completed.wait(self.wait_seconds):
                raise BorsapyGatewayError("Takvim kaynağı henüz yanıt vermedi.", 503)
            return self.get_economic_calendar(from_date, to_date, country, importance)
        try:
            frame = get_borsapy_gateway().run_public(
                lambda bp: calendar_events(
                    bp,
                    start=start.isoformat(),
                    end=end.isoformat(),
                    country=list(countries),
                    importance=None if importance == "all" else importance,
                ),
            )
            events, dropped = _normalize(frame, start, end)
            warnings = WARNINGS.copy()
            if dropped:
                warnings.append(f"Tarihi veya başlığı geçersiz {dropped} olay gösterilemedi.")
            now = _utc_now()
            result = {
                "events": events,
                "meta": {
                    "source": "borsapy_dovizcom",
                    "state": "ok" if events else "empty",
                    "fetched_at": now.isoformat().replace("+00:00", "Z"),
                    "source_timezone": None,
                    "display_timezone": "Europe/Istanbul",
                    "from_date": start.isoformat(),
                    "to_date": end.isoformat(),
                    "countries": list(countries),
                    "warnings": warnings,
                    "cache_hit": False,
                    "provider_cache_seconds": 3600,
                },
            }
            with self._lock:
                self._cache[key] = {"at": now, "result": deepcopy(result)}
                self._cache.move_to_end(key)
                while len(self._cache) > self.max_cache_entries:
                    self._cache.popitem(last=False)
                self._failures.pop(key, None)
            return result
        except Exception as exc:
            with self._lock:
                self._failures[key] = _utc_now() + timedelta(seconds=30)
                self._failures.move_to_end(key)
                while len(self._failures) > self.max_cache_entries:
                    self._failures.popitem(last=False)
                cached = self._cached(key, _utc_now(), stale=True)
            if cached:
                return cached
            if isinstance(exc, BorsapyGatewayError):
                raise
            raise BorsapyGatewayError("Takvim kaynağına erişilemedi.", 502) from None
        finally:
            with self._lock:
                self._flight = None
                completed.set()


calendar_service = CalendarService()
