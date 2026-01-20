"""
Batch Data Loader Modülü
Paralel veri çekme, cache entegrasyonu ve ilerleme takibi.
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

import aiohttp
import pandas as pd

from config import rate_limits
from logger import get_logger

logger = get_logger(__name__)


@dataclass
class BatchProgress:
    """Batch işlem ilerleme durumu."""

    total: int = 0
    completed: int = 0
    successful: int = 0
    failed: int = 0
    cached: int = 0
    start_time: datetime = field(default_factory=datetime.now)

    @property
    def percent(self) -> float:
        """Tamamlanma yüzdesi."""
        if self.total == 0:
            return 0.0
        return (self.completed / self.total) * 100

    @property
    def elapsed_seconds(self) -> float:
        """Geçen süre (saniye)."""
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def estimated_remaining(self) -> float:
        """Tahmini kalan süre (saniye)."""
        if self.completed == 0:
            return 0.0
        per_item = self.elapsed_seconds / self.completed
        remaining = self.total - self.completed
        return per_item * remaining

    def __str__(self) -> str:
        return (
            f"[{self.completed}/{self.total}] "
            f"{self.percent:.1f}% - "
            f"✅{self.successful} ❌{self.failed} 📦{self.cached}"
        )


@dataclass
class BatchConfig:
    """Batch işlem konfigürasyonu."""

    batch_size: int = 20  # Batch başına sembol
    max_concurrent: int = 10  # Eşzamanlı istek
    delay_between_batches: float = 0.5  # Batch arası bekleme
    use_cache: bool = True  # Cache kullan
    cache_ttl_seconds: int = 300  # Cache TTL (5 dk)


class BatchDataLoader:
    """
    Paralel veri çekme sistemi.

    Özellikler:
    - Batch halinde paralel çekme
    - Cache entegrasyonu
    - İlerleme callback'leri
    - Hata toleransı
    """

    def __init__(self, config: BatchConfig | None = None):
        self.config = config or BatchConfig()
        self._progress = BatchProgress()
        self._progress_callback: Callable[[BatchProgress], None] | None = None

    def set_progress_callback(self, callback: Callable[[BatchProgress], None]) -> None:
        """İlerleme callback'ini ayarla."""
        self._progress_callback = callback

    def _notify_progress(self) -> None:
        """İlerleme durumunu bildir."""
        if self._progress_callback:
            self._progress_callback(self._progress)

    async def fetch_bist_batch(
        self,
        symbols: list[str],
        start_date: str = "01-01-2015",
    ) -> dict[str, pd.DataFrame]:
        """
        BIST sembollerini batch halinde çeker.

        Args:
            symbols: Sembol listesi
            start_date: Başlangıç tarihi

        Returns:
            {symbol: DataFrame} dictionary
        """
        results: dict[str, pd.DataFrame] = {}
        self._progress = BatchProgress(total=len(symbols))

        # Cache kontrolü
        symbols_to_fetch = []
        if self.config.use_cache:
            try:
                from price_cache import price_cache

                for symbol in symbols:
                    cached = price_cache.get(symbol, "BIST")
                    if cached is not None:
                        results[symbol] = cached
                        self._progress.cached += 1
                        self._progress.completed += 1
                    else:
                        symbols_to_fetch.append(symbol)
                self._notify_progress()
            except ImportError:
                symbols_to_fetch = symbols
        else:
            symbols_to_fetch = symbols

        logger.info(
            f"BIST Batch: {len(symbols)} sembol, "
            f"{self._progress.cached} cache, "
            f"{len(symbols_to_fetch)} çekilecek"
        )

        # Semaphore ile eşzamanlı istek limiti
        semaphore = asyncio.Semaphore(self.config.max_concurrent)

        async def fetch_one(symbol: str) -> tuple[str, pd.DataFrame | None]:
            async with semaphore:
                try:
                    df = await self._fetch_bist_single(symbol, start_date)
                    return symbol, df
                except Exception as e:
                    logger.error(f"BIST fetch hatası ({symbol}): {e}")
                    return symbol, None

        # Batch'ler halinde işle
        for i in range(0, len(symbols_to_fetch), self.config.batch_size):
            batch = symbols_to_fetch[i : i + self.config.batch_size]

            # Paralel fetch
            tasks = [fetch_one(sym) for sym in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    self._progress.failed += 1
                elif isinstance(result, tuple):
                    symbol, df = result
                    self._progress.completed += 1
                    if df is not None:
                        results[symbol] = df
                        self._progress.successful += 1
                        # Cache'e kaydet
                        if self.config.use_cache:
                            try:
                                from price_cache import price_cache

                                price_cache.set(symbol, "BIST", df)
                            except ImportError:
                                pass
                    else:
                        self._progress.failed += 1

                self._notify_progress()

            # Batch arası bekleme
            if i + self.config.batch_size < len(symbols_to_fetch):
                await asyncio.sleep(self.config.delay_between_batches)

        logger.info(f"BIST Batch tamamlandı: {self._progress}")
        return results

    async def _fetch_bist_single(self, symbol: str, start_date: str) -> pd.DataFrame | None:
        """Tek BIST sembolünü async olarak çeker."""
        try:
            loop = asyncio.get_running_loop()
            df = await loop.run_in_executor(None, self._fetch_bist_sync, symbol, start_date)
            return df
        except Exception as e:
            logger.debug(f"BIST single fetch hatası ({symbol}): {e}")
            return None

    def _fetch_bist_sync(self, symbol: str, start_date: str) -> pd.DataFrame | None:
        """Sync BIST veri çekme (executor'da çalışır)."""
        from isyatirimhisse import fetch_stock_data

        try:
            import time

            time.sleep(rate_limits.BIST_DELAY)

            end_date = datetime.now().strftime("%d-%m-%Y")
            df = fetch_stock_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                exchange="0",
                frequency="1d",
            )

            if df is not None and not df.empty:
                df.index = pd.to_datetime(df.index)
                df = df.sort_index()
                return df
            return None
        except Exception as e:
            logger.debug(f"BIST sync hatası ({symbol}): {e}")
            return None

    async def fetch_crypto_batch(
        self,
        symbols: list[str],
        days_back: int = 2190,  # ~6 yıl
    ) -> dict[str, pd.DataFrame]:
        """
        Kripto sembollerini batch halinde çeker.

        Args:
            symbols: Sembol listesi (BTCUSDT, ETHUSDT, vb.)
            days_back: Kaç gün geriye git

        Returns:
            {symbol: DataFrame} dictionary
        """
        results: dict[str, pd.DataFrame] = {}
        self._progress = BatchProgress(total=len(symbols))

        # Cache kontrolü
        symbols_to_fetch = []
        if self.config.use_cache:
            try:
                from price_cache import price_cache

                for symbol in symbols:
                    cached = price_cache.get(symbol, "Kripto")
                    if cached is not None:
                        results[symbol] = cached
                        self._progress.cached += 1
                        self._progress.completed += 1
                    else:
                        symbols_to_fetch.append(symbol)
                self._notify_progress()
            except ImportError:
                symbols_to_fetch = symbols
        else:
            symbols_to_fetch = symbols

        logger.info(
            f"Kripto Batch: {len(symbols)} sembol, "
            f"{self._progress.cached} cache, "
            f"{len(symbols_to_fetch)} çekilecek"
        )

        semaphore = asyncio.Semaphore(self.config.max_concurrent)

        async def fetch_one(
            session: aiohttp.ClientSession, symbol: str
        ) -> tuple[str, pd.DataFrame | None]:
            async with semaphore:
                try:
                    df = await self._fetch_crypto_single(session, symbol, days_back)
                    return symbol, df
                except Exception as e:
                    logger.error(f"Kripto fetch hatası ({symbol}): {e}")
                    return symbol, None

        async with aiohttp.ClientSession() as session:
            for i in range(0, len(symbols_to_fetch), self.config.batch_size):
                batch = symbols_to_fetch[i : i + self.config.batch_size]

                tasks = [fetch_one(session, sym) for sym in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in batch_results:
                    if isinstance(result, Exception):
                        self._progress.failed += 1
                    elif isinstance(result, tuple):
                        symbol, df = result
                        self._progress.completed += 1
                        if df is not None:
                            results[symbol] = df
                            self._progress.successful += 1
                            if self.config.use_cache:
                                try:
                                    from price_cache import price_cache

                                    price_cache.set(symbol, "Kripto", df)
                                except ImportError:
                                    pass
                        else:
                            self._progress.failed += 1

                    self._notify_progress()

                if i + self.config.batch_size < len(symbols_to_fetch):
                    await asyncio.sleep(self.config.delay_between_batches)

        logger.info(f"Kripto Batch tamamlandı: {self._progress}")
        return results

    async def _fetch_crypto_single(
        self,
        session: aiohttp.ClientSession,
        symbol: str,
        days_back: int,
    ) -> pd.DataFrame | None:
        """Tek kripto sembolünü async olarak çeker."""
        try:
            import time

            end_time = int(time.time() * 1000)
            start_time = end_time - (days_back * 24 * 60 * 60 * 1000)

            url = "https://api.binance.com/api/v3/klines"
            params = {
                "symbol": symbol,
                "interval": "1d",
                "startTime": start_time,
                "endTime": end_time,
                "limit": 1000,
            }

            all_klines = []

            while True:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        break

                    klines = await response.json()
                    if not klines:
                        break

                    all_klines.extend(klines)

                    last_time = klines[-1][0]
                    if last_time >= end_time or len(klines) < 1000:
                        break

                    params["startTime"] = last_time + 1
                    await asyncio.sleep(rate_limits.CRYPTO_DELAY)

            if not all_klines:
                return None

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

            for col in ["Open", "High", "Low", "Close", "Volume"]:
                df[col] = df[col].astype(float)

            df.index = pd.to_datetime(df["OpenTime"], unit="ms")
            df = df[["Open", "High", "Low", "Close", "Volume"]]
            df = df.sort_index()

            return df

        except Exception as e:
            logger.debug(f"Kripto single fetch hatası ({symbol}): {e}")
            return None

    @property
    def progress(self) -> BatchProgress:
        """Mevcut ilerleme durumu."""
        return self._progress


# ==================== CONVENIENCE FUNCTIONS ====================


async def fetch_all_bist_async(
    start_date: str = "01-01-2015",
    progress_callback: Callable[[BatchProgress], None] | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Tüm BIST sembollerini async olarak çeker.

    Args:
        start_date: Başlangıç tarihi
        progress_callback: İlerleme callback'i

    Returns:
        {symbol: DataFrame} dictionary
    """
    from data_loader import get_all_bist_symbols

    loader = BatchDataLoader()
    if progress_callback:
        loader.set_progress_callback(progress_callback)

    symbols = get_all_bist_symbols()
    return await loader.fetch_bist_batch(symbols, start_date)


async def fetch_all_crypto_async(
    progress_callback: Callable[[BatchProgress], None] | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Tüm kripto sembollerini async olarak çeker.

    Args:
        progress_callback: İlerleme callback'i

    Returns:
        {symbol: DataFrame} dictionary
    """
    from data_loader import get_all_binance_symbols

    loader = BatchDataLoader()
    if progress_callback:
        loader.set_progress_callback(progress_callback)

    symbols = get_all_binance_symbols()
    return await loader.fetch_crypto_batch(symbols)


def run_batch_fetch_bist(
    symbols: list[str] | None = None,
    start_date: str = "01-01-2015",
    progress_callback: Callable[[BatchProgress], None] | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Sync wrapper - BIST batch fetch.

    Args:
        symbols: Sembol listesi (None ise tümü)
        start_date: Başlangıç tarihi
        progress_callback: İlerleme callback'i

    Returns:
        {symbol: DataFrame} dictionary
    """
    from data_loader import get_all_bist_symbols

    if symbols is None:
        symbols = get_all_bist_symbols()

    loader = BatchDataLoader()
    if progress_callback:
        loader.set_progress_callback(progress_callback)

    return asyncio.run(loader.fetch_bist_batch(symbols, start_date))


def run_batch_fetch_crypto(
    symbols: list[str] | None = None,
    progress_callback: Callable[[BatchProgress], None] | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Sync wrapper - Kripto batch fetch.

    Args:
        symbols: Sembol listesi (None ise tümü)
        progress_callback: İlerleme callback'i

    Returns:
        {symbol: DataFrame} dictionary
    """
    from data_loader import get_all_binance_symbols

    if symbols is None:
        symbols = get_all_binance_symbols()

    loader = BatchDataLoader()
    if progress_callback:
        loader.set_progress_callback(progress_callback)

    return asyncio.run(loader.fetch_crypto_batch(symbols))
