import datetime
import os
from typing import Any

import requests


class CalendarService:
    def __init__(self):
        self.api_key = os.getenv("FINNHUB_API_KEY")
        self.base_url = "https://finnhub.io/api/v1/calendar/economic"
        self._cache = {}
        self._cache_expiry = {}

    def get_economic_calendar(
        self, from_date: str = None, to_date: str = None
    ) -> list[dict[str, Any]]:
        """
        Finnhub API'den ekonomik takvim verilerini çeker.
        Tarih formatı: YYYY-MM-DD
        """
        if not self.api_key:
            print("WARNING: FINNHUB_API_KEY bulunamadı. Mock veri veya boş liste dönebilir.")
            return []

        # Varsayılan tarihler (bugün ve gelecek 7 gün)
        if not from_date:
            from_date = datetime.date.today().strftime("%Y-%m-%d")
        if not to_date:
            to_date = (datetime.date.today() + datetime.timedelta(days=7)).strftime("%Y-%m-%d")

        # Cache key oluştur
        cache_key = f"{from_date}_{to_date}"

        # Cache kontrolü (1 saatlik cache)
        if cache_key in self._cache and datetime.datetime.now() < self._cache_expiry[cache_key]:
            return self._cache[cache_key]

        try:
            params = {"from": from_date, "to": to_date, "token": self.api_key}

            response = requests.get(self.base_url, params=params)
            response.raise_for_status()

            data = response.json()

            # Veriyi işle ve cache'le
            if "economicCalendar" in data:
                # Bazen data direkt liste olabilir veya 'economicCalendar' key'i içinde olabilir
                # Finnhub dokümanına göre response: { "economicCalendar": [...] }
                events = data["economicCalendar"]
            elif isinstance(data, list):
                events = data
            else:
                events = []

            # Önemli eventleri filtreleyebiliriz veya hepsini dönebiliriz.
            # Şimdilik hepsini dönüyoruz.

            self._cache[cache_key] = events
            self._cache_expiry[cache_key] = datetime.datetime.now() + datetime.timedelta(hours=1)

            return events

        except requests.RequestException as e:
            print(f"Finnhub API hatası: {e}")
            return []
        except Exception as e:
            print(f"Beklenmedik hata (CalendarService): {e}")
            return []


calendar_service = CalendarService()
