"""
WebSocket Manager - Binance Real-time Data Streams
Handles ticker, depth, and trade streams with automatic reconnection.
"""

import asyncio
import json
import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class StreamType(Enum):
    """WebSocket stream types."""

    TICKER = "ticker"
    MINI_TICKER = "miniTicker"
    DEPTH = "depth"
    TRADE = "trade"
    KLINE = "kline"
    AGG_TRADE = "aggTrade"


@dataclass
class TickerData:
    """Standardized ticker data structure."""

    symbol: str
    price: float
    price_change: float
    price_change_percent: float
    high_24h: float
    low_24h: float
    volume_24h: float
    quote_volume_24h: float
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "priceChange": self.price_change,
            "priceChangePercent": self.price_change_percent,
            "high24h": self.high_24h,
            "low24h": self.low_24h,
            "volume24h": self.volume_24h,
            "quoteVolume24h": self.quote_volume_24h,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class TradeData:
    """Standardized trade data structure."""

    symbol: str
    trade_id: int
    price: float
    quantity: float
    buyer_maker: bool
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "tradeId": self.trade_id,
            "price": self.price,
            "quantity": self.quantity,
            "side": "SELL" if self.buyer_maker else "BUY",
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class KlineData:
    """Standardized kline/candlestick data."""

    symbol: str
    interval: str
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: int
    is_closed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "time": self.open_time,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "isClosed": self.is_closed,
        }


