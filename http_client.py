"""
Async HTTP Client Modülü
Gelişmiş retry mekanizması, exponential backoff ve circuit breaker.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import aiohttp

from logger import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker durumları."""

    CLOSED = "closed"  # Normal çalışma
    OPEN = "open"  # Hata durumu, istekler engellendi
    HALF_OPEN = "half_open"  # Test aşaması


@dataclass
class RetryConfig:
    """Retry konfigürasyonu."""

    max_retries: int = 3  # Maksimum deneme sayısı
    base_delay: float = 1.0  # İlk bekleme süresi (saniye)
    max_delay: float = 30.0  # Maksimum bekleme süresi
    exponential_base: float = 2.0  # Exponential artış faktörü
    jitter: bool = True  # Rastgele gecikme ekle


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker konfigürasyonu."""

    failure_threshold: int = 5  # Bu kadar hatadan sonra aç
    recovery_timeout: float = 60.0  # Bu kadar saniye sonra dene
    half_open_max_calls: int = 3  # Half-open durumunda max deneme


@dataclass
class CircuitBreaker:
    """Circuit breaker implementasyonu."""

    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: datetime | None = None
    half_open_calls: int = 0

    def record_success(self) -> None:
        """Başarılı istek kaydet."""
        self.failure_count = 0
        self.half_open_calls = 0
        if self.state != CircuitState.CLOSED:
            logger.info("Circuit breaker kapatıldı (normal çalışma)")
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Başarısız istek kaydet."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitState.HALF_OPEN:
            logger.warning("Circuit breaker açıldı (half-open test başarısız)")
            self.state = CircuitState.OPEN
        elif self.failure_count >= self.config.failure_threshold:
            logger.warning(f"Circuit breaker açıldı ({self.failure_count} başarısız istek)")
            self.state = CircuitState.OPEN

    def can_execute(self) -> bool:
        """İstek yapılabilir mi kontrol et."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Recovery timeout geçti mi?
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.config.recovery_timeout:
                    logger.info("Circuit breaker half-open durumuna geçti")
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls < self.config.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False

        return False


