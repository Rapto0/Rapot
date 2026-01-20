"""
Telegram Bildirim Modülü
Gelişmiş rate limiting, mesaj kuyruğu ve exponential backoff.
"""

import threading
import time
from dataclasses import dataclass
from enum import Enum
from queue import Empty, Queue

import requests

from config import rate_limits
from settings import settings

# Logger - circular import'u önlemek için lazy import
_logger = None


def get_tg_logger():
    global _logger
    if _logger is None:
        from logger import get_logger

        _logger = get_logger(__name__)
    return _logger


# Telegram credentials - settings.py'den alınıyor
TOKEN = settings.telegram_token
CHAT_ID = settings.telegram_chat_id


class MessagePriority(Enum):
    """Mesaj öncelik seviyeleri"""

    LOW = 0  # Normal sinyaller
    NORMAL = 1  # Standart mesajlar
    HIGH = 2  # Önemli sinyaller (ÇOK UCUZ, BELEŞ vb.)
    CRITICAL = 3  # Hata bildirimleri, acil durumlar


@dataclass
class TelegramMessage:
    """Kuyrukta bekleyen mesaj"""

    text: str
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class TelegramRateLimiter:
    """
    Gelişmiş Telegram Rate Limiter
    - Mesaj kuyruğu
    - Exponential backoff
    - Öncelik sıralaması
    - Burst koruma
    """

    # Telegram limitleri
    MESSAGES_PER_SECOND = 1  # Kişisel chat için 1 msg/sn
    MESSAGES_PER_MINUTE = 20  # Güvenli limit
    MIN_DELAY = 0.5  # Minimum bekleme (saniye)
    MAX_DELAY = 60  # Maximum bekleme (saniye)

    def __init__(self):
        self._lock = threading.Lock()
        self._last_send_time = 0.0
        self._message_count_minute = 0
        self._minute_start = time.time()
        self._current_delay = self.MIN_DELAY
        self._consecutive_errors = 0
        self._last_update_id = 0

        # Mesaj kuyruğu
        self._queue: Queue[TelegramMessage] = Queue(maxsize=100)
        self._queue_thread: threading.Thread | None = None
        self._running = False

    def start_queue_worker(self):
        """Arka plan mesaj işleyicisini başlat"""
        if self._queue_thread is None or not self._queue_thread.is_alive():
            self._running = True
            self._queue_thread = threading.Thread(target=self._process_queue, daemon=True)
            self._queue_thread.start()
            get_tg_logger().info("Telegram kuyruk işleyici başlatıldı")

    def stop_queue_worker(self):
        """Kuyruk işleyicisini durdur"""
        self._running = False
        if self._queue_thread:
            self._queue_thread.join(timeout=5)

    def _process_queue(self):
        """Kuyruktaki mesajları işle"""
        while self._running:
            try:
                msg = self._queue.get(timeout=1)
                self._send_with_rate_limit(msg.text)
                self._queue.task_done()
            except Empty:
                continue
            except Exception as e:
                get_tg_logger().error(f"Kuyruk işleme hatası: {e}")

    def _check_minute_limit(self) -> bool:
        """Dakikalık limite ulaşılmış mı?"""
        current_time = time.time()

        # Yeni dakika başladıysa sayacı sıfırla
        if current_time - self._minute_start >= 60:
            self._minute_start = current_time
            self._message_count_minute = 0

        return self._message_count_minute < self.MESSAGES_PER_MINUTE

    def _calculate_delay(self) -> float:
        """Exponential backoff ile bekleme süresi hesapla"""
        if self._consecutive_errors == 0:
            return self.MIN_DELAY

        # Her hatada 2x artır, max'ı geçme
        delay = min(self.MIN_DELAY * (2**self._consecutive_errors), self.MAX_DELAY)
        return delay

    def _send_with_rate_limit(self, message: str) -> bool:
        """Rate limit uygulayarak mesaj gönder"""
        if not TOKEN or not CHAT_ID:
            get_tg_logger().warning("Telegram ayarları eksik!")
            return False

        with self._lock:
            # Dakikalık limit kontrolü
            if not self._check_minute_limit():
                wait_time = 60 - (time.time() - self._minute_start)
                get_tg_logger().warning(f"Dakikalık limit aşıldı, {wait_time:.0f}sn bekleniyor")
                time.sleep(wait_time)
                self._minute_start = time.time()
                self._message_count_minute = 0

            # Son gönderimden bu yana geçen süre
            elapsed = time.time() - self._last_send_time
            required_delay = self._calculate_delay()

            if elapsed < required_delay:
                time.sleep(required_delay - elapsed)

        # Mesajı gönder
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}

        max_retries = rate_limits.MAX_RETRIES

        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, timeout=15)

                if response.status_code == 200:
                    with self._lock:
                        self._last_send_time = time.time()
                        self._message_count_minute += 1
                        self._consecutive_errors = 0
                        self._current_delay = self.MIN_DELAY
                    return True

                elif response.status_code == 429:
                    # Rate limit - Telegram'ın söylediği süre kadar bekle
                    data = response.json()
                    retry_after = data.get("parameters", {}).get("retry_after", 10)
                    get_tg_logger().warning(f"Telegram rate limit! {retry_after}sn bekleniyor...")

                    with self._lock:
                        self._consecutive_errors += 1

                    time.sleep(retry_after + 1)
                    continue

                else:
                    get_tg_logger().error(
                        f"Telegram hatası [{response.status_code}]: {response.text[:100]}"
                    )
                    with self._lock:
                        self._consecutive_errors += 1
                    return False

            except requests.exceptions.Timeout:
                get_tg_logger().warning(f"Telegram timeout, deneme {attempt + 1}/{max_retries}")
                with self._lock:
                    self._consecutive_errors += 1
                time.sleep(self._calculate_delay())

            except requests.exceptions.RequestException as e:
                get_tg_logger().error(f"Telegram bağlantı hatası: {e}")
                with self._lock:
                    self._consecutive_errors += 1
                time.sleep(self._calculate_delay())

        return False

    def send(
        self,
        message: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        use_queue: bool = True,
    ) -> bool:
        """
        Mesaj gönder

        Args:
            message: Gönderilecek mesaj
            priority: Mesaj önceliği
            use_queue: True ise kuyruğa ekle, False ise direkt gönder

        Returns:
            True if successful
        """
        if use_queue and self._running:
            try:
                msg = TelegramMessage(text=message, priority=priority)
                self._queue.put_nowait(msg)
                return True
            except Exception:
                # Kuyruk doluysa direkt gönder
                pass

        return self._send_with_rate_limit(message)

    def get_updates(self) -> list[str]:
        """Yeni mesajları al (thread-safe)"""
        if not TOKEN:
            return []

        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

        with self._lock:
            params = {"offset": self._last_update_id + 1, "timeout": 1}

        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                result = response.json().get("result", [])
                messages: list[str] = []

                with self._lock:
                    for update in result:
                        self._last_update_id = update["update_id"]
                        if "message" in update and "text" in update["message"]:
                            messages.append(update["message"]["text"])

                return messages
        except requests.exceptions.RequestException as e:
            get_tg_logger().debug(f"Get updates hatası: {e}")

        return []

    @property
    def queue_size(self) -> int:
        """Kuyrukta bekleyen mesaj sayısı"""
        return self._queue.qsize()

    @property
    def stats(self) -> dict:
        """Rate limiter istatistikleri"""
        with self._lock:
            return {
                "queue_size": self._queue.qsize(),
                "messages_this_minute": self._message_count_minute,
                "current_delay": self._current_delay,
                "consecutive_errors": self._consecutive_errors,
            }


# Global rate limiter instance
_rate_limiter = TelegramRateLimiter()


def send_message(message: str, priority: MessagePriority = MessagePriority.NORMAL) -> bool:
    """
    Telegram'a mesaj gönderir (rate limit korumalı).

    Args:
        message: Gönderilecek mesaj
        priority: Mesaj önceliği

    Returns:
        True if successful
    """
    return _rate_limiter.send(message, priority, use_queue=False)


def send_message_async(message: str, priority: MessagePriority = MessagePriority.NORMAL):
    """Mesajı kuyruğa ekle (non-blocking)"""
    _rate_limiter.start_queue_worker()
    _rate_limiter.send(message, priority, use_queue=True)


def get_last_messages() -> list[str]:
    """Son gelen mesajları kontrol eder (thread-safe)."""
    return _rate_limiter.get_updates()


def get_telegram_stats() -> dict:
    """Telegram rate limiter istatistiklerini döndürür."""
    return _rate_limiter.stats
