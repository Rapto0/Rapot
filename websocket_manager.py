"""
WebSocket Manager - Binance Real-time Data Streams
Handles ticker, depth, and trade streams with automatic reconnection.
"""

import asyncio
import json
import re
from collections import defaultdict
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from time import monotonic
from typing import Any

import aiohttp

from logger import get_logger

logger = get_logger(__name__)


def normalize_stream_symbol(symbol: str) -> str:
    if not isinstance(symbol, str):
        raise ValueError("Invalid stream symbol")
    normalized = symbol.strip().upper()
    if re.fullmatch(r"[A-Z0-9]{2,30}", normalized) is None:
        raise ValueError("Invalid stream symbol")
    return normalized


def normalize_kline_interval(interval: str) -> str:
    allowed = {
        "1s",
        "1m",
        "3m",
        "5m",
        "15m",
        "30m",
        "1h",
        "2h",
        "4h",
        "6h",
        "8h",
        "12h",
        "1d",
        "3d",
        "1w",
        "1M",
    }
    if not isinstance(interval, str) or interval.strip() not in allowed:
        raise ValueError("Invalid kline interval")
    return interval.strip()


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
        self._subscription_counts: dict[str, int] = {}
        self._subscription_lock = asyncio.Lock()
        self._message_id = 0
        self._next_control_at = 0.0
        self._control_sleep = asyncio.sleep
        self._pending_controls: dict[int, tuple[str, str]] = {}
        self._last_subscription_error: str | None = None
        self._connection_task: asyncio.Task | None = None
        self._callbacks: dict[str, list[Callable]] = defaultdict(list)
        self._ticker_cache: dict[str, TickerData] = {}
        self._last_prices: dict[str, float] = {}

    async def start(self):
        """Start the WebSocket manager."""
        if self._running:
            return

        self._running = True
        self._session = aiohttp.ClientSession()
        await self.subscribe_all_tickers()
        self._connection_task = asyncio.create_task(
            self._connection_loop(), name="rapot-binance-stream"
        )
        logger.info("BinanceWebSocketManager started")

    async def stop(self):
        """Stop the WebSocket manager and cleanup."""
        self._running = False
        error = None
        if self._connection_task is not None:
            self._connection_task.cancel()
            try:
                with suppress(asyncio.CancelledError):
                    await self._connection_task
            except Exception as exc:
                error = exc
            finally:
                self._connection_task = None
        for attribute in ("_ws", "_session"):
            resource = getattr(self, attribute)
            if resource is not None and not resource.closed:
                try:
                    await asyncio.wait_for(resource.close(), timeout=5)
                except Exception as exc:
                    error = error or exc
            if resource is None or resource.closed:
                setattr(self, attribute, None)
        self._subscriptions.clear()
        self._subscription_counts.clear()
        self._pending_controls.clear()
        if error is not None:
            raise error

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
            finally:
                if self._ws is not None and not self._ws.closed:
                    with suppress(Exception):
                        await asyncio.wait_for(self._ws.close(), timeout=5)
                self._ws = None

            if self._running:
                logger.info(f"Reconnecting in {self._reconnect_delay}s...")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)

    async def _connect(self):
        """Establish WebSocket connection."""
        if not self._subscriptions:
            # Default: subscribe to all USDT pairs mini ticker
            await self.subscribe_all_tickers()
        # Serialize the initial subscription snapshot with dynamic requests so
        # a subscription arriving during the handshake cannot be lost.
        async with self._subscription_lock:
            streams = "/".join(sorted(self._subscriptions))
            url = f"{self.COMBINED_URL}?streams={streams}"
            self._ws = await asyncio.wait_for(
                self._session.ws_connect(url, heartbeat=30), timeout=10
            )
            self._pending_controls.clear()
        self._reconnect_delay = 1
        logger.info(f"Connected to Binance WebSocket with {len(self._subscriptions)} streams")

    async def _listen(self):
        """Listen for incoming WebSocket messages."""
        if self._ws is None:
            logger.debug("WebSocket listen skipped because connection is not established yet")
            return

        async for msg in self._ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    payload = json.loads(msg.data)
                except json.JSONDecodeError as exc:
                    logger.warning("Malformed JSON payload received: %s", exc)
                    continue

                try:
                    await self._handle_message(payload)
                except (KeyError, ValueError, TypeError) as exc:
                    logger.warning("Malformed websocket payload ignored: %s", exc)
                    continue
                except Exception:
                    logger.exception("Unexpected websocket payload handling error.")
                    continue
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

        if "id" in data and ("result" in data or "code" in data):
            request_id = data.get("id")
            request = (
                self._pending_controls.pop(request_id, None)
                if isinstance(request_id, int)
                else None
            )
            if "code" in data:
                self._last_subscription_error = f"{data.get('code')}: {data.get('msg')}"
                logger.warning(
                    "Binance stream control rejected (%s): %s",
                    request,
                    self._last_subscription_error,
                )
                # Reconnect with the current desired set; a transport send is
                # not an acknowledgement of the server's subscription state.
                if self._ws is not None and not self._ws.closed:
                    await asyncio.wait_for(self._ws.close(), timeout=5)
            elif request is not None and data.get("result") is None:
                logger.debug("Binance stream control acknowledged: %s", request)
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

        try:
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
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Malformed payload for stream %s ignored: %s", stream_name, exc)
        except Exception:
            logger.exception("Unexpected payload processing error for stream %s.", stream_name)

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
        if "!miniTicker@arr" not in self._subscriptions:
            await self._subscribe_stream("!miniTicker@arr")

    async def _send_subscription(self, method: str, stream: str) -> None:
        if self._ws is None or self._ws.closed:
            return
        # Binance allows 5 incoming messages/s including ping/pong. Spread
        # control requests to <3/s under the subscription lock, leaving headroom.
        self._message_id += 1
        request_id = self._message_id
        try:
            delay = self._next_control_at - monotonic()
            if delay > 0:
                await self._control_sleep(delay)
            if len(self._pending_controls) >= 1024:
                raise RuntimeError("Too many unacknowledged Binance stream requests")
            self._pending_controls[request_id] = (method, stream)
            await asyncio.wait_for(
                self._ws.send_json({"method": method, "params": [stream], "id": request_id}),
                timeout=5,
            )
        except BaseException:
            self._pending_controls.pop(request_id, None)
            if self._ws is not None and not self._ws.closed:
                with suppress(Exception):
                    await asyncio.wait_for(self._ws.close(), timeout=5)
            raise
        finally:
            self._next_control_at = monotonic() + 0.35

    async def _subscribe_stream(self, stream: str) -> None:
        async with self._subscription_lock:
            count = self._subscription_counts.get(stream, 0)
            if count == 0:
                if len(self._subscriptions) >= 1024:
                    raise ValueError("Binance stream subscription limit reached")
                await self._send_subscription("SUBSCRIBE", stream)
                self._subscriptions.add(stream)
            self._subscription_counts[stream] = count + 1

    async def _unsubscribe_stream(self, stream: str) -> None:
        async with self._subscription_lock:
            count = self._subscription_counts.get(stream, 0)
            if count > 1:
                self._subscription_counts[stream] = count - 1
            elif count == 1:
                self._subscription_counts.pop(stream, None)
                self._subscriptions.discard(stream)
                await self._send_subscription("UNSUBSCRIBE", stream)

    async def subscribe_ticker(self, symbol: str):
        """Subscribe to a specific symbol's ticker."""
        await self._subscribe_stream(f"{normalize_stream_symbol(symbol).lower()}@ticker")

    async def unsubscribe_ticker(self, symbol: str) -> None:
        await self._unsubscribe_stream(f"{normalize_stream_symbol(symbol).lower()}@ticker")

    async def subscribe_kline(self, symbol: str, interval: str = "1m"):
        """Subscribe to kline stream for a symbol."""
        await self._subscribe_stream(
            f"{normalize_stream_symbol(symbol).lower()}@kline_{normalize_kline_interval(interval)}"
        )

    async def unsubscribe_kline(self, symbol: str, interval: str = "1m") -> None:
        await self._unsubscribe_stream(
            f"{normalize_stream_symbol(symbol).lower()}@kline_{normalize_kline_interval(interval)}"
        )

    async def subscribe_trade(self, symbol: str):
        """Subscribe to trade stream for a symbol."""
        await self._subscribe_stream(f"{normalize_stream_symbol(symbol).lower()}@trade")

    async def unsubscribe_trade(self, symbol: str) -> None:
        await self._unsubscribe_stream(f"{normalize_stream_symbol(symbol).lower()}@trade")

    async def subscribe_agg_trade(self, symbol: str):
        """Subscribe to aggregated trade stream."""
        await self._subscribe_stream(f"{normalize_stream_symbol(symbol).lower()}@aggTrade")

    async def unsubscribe_agg_trade(self, symbol: str) -> None:
        await self._unsubscribe_stream(f"{normalize_stream_symbol(symbol).lower()}@aggTrade")

    def on(self, event: str, callback: Callable):
        """Register a callback for an event type."""
        if callback not in self._callbacks[event]:
            self._callbacks[event].append(callback)

    def off(self, event: str, callback: Callable):
        """Remove a callback for an event type."""
        if callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)

    async def _notify(self, event: str, data: Any):
        """Notify all registered callbacks for an event."""
        for callback in tuple(self._callbacks[event]):
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