class BinanceWebSocketManager:
    """
    Manages Binance WebSocket connections with automatic reconnection.
    Supports multiple stream types and callback-based data distribution.
    """

    BASE_URL = "wss://stream.binance.com:9443/ws"
    COMBINED_URL = "wss://stream.binance.com:9443/stream"

    def __init__(self):
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._running = False
        self._reconnect_delay = 1
        self._max_reconnect_delay = 60
        self._subscriptions: set[str] = set()
        self._callbacks: dict[str, list[Callable]] = defaultdict(list)
        self._ticker_cache: dict[str, TickerData] = {}
        self._last_prices: dict[str, float] = {}

    async def start(self):
        """Start the WebSocket manager."""
        if self._running:
            return

        self._running = True
        self._session = aiohttp.ClientSession()
        asyncio.create_task(self._connection_loop())
        logger.info("BinanceWebSocketManager started")

    async def stop(self):
        """Stop the WebSocket manager and cleanup."""
        self._running = False

        if self._ws and not self._ws.closed:
            await self._ws.close()

        if self._session and not self._session.closed:
            await self._session.close()

        logger.info("BinanceWebSocketManager stopped")

    async def _connection_loop(self):
        """Main connection loop with automatic reconnection."""
        while self._running:
            try:
                await self._connect()
                await self._listen()
            except aiohttp.ClientError as e:
                logger.error(f"WebSocket connection error: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Unexpected error in WebSocket: {e}")

            if self._running:
                logger.info(f"Reconnecting in {self._reconnect_delay}s...")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)

    async def _connect(self):
        """Establish WebSocket connection."""
        if not self._subscriptions:
            # Default: subscribe to all USDT pairs mini ticker
            await self.subscribe_all_tickers()
            return

        streams = "/".join(self._subscriptions)
        url = f"{self.COMBINED_URL}?streams={streams}"

        self._ws = await self._session.ws_connect(url, heartbeat=30)
        self._reconnect_delay = 1
        logger.info(f"Connected to Binance WebSocket with {len(self._subscriptions)} streams")

    async def _listen(self):
        """Listen for incoming WebSocket messages."""
        if self._ws is None:
            logger.debug("WebSocket listen skipped because connection is not established yet")
            return

        async for msg in self._ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                await self._handle_message(json.loads(msg.data))
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error(f"WebSocket error: {self._ws.exception()}")
                break
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                logger.warning("WebSocket closed by server")
                break

    async def _handle_message(self, data: Any):
        """Process incoming WebSocket message."""
        if isinstance(data, list):
            for item in data:
                await self._handle_message(item)
            return

        if not isinstance(data, dict):
            logger.warning("Ignoring unexpected WebSocket payload type: %s", type(data).__name__)
            return

        if "stream" in data:
            stream_name = str(data["stream"])
            payload = data.get("data")
        else:
            stream_name = str(data.get("e", "unknown"))
            payload = data

        await self._handle_payload(payload, stream_name)

    async def _handle_payload(self, payload: Any, stream_name: str):
        """Process a normalized WebSocket payload."""
        if isinstance(payload, list):
            for item in payload:
                await self._handle_payload(item, stream_name)
            return

        if not isinstance(payload, dict):
            logger.warning(
                "Ignoring unexpected WebSocket message payload type for %s: %s",
                stream_name,
                type(payload).__name__,
            )
            return

        event_type = str(payload.get("e", "") or "")
        if not event_type:
            if "miniTicker" in stream_name:
                event_type = "24hrMiniTicker"
            elif stream_name.endswith("@ticker"):
                event_type = "24hrTicker"
            elif "@trade" in stream_name:
                event_type = "trade"
            elif "@aggTrade" in stream_name:
                event_type = "aggTrade"
            elif "@kline_" in stream_name:
                event_type = "kline"

        # Parse and distribute data
        if event_type == "24hrMiniTicker":
            ticker = self._parse_mini_ticker(payload)
            self._ticker_cache[ticker.symbol] = ticker
            await self._notify("ticker", ticker.to_dict())

        elif event_type == "24hrTicker":
            ticker = self._parse_ticker(payload)
            self._ticker_cache[ticker.symbol] = ticker
            await self._notify("ticker", ticker.to_dict())

        elif event_type == "trade":
            trade = self._parse_trade(payload)
            await self._notify("trade", trade.to_dict())

        elif event_type == "kline":
            kline = self._parse_kline(payload)
            await self._notify("kline", kline.to_dict())

        elif event_type == "aggTrade":
            trade = self._parse_agg_trade(payload)
            await self._notify("trade", trade.to_dict())

    def _parse_mini_ticker(self, data: dict) -> TickerData:
        """Parse mini ticker data."""
        symbol = data["s"]
        price = float(data["c"])

        # Calculate change from cached price
        last_price = self._last_prices.get(symbol, price)
        price_change = price - last_price
        price_change_percent = (price_change / last_price * 100) if last_price else 0
        self._last_prices[symbol] = price

        return TickerData(
            symbol=symbol,
            price=price,
            price_change=price_change,
            price_change_percent=price_change_percent,
            high_24h=float(data.get("h", 0)),
            low_24h=float(data.get("l", 0)),
            volume_24h=float(data.get("v", 0)),
            quote_volume_24h=float(data.get("q", 0)),
        )

    def _parse_ticker(self, data: dict) -> TickerData:
        """Parse full ticker data."""
        return TickerData(
            symbol=data["s"],
            price=float(data["c"]),
            price_change=float(data["p"]),
            price_change_percent=float(data["P"]),
            high_24h=float(data["h"]),
            low_24h=float(data["l"]),
            volume_24h=float(data["v"]),
            quote_volume_24h=float(data["q"]),
        )

    def _parse_trade(self, data: dict) -> TradeData:
        """Parse trade data."""
        return TradeData(
            symbol=data["s"],
            trade_id=data["t"],
            price=float(data["p"]),
            quantity=float(data["q"]),
            buyer_maker=data["m"],
            timestamp=datetime.fromtimestamp(data["T"] / 1000),
        )

    def _parse_agg_trade(self, data: dict) -> TradeData:
        """Parse aggregated trade data."""
        return TradeData(
            symbol=data["s"],
            trade_id=data["a"],
            price=float(data["p"]),
            quantity=float(data["q"]),
            buyer_maker=data["m"],
            timestamp=datetime.fromtimestamp(data["T"] / 1000),
        )

    def _parse_kline(self, data: dict) -> KlineData:
        """Parse kline/candlestick data."""
        k = data["k"]
        return KlineData(
            symbol=data["s"],
            interval=k["i"],
            open_time=k["t"],
            open=float(k["o"]),
            high=float(k["h"]),
            low=float(k["l"]),
            close=float(k["c"]),
            volume=float(k["v"]),
            close_time=k["T"],
            is_closed=k["x"],
        )

    async def subscribe_all_tickers(self):
        """Subscribe to all USDT pair mini tickers."""
        self._subscriptions.add("!miniTicker@arr")

    async def subscribe_ticker(self, symbol: str):
        """Subscribe to a specific symbol's ticker."""
        stream = f"{symbol.lower()}@ticker"
        self._subscriptions.add(stream)

    async def subscribe_kline(self, symbol: str, interval: str = "1m"):
        """Subscribe to kline stream for a symbol."""
        stream = f"{symbol.lower()}@kline_{interval}"
        self._subscriptions.add(stream)

    async def subscribe_trade(self, symbol: str):
        """Subscribe to trade stream for a symbol."""
        stream = f"{symbol.lower()}@trade"
        self._subscriptions.add(stream)

    async def subscribe_agg_trade(self, symbol: str):
        """Subscribe to aggregated trade stream."""
        stream = f"{symbol.lower()}@aggTrade"
        self._subscriptions.add(stream)

    def on(self, event: str, callback: Callable):
        """Register a callback for an event type."""
        self._callbacks[event].append(callback)

    def off(self, event: str, callback: Callable):
        """Remove a callback for an event type."""
        if callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)

    async def _notify(self, event: str, data: Any):
        """Notify all registered callbacks for an event."""
        for callback in self._callbacks[event]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Error in callback for {event}: {e}")

    def get_cached_tickers(self) -> dict[str, dict]:
        """Get all cached ticker data."""
        return {symbol: ticker.to_dict() for symbol, ticker in self._ticker_cache.items()}

    def get_ticker(self, symbol: str) -> dict | None:
        """Get cached ticker for a specific symbol."""
        ticker = self._ticker_cache.get(symbol)
        return ticker.to_dict() if ticker else None


# Global instance
ws_manager = BinanceWebSocketManager()
