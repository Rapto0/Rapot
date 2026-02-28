"""
Merkezi Ayar Yönetimi - Pydantic Settings
Tüm environment değişkenleri ve konfigürasyonlar burada yönetilir.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Uygulama ayarları.
    .env dosyasından veya environment variables'dan okunur.
    """

    # ==================== TELEGRAM ====================
    telegram_token: str = Field(..., description="Telegram Bot Token")
    telegram_chat_id: str = Field(..., description="Telegram Chat ID")

    # ==================== BINANCE (Opsiyonel - Kripto için) ====================
    binance_api_key: str = Field("", description="Binance API Key (kripto için gerekli)")
    binance_secret_key: str = Field("", description="Binance Secret Key (kripto için gerekli)")

    # ==================== GEMINI AI ====================
    gemini_api_key: str | None = Field(None, description="Google Gemini API Key (opsiyonel)")

    # ==================== CRYPTOPANIC (Haber API) ====================
    cryptopanic_api_key: str | None = Field(
        None, description="CryptoPanic API Key (opsiyonel, haber çekme için)"
    )

    # ==================== DATABASE ====================
    database_path: str = Field("trading_bot.db", description="SQLite veritabanı dosya yolu")
    cache_database_path: str = Field("price_cache.db", description="Cache veritabanı dosya yolu")

    # ==================== SCANNING ====================
    scan_interval_hours: int = Field(4, ge=1, le=24, description="Tarama aralığı (saat)")
    min_data_days: int = Field(30, ge=7, description="Minimum veri günü")
    warmup_days: int = Field(60, ge=30, description="Warmup günü")
    min_backtest_days: int = Field(120, ge=60, description="Minimum backtest günü")

    # ==================== RATE LIMITS ====================
    bist_delay: float = Field(0.3, ge=0.1, description="BIST API gecikme (saniye)")
    crypto_delay: float = Field(0.1, ge=0.05, description="Kripto API gecikme (saniye)")
    telegram_delay: float = Field(0.5, ge=0.1, description="Telegram mesaj gecikme (saniye)")
    max_retries: int = Field(3, ge=1, le=10, description="Maksimum yeniden deneme")
    retry_wait: float = Field(2.0, ge=1.0, description="Yeniden deneme bekleme (saniye)")

    # ==================== HEALTH API ====================
    health_api_port: int = Field(5000, ge=1024, le=65535, description="Health API portu")
    health_api_host: str = Field("0.0.0.0", description="Health API host")

    # ==================== AI ====================
    ai_timeout: int = Field(30, ge=10, le=120, description="AI analiz timeout (saniye)")
    ai_provider: str = Field("gemini", description="AI provider (ornek: gemini)")
    ai_model: str = Field("gemini-2.5-flash", description="Varsayilan AI model adi")
    ai_fallback_model: str | None = Field(
        "gemini-2.5-flash-lite", description="Birincil model basarisiz olursa denenecek model"
    )
    ai_temperature: float = Field(0.2, ge=0.0, le=2.0, description="AI sicaklik degeri")
    ai_max_output_tokens: int = Field(
        1024, ge=128, le=8192, description="AI maksimum cikti token limiti"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """
    Singleton pattern ile settings döndürür.
    lru_cache ile sadece bir kez yüklenir.
    """
    return Settings()


# Global erişim için
settings = get_settings()
