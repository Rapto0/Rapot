"""
Merkezi Konfigürasyon Dosyası
Tüm sabit değerler ve ayarlar burada tutulur.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimits:
    """API rate limit ayarları (saniye cinsinden)"""

    BIST_DELAY: float = 0.3
    CRYPTO_DELAY: float = 0.1
    TELEGRAM_DELAY: float = 0.5
    MAX_RETRIES: int = 3
    RETRY_WAIT: float = 2.0


@dataclass(frozen=True)
class ScanSettings:
    """Tarama ayarları"""

    SCAN_INTERVAL_HOURS: int = 4
    MIN_DATA_DAYS: int = 30
    WARMUP_DAYS: int = 60
    MIN_BACKTEST_DAYS: int = 120


@dataclass(frozen=True)
class ComboThresholds:
    """COMBO stratejisi eşik değerleri"""

    # Günlük
    DAILY_BUY_LIMIT: int = 4
    DAILY_SELL_LIMIT: int = 3
    # Haftalık
    WEEKLY_BUY_LIMIT: int = 4
    WEEKLY_SELL_LIMIT: int = 3
    # Diğer periyotlar
    OTHER_BUY_LIMIT: int = 3
    OTHER_SELL_LIMIT: int = 3

    # İndikatör eşikleri
    MACD_BUY: float = 0.0  # < 0 ise AL
    MACD_SELL: float = 0.0  # > 0 ise SAT
    RSI_OVERSOLD: float = 40.0
    RSI_OVERBOUGHT: float = 80.0
    WR_OVERSOLD: float = -80.0
    WR_OVERBOUGHT: float = -10.0
    CCI_OVERSOLD: float = -100.0
    CCI_OVERBOUGHT: float = 200.0


@dataclass(frozen=True)
class HunterThresholds:
    """HUNTER stratejisi eşik değerleri"""

    # Dip/Tepe gereksinimleri
    DAILY_DIP_REQ: int = 7
    DAILY_TOP_REQ: int = 10
    WEEKLY_DIP_REQ: int = 7
    WEEKLY_TOP_REQ: int = 10
    BIWEEKLY_DIP_REQ: int = 7
    BIWEEKLY_TOP_REQ: int = 10
    TRIWEEKLY_DIP_REQ: int = 5
    TRIWEEKLY_TOP_REQ: int = 10
    MONTHLY_DIP_REQ: int = 5
    MONTHLY_TOP_REQ: int = 10

    # İndikatör eşikleri
    RSI_DIP: float = 30.0
    RSI_TOP: float = 70.0
    RSI_FAST_DIP: float = 20.0
    RSI_FAST_TOP: float = 80.0
    CMO_DIP: float = -50.0
    CMO_TOP: float = 50.0
    BOP_DIP: float = -0.7
    BOP_TOP: float = 0.7


@dataclass(frozen=True)
class BacktestSettings:
    """Backtest ayarları"""

    BIST_INITIAL_CASH: float = 100000.0
    CRYPTO_INITIAL_CASH: float = 20000.0
    BIST_TRADE_AMOUNT: float = 1000.0
    CRYPTO_TRADE_AMOUNT: float = 100.0
    START_DATE: str = "2006-01-01"


# Minimum periyot gereksinimleri (timeframe bazlı)
MIN_PERIODS: dict[str, int] = {
    "1D": 30,
    "D": 30,
    "Daily": 30,
    "W-FRI": 14,
    "2W-FRI": 10,
    "3W-FRI": 8,
    "ME": 8,
}

# Zaman dilimleri
TIMEFRAMES: list[tuple[str, str]] = [
    ("1D", "GÜNLÜK"),
    ("W-FRI", "1 HAFTALIK"),
    ("2W-FRI", "2 HAFTALIK"),
    ("3W-FRI", "3 HAFTALIK"),
    ("ME", "1 AYLIK"),
]


# Global config instances
rate_limits = RateLimits()
scan_settings = ScanSettings()
combo_thresholds = ComboThresholds()
hunter_thresholds = HunterThresholds()
backtest_settings = BacktestSettings()
