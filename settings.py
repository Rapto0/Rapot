"""
Centralized application settings (Pydantic Settings).
All environment variables should be read from this module.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment / .env."""

    # ==================== TELEGRAM ====================
    telegram_token: str = Field(..., description="Telegram Bot Token")
    telegram_chat_id: str = Field(..., description="Telegram Chat ID")

    # ==================== BINANCE ====================
    binance_api_key: str = Field("", description="Binance API Key")
    binance_secret_key: str = Field("", description="Binance Secret Key")

    # ==================== GEMINI AI ====================
    gemini_api_key: str | None = Field(None, description="Google Gemini API Key")

    # ==================== CRYPTOPANIC ====================
    cryptopanic_api_key: str | None = Field(None, description="CryptoPanic API Key")
    finnhub_api_key: str | None = Field(None, description="Finnhub API key")
    calendar_cache_seconds: int = Field(60, ge=10, le=3600, description="Calendar cache TTL")

    # ==================== DATABASE ====================
    database_url: str | None = Field(None, description="Full DB URL (optional)")
    database_path: str = Field("trading_bot.db", description="SQLite DB file path")
    cache_database_path: str = Field("price_cache.db", description="Cache DB file path")

    # ==================== APP RUNTIME ====================
    app_env: str = Field("production", description="Runtime env: production/development/test")
    run_embedded_bot: bool = Field(False, description="Run scheduler inside API process")
    cors_allow_origins: str = Field(
        "http://localhost:3000,http://127.0.0.1:3000",
        description="Comma separated CORS origins",
    )
    cors_allow_credentials: bool = Field(True, description="Enable CORS credentials")

    # ==================== SCANNING ====================
    scan_interval_hours: int = Field(4, ge=1, le=24, description="Scan interval (hours)")
    min_data_days: int = Field(30, ge=7, description="Min data days")
    warmup_days: int = Field(60, ge=30, description="Warmup days")
    min_backtest_days: int = Field(120, ge=60, description="Min backtest days")

    # ==================== RATE LIMITS ====================
    bist_delay: float = Field(0.3, ge=0.1, description="BIST API delay (seconds)")
    crypto_delay: float = Field(0.1, ge=0.05, description="Crypto API delay (seconds)")
    telegram_delay: float = Field(0.5, ge=0.1, description="Telegram delay (seconds)")
    max_retries: int = Field(3, ge=1, le=10, description="Max retries")
    retry_wait: float = Field(2.0, ge=1.0, description="Retry wait (seconds)")

    # ==================== HEALTH API ====================
    health_api_port: int = Field(5000, ge=1024, le=65535, description="Health API port")
    health_api_host: str = Field("0.0.0.0", description="Health API host")

    # ==================== AI ====================
    ai_enabled: bool = Field(True, description="Master switch for AI analysis")
    ai_timeout: int = Field(30, ge=10, le=120, description="AI timeout (seconds)")
    ai_provider: str = Field("gemini", description="AI provider")
    ai_model: str = Field("gemini-2.5-flash", description="Default AI model")
    ai_enable_fallback: bool = Field(False, description="Enable AI fallback model")
    ai_fallback_model: str | None = Field(None, description="Fallback AI model")
    ai_temperature: float = Field(0.2, ge=0.0, le=2.0, description="AI temperature")
    ai_thinking_budget: int = Field(0, ge=0, le=24576, description="Gemini thinking budget")
    ai_max_output_tokens: int = Field(2048, ge=128, le=8192, description="AI max output tokens")

    # ==================== AUTH/JWT ====================
    jwt_secret_key: str | None = Field(None, description="JWT signing secret")
    allow_insecure_jwt_secret: bool = Field(
        False, description="Allow insecure JWT fallback only in local/dev"
    )
    jwt_expire_minutes: int = Field(1440, ge=1, le=10080, description="JWT expiry minutes")
    admin_password: str = Field("", description="Admin plaintext password (optional)")
    user_password: str = Field("", description="User plaintext password (optional)")
    admin_password_hash: str = Field("", description="Admin bcrypt/legacy hash")
    user_password_hash: str = Field("", description="User bcrypt/legacy hash")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parsed CORS origins from comma-separated setting."""
        parsed = [item.strip() for item in self.cors_allow_origins.split(",") if item.strip()]
        if not parsed:
            return ["http://localhost:3000", "http://127.0.0.1:3000"]
        return parsed


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
