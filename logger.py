"""
Merkezi Logging Modülü
Rotating file handler ile profesyonel log yönetimi.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(
    name: str = "trading_bot",
    log_file: str = "trading_bot.log",
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """
    Merkezi logger oluşturur.

    Args:
        name: Logger ismi
        log_file: Log dosyası yolu
        console_level: Konsol log seviyesi (varsayılan: INFO)
        file_level: Dosya log seviyesi (varsayılan: DEBUG)
        max_bytes: Maksimum dosya boyutu (byte)
        backup_count: Saklanacak eski log sayısı

    Returns:
        Yapılandırılmış Logger instance
    """
    logger = logging.getLogger(name)

    # Zaten handler varsa tekrar ekleme
    if logger.handlers:
        return logger

    # En düşük seviyeyi ayarla (DEBUG)
    logger.setLevel(logging.DEBUG)

    # Format
    detailed_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    simple_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%H:%M:%S"
    )

    # Logs klasörü oluştur
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # File handler (rotating) - DEBUG seviyesi
    file_handler = RotatingFileHandler(
        log_dir / log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)

    # Error file handler - sadece ERROR ve üstü
    error_handler = RotatingFileHandler(
        log_dir / "errors.log", maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)

    # Console handler - INFO seviyesi
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)

    # Telegram handler - sadece CRITICAL
    try:
        telegram_handler = TelegramHandler()
        telegram_handler.setLevel(logging.CRITICAL)
        telegram_handler.setFormatter(simple_formatter)
        logger.addHandler(telegram_handler)
    except Exception:
        pass  # Telegram ayarları yoksa sessizce geç

    return logger


class TelegramHandler(logging.Handler):
    """
    Kritik hataları Telegram'a gönderen handler.
    Rate limiting ile spam önlenir.
    """

    def __init__(self, min_interval: int = 60):
        """
        Args:
            min_interval: Aynı mesaj için minimum bekleme süresi (saniye)
        """
        super().__init__()
        self._last_sent = {}
        self._min_interval = min_interval
        self._lock = __import__("threading").Lock()

    def emit(self, record):
        """Log kaydını Telegram'a gönderir."""
        try:
            import time

            import requests

            # Lazy import to avoid circular import with settings
            from settings import settings

            token = settings.telegram_token
            chat_id = settings.telegram_chat_id

            if not token or not chat_id:
                return

            # Rate limiting - aynı hatayı tekrar gönderme
            msg_key = f"{record.filename}:{record.lineno}"
            current_time = time.time()

            with self._lock:
                if msg_key in self._last_sent:
                    if current_time - self._last_sent[msg_key] < self._min_interval:
                        return
                self._last_sent[msg_key] = current_time

            # Mesaj formatla
            emoji = "🚨" if record.levelno >= logging.CRITICAL else "❌"
            msg = (
                f"{emoji} <b>KRİTİK HATA</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📁 {record.filename}:{record.lineno}\n"
                f"⚠️ {record.getMessage()[:500]}\n"
                f"🕐 {self.formatter.formatTime(record) if self.formatter else ''}"
            )

            # Telegram'a gönder (async değil, blocking)
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(
                url, data={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=5
            )

        except Exception:
            pass  # Handler hatası loglanmamalı (infinite loop riski)


def get_logger(module_name: str) -> logging.Logger:
    """
    Modül bazlı child logger döndürür.
    Parent logger'ın handler'larını kullanır.

    Args:
        module_name: Modül adı (genellikle __name__)

    Returns:
        Child logger instance
    """
    # Parent logger'ın kurulduğundan emin ol
    parent = logging.getLogger("trading_bot")
    if not parent.handlers:
        setup_logger()

    return logging.getLogger(f"trading_bot.{module_name}")


def send_critical_alert(message: str) -> None:
    """
    Manuel kritik hata bildirimi.

    Args:
        message: Hata mesajı
    """
    logger = logging.getLogger("trading_bot")
    logger.critical(message)


# İlk import'ta logger'ı kur
_main_logger = setup_logger()