class AsyncHTTPClient:
    """
    Gelişmiş Async HTTP Client.

    Özellikler:
    - Exponential backoff retry
    - Circuit breaker pattern
    - Timeout yönetimi
    - Connection pooling
    """

    def __init__(
        self,
        retry_config: RetryConfig | None = None,
        circuit_config: CircuitBreakerConfig | None = None,
        timeout: float = 30.0,
    ):
        """
        Args:
            retry_config: Retry ayarları
            circuit_config: Circuit breaker ayarları
            timeout: İstek timeout süresi (saniye)
        """
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker = CircuitBreaker(config=circuit_config or CircuitBreakerConfig())
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "AsyncHTTPClient":
        """Context manager girişi."""
        self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, *args) -> None:
        """Context manager çıkışı."""
        if self._session:
            await self._session.close()

    def _calculate_delay(self, attempt: int) -> float:
        """
        Exponential backoff ile bekleme süresi hesapla.

        Args:
            attempt: Deneme numarası (0'dan başlar)

        Returns:
            Bekleme süresi (saniye)
        """
        delay = min(
            self.retry_config.base_delay * (self.retry_config.exponential_base**attempt),
            self.retry_config.max_delay,
        )

        # Jitter ekle (rastgele ±25%)
        if self.retry_config.jitter:
            import random

            jitter = delay * 0.25 * (2 * random.random() - 1)
            delay += jitter

        return max(delay, 0.1)

    async def request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> dict | list | None:
        """
        HTTP isteği yap (retry ve circuit breaker ile).

        Args:
            method: HTTP metodu (GET, POST, vb.)
            url: İstek URL'i
            **kwargs: aiohttp'ye geçirilecek ek parametreler

        Returns:
            JSON response veya None

        Raises:
            aiohttp.ClientError: Tüm retrylar başarısız olursa
        """
        if not self._session:
            raise RuntimeError("Client başlatılmadı. 'async with' kullanın.")

        # Circuit breaker kontrolü
        if not self.circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker açık, istek engellendi: {url}")
            return None

        last_exception: Exception | None = None

        for attempt in range(self.retry_config.max_retries):
            try:
                async with self._session.request(method, url, **kwargs) as response:
                    if response.status == 200:
                        self.circuit_breaker.record_success()
                        return await response.json()

                    elif response.status == 429:
                        # Rate limit - retry-after header'ı kontrol et
                        retry_after = int(response.headers.get("Retry-After", 10))
                        logger.warning(f"Rate limit! {retry_after}s bekleniyor... ({url})")
                        await asyncio.sleep(retry_after)
                        continue

                    elif response.status >= 500:
                        # Server hatası - retry
                        logger.warning(
                            f"Server hatası [{response.status}]: {url}, deneme {attempt + 1}"
                        )
                        last_exception = aiohttp.ClientResponseError(
                            response.request_info,
                            response.history,
                            status=response.status,
                        )
                    else:
                        # Client hatası - retry yapma
                        logger.error(f"Client hatası [{response.status}]: {url}")
                        self.circuit_breaker.record_failure()
                        return None

            except TimeoutError:
                logger.warning(f"Timeout: {url}, deneme {attempt + 1}")
                last_exception = TimeoutError()

            except aiohttp.ClientError as e:
                logger.warning(f"Bağlantı hatası: {url}, deneme {attempt + 1}: {e}")
                last_exception = e

            # Retry bekleme
            if attempt < self.retry_config.max_retries - 1:
                delay = self._calculate_delay(attempt)
                logger.debug(f"Retry bekleme: {delay:.2f}s")
                await asyncio.sleep(delay)

        # Tüm retrylar başarısız
        self.circuit_breaker.record_failure()
        logger.error(f"Tüm retrylar başarısız: {url}")

        if last_exception:
            raise last_exception
        return None

    async def get(self, url: str, **kwargs: Any) -> dict | list | None:
        """GET isteği."""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> dict | list | None:
        """POST isteği."""
        return await self.request("POST", url, **kwargs)

    async def get_with_fallback(
        self,
        url: str,
        fallback_url: str | None = None,
        **kwargs: Any,
    ) -> dict | list | None:
        """
        GET isteği - fallback URL ile.

        Args:
            url: Ana URL
            fallback_url: Yedek URL (opsiyonel)
            **kwargs: Ek parametreler

        Returns:
            JSON response veya None
        """
        try:
            result = await self.get(url, **kwargs)
            if result is not None:
                return result
        except Exception as e:
            logger.warning(f"Ana URL başarısız: {e}")

        if fallback_url:
            logger.info(f"Fallback URL deneniyor: {fallback_url}")
            try:
                return await self.get(fallback_url, **kwargs)
            except Exception as e:
                logger.error(f"Fallback URL de başarısız: {e}")

        return None


# ==================== CONVENIENCE FUNCTIONS ====================


async def fetch_json(url: str, timeout: float = 30.0) -> dict | list | None:
    """
    Basit JSON fetch fonksiyonu.

    Args:
        url: İstek URL'i
        timeout: Timeout süresi

    Returns:
        JSON response veya None
    """
    async with AsyncHTTPClient(timeout=timeout) as client:
        return await client.get(url)


async def fetch_multiple(
    urls: list[str],
    timeout: float = 30.0,
    max_concurrent: int = 10,
) -> dict[str, dict | list | None]:
    """
    Birden fazla URL'i paralel fetch et.

    Args:
        urls: URL listesi
        timeout: Timeout süresi
        max_concurrent: Maksimum eşzamanlı istek

    Returns:
        {url: response} dictionary
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    results: dict[str, dict | list | None] = {}

    async def fetch_one(url: str) -> None:
        async with semaphore:
            try:
                async with AsyncHTTPClient(timeout=timeout) as client:
                    results[url] = await client.get(url)
            except Exception as e:
                logger.error(f"Fetch hatası ({url}): {e}")
                results[url] = None

    await asyncio.gather(*[fetch_one(url) for url in urls])
    return results
