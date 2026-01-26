"""
BIST Data Service - Istanbul Stock Exchange Real-time Data
Fetches and caches BIST data with automatic refresh.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class BISTStock:
    """BIST stock data structure."""
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    volume: int
    high: float
    low: float
    open: float
    prev_close: float
    timestamp: datetime = field(default_factory=datetime.now)
    market: str = "BIST"

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "price": self.price,
            "change": self.change,
            "changePercent": self.change_percent,
            "volume": self.volume,
            "high": self.high,
            "low": self.low,
            "open": self.open,
            "prevClose": self.prev_close,
            "timestamp": self.timestamp.isoformat(),
            "market": self.market,
        }


class BISTDataService:
    """
    BIST data fetching and caching service.
    Uses Is Yatirim public endpoints for data.
    """

    # Is Yatirim endpoints
    HISSE_ENDPOINT = "https://www.isyatirim.com.tr/api/borsa/hisseler"
    TICKER_ENDPOINT = "https://www.isyatirim.com.tr/_Layouts/15/IsYatirim.Website/Common/ChartData.aspx/IndexChartData"

    # Cache settings
    CACHE_TTL = 30  # seconds
    REFRESH_INTERVAL = 15  # seconds

    def __init__(self):
        self._cache: dict[str, BISTStock] = {}
        self._cache_time: datetime | None = None
        self._session: aiohttp.ClientSession | None = None
        self._running = False
        self._callbacks: list = []
        self._symbols: list[str] = []
        self._load_symbols()

    def _load_symbols(self):
        """Load BIST symbols from file."""
        symbols_file = Path(__file__).parent / "data" / "bist_symbols.json"
        if symbols_file.exists():
            with open(symbols_file) as f:
                data = json.load(f)
                self._symbols = data.get("symbols", [])
                logger.info(f"Loaded {len(self._symbols)} BIST symbols")
        else:
            # Default BIST 30 symbols
            self._symbols = [
                "AKBNK", "ARCLK", "ASELS", "BIMAS", "EKGYO",
                "EREGL", "FROTO", "GARAN", "GUBRF", "HEKTS",
                "ISCTR", "KCHOL", "KOZAA", "KOZAL", "KRDMD",
                "PETKM", "PGSUS", "SAHOL", "SASA", "SISE",
                "TAVHL", "TCELL", "THYAO", "TKFEN", "TOASO",
                "TTKOM", "TUPRS", "VAKBN", "VESTL", "YKBNK",
            ]
            logger.info("Using default BIST 30 symbols")

    async def start(self):
        """Start the BIST data service."""
        if self._running:
            return

        self._running = True
        self._session = aiohttp.ClientSession(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
            }
        )
        asyncio.create_task(self._refresh_loop())
        logger.info("BISTDataService started")

    async def stop(self):
        """Stop the BIST data service."""
        self._running = False
        if self._session and not self._session.closed:
            await self._session.close()
        logger.info("BISTDataService stopped")

    async def _refresh_loop(self):
        """Periodically refresh BIST data."""
        while self._running:
            try:
                await self._fetch_all_data()
                await self._notify_subscribers()
            except Exception as e:
                logger.error(f"Error refreshing BIST data: {e}")

            await asyncio.sleep(self.REFRESH_INTERVAL)

    async def _fetch_all_data(self):
        """Fetch all BIST stock data."""
        try:
            # Try Is Yatirim API first
            data = await self._fetch_isyatirim_data()
            if data:
                self._update_cache(data)
                return

            # Fallback: Fetch individual symbols
            await self._fetch_individual_symbols()

        except Exception as e:
            logger.error(f"Error fetching BIST data: {e}")

    async def _fetch_isyatirim_data(self) -> list[dict] | None:
        """Fetch data from Is Yatirim API."""
        try:
            url = "https://www.isyatirim.com.tr/_layouts/15/IsYatirim.Website/Common/Data.aspx/HissseSenetleri"
            params = {
                "hession": "XU100",
                "startdate": datetime.now().strftime("%d-%m-%Y"),
                "enddate": datetime.now().strftime("%d-%m-%Y"),
            }

            async with self._session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.warning(f"Is Yatirim API failed: {e}")

        return None

    async def _fetch_individual_symbols(self):
        """Fetch individual symbol data as fallback."""
        tasks = []
        for symbol in self._symbols[:50]:  # Limit to 50 symbols
            tasks.append(self._fetch_symbol_data(symbol))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, BISTStock):
                self._cache[result.symbol] = result

    async def _fetch_symbol_data(self, symbol: str) -> BISTStock | None:
        """Fetch data for a single symbol."""
        try:
            # Simulated data based on typical BIST behavior
            # In production, this would call actual API endpoints
            url = f"https://www.isyatirim.com.tr/_Layouts/15/IsYatirim.Website/Common/ChartData.aspx/IndexChartData"
            params = {
                "endeks": f"{symbol}.E.BIST",
                "doession": "",
            }

            async with self._session.get(url, params=params, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return self._parse_symbol_data(symbol, data)

        except Exception as e:
            logger.debug(f"Failed to fetch {symbol}: {e}")

        return None

    def _parse_symbol_data(self, symbol: str, data: dict) -> BISTStock | None:
        """Parse symbol data from API response."""
        try:
            # Adapt parsing based on actual API response structure
            return BISTStock(
                symbol=symbol,
                name=data.get("name", symbol),
                price=float(data.get("price", 0)),
                change=float(data.get("change", 0)),
                change_percent=float(data.get("changePercent", 0)),
                volume=int(data.get("volume", 0)),
                high=float(data.get("high", 0)),
                low=float(data.get("low", 0)),
                open=float(data.get("open", 0)),
                prev_close=float(data.get("prevClose", 0)),
            )
        except Exception:
            return None

    def _update_cache(self, data: list[dict]):
        """Update cache with fetched data."""
        for item in data:
            try:
                symbol = item.get("symbol") or item.get("hisse") or item.get("kod")
                if not symbol:
                    continue

                stock = BISTStock(
                    symbol=symbol,
                    name=item.get("name", item.get("ad", symbol)),
                    price=float(item.get("price", item.get("kapanis", 0))),
                    change=float(item.get("change", item.get("fark", 0))),
                    change_percent=float(item.get("changePercent", item.get("yuzde", 0))),
                    volume=int(item.get("volume", item.get("hacim", 0))),
                    high=float(item.get("high", item.get("yuksek", 0))),
                    low=float(item.get("low", item.get("dusuk", 0))),
                    open=float(item.get("open", item.get("acilis", 0))),
                    prev_close=float(item.get("prevClose", item.get("oncekiKapanis", 0))),
                )
                self._cache[symbol] = stock
            except Exception as e:
                logger.debug(f"Error parsing stock data: {e}")

        self._cache_time = datetime.now()
        logger.debug(f"Updated BIST cache with {len(self._cache)} stocks")

    def on_update(self, callback):
        """Register a callback for data updates."""
        self._callbacks.append(callback)

    def off_update(self, callback):
        """Remove a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def _notify_subscribers(self):
        """Notify all subscribers of data update."""
        data = self.get_all_stocks()
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Error in BIST callback: {e}")

    def get_all_stocks(self) -> list[dict]:
        """Get all cached stock data."""
        return [stock.to_dict() for stock in self._cache.values()]

    def get_stock(self, symbol: str) -> dict | None:
        """Get cached data for a specific symbol."""
        stock = self._cache.get(symbol.upper())
        return stock.to_dict() if stock else None

    def get_top_gainers(self, limit: int = 10) -> list[dict]:
        """Get top gaining stocks."""
        stocks = sorted(
            self._cache.values(),
            key=lambda x: x.change_percent,
            reverse=True
        )
        return [s.to_dict() for s in stocks[:limit]]

    def get_top_losers(self, limit: int = 10) -> list[dict]:
        """Get top losing stocks."""
        stocks = sorted(
            self._cache.values(),
            key=lambda x: x.change_percent
        )
        return [s.to_dict() for s in stocks[:limit]]

    def get_most_active(self, limit: int = 10) -> list[dict]:
        """Get most active stocks by volume."""
        stocks = sorted(
            self._cache.values(),
            key=lambda x: x.volume,
            reverse=True
        )
        return [s.to_dict() for s in stocks[:limit]]

    @property
    def is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._cache_time:
            return False
        return datetime.now() - self._cache_time < timedelta(seconds=self.CACHE_TTL)


# Global instance
bist_service = BISTDataService()
