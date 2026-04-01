from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MarketDataProvider(Protocol):
    """Unified provider interface for BIST/Kripto market data calls."""

    def fetch_history_with_fallback(
        self,
        symbol: str,
        *,
        period: str = "1d",
        fallback_period: str | None = "5d",
        interval: str | None = None,
        auto_adjust: bool = True,
        actions: bool = False,
    ) -> Any: ...

    def fetch_yfinance_download(self, tickers: str | list[str]) -> Any: ...

    def fetch_binance_klines(self, symbol: str, interval: str, limit: int) -> Any: ...

    def fetch_binance_24h_metrics(
        self, symbols: list[str]
    ) -> dict[str, dict[str, float | None | str]]: ...

    def normalize_binance_symbol(self, symbol: str) -> str: ...


@dataclass(slots=True)
class CallableMarketDataProvider(MarketDataProvider):
    """
    Adapter that turns existing function-based integrations into a common provider.
    """

    history_fetcher: Any
    yfinance_download_fetcher: Any
    binance_klines_fetcher: Any
    binance_24h_metrics_fetcher: Any
    binance_symbol_normalizer: Any

    def fetch_history_with_fallback(
        self,
        symbol: str,
        *,
        period: str = "1d",
        fallback_period: str | None = "5d",
        interval: str | None = None,
        auto_adjust: bool = True,
        actions: bool = False,
    ) -> Any:
        return self.history_fetcher(
            symbol,
            period=period,
            fallback_period=fallback_period,
            interval=interval,
            auto_adjust=auto_adjust,
            actions=actions,
        )

    def fetch_yfinance_download(self, tickers: str | list[str]) -> Any:
        return self.yfinance_download_fetcher(tickers)

    def fetch_binance_klines(self, symbol: str, interval: str, limit: int) -> Any:
        return self.binance_klines_fetcher(symbol, interval, limit)

    def fetch_binance_24h_metrics(
        self, symbols: list[str]
    ) -> dict[str, dict[str, float | None | str]]:
        return self.binance_24h_metrics_fetcher(symbols)

    def normalize_binance_symbol(self, symbol: str) -> str:
        return self.binance_symbol_normalizer(symbol)
