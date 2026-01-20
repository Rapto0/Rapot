"""
Async Data Loader Modülü
Asenkron veri çekme işlemleri.
"""

import asyncio

import aiohttp
import pandas as pd

from config import rate_limits
from logger import get_logger
from settings import settings

logger = get_logger(__name__)

# Binance client - lazy initialization
_binance_client = None


def _get_binance_client():
    """Binance client'ı lazy olarak başlatır."""
    global _binance_client
    if _binance_client is None:
        if settings.binance_api_key and settings.binance_secret_key:
            from binance.client import Client

            _binance_client = Client(settings.binance_api_key, settings.binance_secret_key)
    return _binance_client


# Rate limiting semaphore
BIST_SEMAPHORE = asyncio.Semaphore(5)  # Max 5 eşzamanlı BIST isteği
CRYPTO_SEMAPHORE = asyncio.Semaphore(10)  # Max 10 eşzamanlı kripto isteği


async def fetch_bist_data_async(
    session: aiohttp.ClientSession, symbol: str, start_date: str = "01-01-2015"
) -> pd.DataFrame | None:
    """
    Asenkron BIST veri çekme.

    Args:
        session: aiohttp session
        symbol: BIST sembolü
        start_date: Başlangıç tarihi

    Returns:
        OHLCV DataFrame veya None
    """
    async with BIST_SEMAPHORE:
        try:
            # isyatirimhisse sync kütüphane, thread pool'da çalıştır
            # Python 3.10+ uyumlu: get_running_loop() kullan
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            df = await loop.run_in_executor(None, _fetch_bist_sync, symbol, start_date)
            return df
        except Exception as e:
            logger.error(f"Async BIST veri hatası ({symbol}): {e}")
            return None


def _fetch_bist_sync(symbol: str, start_date: str) -> pd.DataFrame | None:
    """Sync BIST veri çekme (executor'da çalışır)."""
    from isyatirimhisse import fetch_stock_data

    try:
        # isyatirimhisse expects 'symbols' as a list
        # Note: No end_date - library will get data until today
        df = fetch_stock_data(symbols=[symbol], start_date=start_date)

        if df is None or df.empty:
            return None

        # Sütun dönüşümü - isyatirimhisse Türkçe sütun isimleri kullanır
        df = df.rename(
            columns={
                "HGDG_KAPANIS": "Close",
                "HGDG_MIN": "Low",
                "HGDG_MAX": "High",
                "HGDG_HACIM": "Volume",
                "HGDG_TARIH": "Date",
            }
        )

        # Open sütunu yoksa Close'tan oluştur
        if "Open" not in df.columns and "Close" in df.columns:
            df["Open"] = df["Close"]

        # Date sütunundan index oluştur
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df.set_index("Date", inplace=True)

        # Sayısal sütunları float'a çevir
        cols_to_fix = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
        if cols_to_fix:
            df[cols_to_fix] = df[cols_to_fix].astype(float)

        df = df.sort_index()
        return df

    except Exception as e:
        logger.debug(f"BIST sync hatası ({symbol}): {e}")
        return None


async def fetch_crypto_data_async(
    session: aiohttp.ClientSession, symbol: str, start_str: str = "6 years ago"
) -> pd.DataFrame | None:
    """
    Asenkron kripto veri çekme (Binance API).

    Args:
        session: aiohttp session
        symbol: Kripto çifti (örn: BTCUSDT)
        start_str: Başlangıç tarihi string

    Returns:
        OHLCV DataFrame veya None
    """
    async with CRYPTO_SEMAPHORE:
        try:
            # Binance klines endpoint
            url = "https://api.binance.com/api/v3/klines"

            # Start time hesapla (basit yaklaşım: 6 yıl = ~2190 gün)
            import time

            end_time = int(time.time() * 1000)
            start_time = end_time - (2190 * 24 * 60 * 60 * 1000)

            params = {
                "symbol": symbol,
                "interval": "1d",
                "startTime": start_time,
                "endTime": end_time,
                "limit": 1000,
            }

            all_klines = []

            # Pagination ile tüm veriyi çek
            while True:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        break

                    klines = await response.json()
                    if not klines:
                        break

                    all_klines.extend(klines)

                    # Son verinin timestamp'i
                    last_time = klines[-1][0]
                    if last_time >= end_time or len(klines) < 1000:
                        break

                    params["startTime"] = last_time + 1
                    await asyncio.sleep(0.1)  # Rate limit

            if not all_klines:
                return None

            # DataFrame'e çevir
            df = pd.DataFrame(
                all_klines,
                columns=[
                    "OpenTime",
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Volume",
                    "CloseTime",
                    "QuoteVolume",
                    "Trades",
                    "TakerBuyBase",
                    "TakerBuyQuote",
                    "Ignore",
                ],
            )

            df["Open"] = df["Open"].astype(float)
            df["High"] = df["High"].astype(float)
            df["Low"] = df["Low"].astype(float)
            df["Close"] = df["Close"].astype(float)
            df["Volume"] = df["Volume"].astype(float)
            df.index = pd.to_datetime(df["OpenTime"], unit="ms")
            df = df[["Open", "High", "Low", "Close", "Volume"]]
            df = df.sort_index()

            return df

        except Exception as e:
            logger.error(f"Async kripto veri hatası ({symbol}): {e}")
            return None


async def fetch_multiple_bist_async(
    symbols: list[str], start_date: str = "01-01-2015", batch_size: int = 20
) -> dict:
    """
    Birden fazla BIST sembolünü paralel çeker.

    Args:
        symbols: Sembol listesi
        start_date: Başlangıç tarihi
        batch_size: Batch boyutu

    Returns:
        {symbol: DataFrame} dictionary
    """
    results = {}

    async with aiohttp.ClientSession() as session:
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i : i + batch_size]

            tasks = [fetch_bist_data_async(session, sym, start_date) for sym in batch]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for sym, result in zip(batch, batch_results):
                if isinstance(result, pd.DataFrame):
                    results[sym] = result
                elif isinstance(result, Exception):
                    logger.error(f"Batch hatası ({sym}): {result}")

            # Batch arası bekleme
            await asyncio.sleep(rate_limits.BIST_DELAY)

    return results


async def fetch_multiple_crypto_async(symbols: list[str], batch_size: int = 50) -> dict:
    """
    Birden fazla kripto sembolünü paralel çeker.

    Args:
        symbols: Sembol listesi
        batch_size: Batch boyutu

    Returns:
        {symbol: DataFrame} dictionary
    """
    results = {}

    async with aiohttp.ClientSession() as session:
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i : i + batch_size]

            tasks = [fetch_crypto_data_async(session, sym) for sym in batch]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for sym, result in zip(batch, batch_results):
                if isinstance(result, pd.DataFrame):
                    results[sym] = result
                elif isinstance(result, Exception):
                    logger.error(f"Batch hatası ({sym}): {result}")

            # Batch arası bekleme
            await asyncio.sleep(rate_limits.CRYPTO_DELAY)

    return results


def get_all_binance_symbols_async() -> list[str]:
    """Binance USDT çiftlerini döndürür."""
    client = _get_binance_client()
    if client is None:
        return []

    try:
        info = client.get_exchange_info()
        return [
            s["symbol"]
            for s in info["symbols"]
            if s["quoteAsset"] == "USDT" and s["status"] == "TRADING"
        ]
    except Exception as e:
        logger.error(f"Binance symbols hatası: {e}")
        return []
