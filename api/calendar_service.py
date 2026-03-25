import datetime
from typing import Any

import requests

from logger import get_logger
from settings import settings

logger = get_logger(__name__)


class CalendarService:
    def __init__(self) -> None:
        self.api_key = str(settings.finnhub_api_key or "").strip()
        self.base_url = "https://finnhub.io/api/v1/calendar/economic"
        self.cache_ttl_seconds = int(settings.calendar_cache_seconds)
        self._cache: dict[str, list[dict[str, Any]]] = {}
        self._cache_expiry: dict[str, datetime.datetime] = {}

    def get_economic_calendar(
        self, from_date: str | None = None, to_date: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Finnhub ekonomik takvim verilerini doner.
        Tarih formatlari: YYYY-MM-DD
        """
        if not self.api_key:
            logger.warning("FINNHUB_API_KEY bulunamadi, ekonomik takvim bos donuyor.")
            return []

        today = datetime.date.today()
        if not from_date:
            from_date = today.strftime("%Y-%m-%d")
        if not to_date:
            to_date = (today + datetime.timedelta(days=7)).strftime("%Y-%m-%d")

        cache_key = f"{from_date}_{to_date}"
        now = datetime.datetime.utcnow()
        expires_at = self._cache_expiry.get(cache_key)
        if expires_at and cache_key in self._cache and now < expires_at:
            return self._cache[cache_key]

        try:
            response = requests.get(
                self.base_url,
                params={
                    "from": from_date,
                    "to": to_date,
                    "token": self.api_key,
                },
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()

            if isinstance(payload, dict) and isinstance(payload.get("economicCalendar"), list):
                events = payload["economicCalendar"]
            elif isinstance(payload, list):
                events = payload
            else:
                events = []

            self._cache[cache_key] = events
            self._cache_expiry[cache_key] = now + datetime.timedelta(seconds=self.cache_ttl_seconds)
            return events
        except requests.RequestException as exc:
            logger.warning("Finnhub calendar request failed: %s", exc)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected calendar service error: %s", exc)

        # Hata durumunda son basarili cache varsa onu don.
        if cache_key in self._cache:
            return self._cache[cache_key]
        return []


calendar_service = CalendarService()
