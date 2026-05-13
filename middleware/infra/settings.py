from __future__ import annotations

from decimal import Decimal
from functools import cached_property

from pydantic_settings import BaseSettings, SettingsConfigDict

from middleware.domain.enums import BrokerName, ExecutionMode


class MiddlewareSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MW_",
        env_file=("middleware/.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "rapot-trading-middleware"
    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/rapot_middleware"
    trading_enabled: bool = False
    execution_mode: ExecutionMode = ExecutionMode.DRY_RUN
    broker_name: BrokerName = BrokerName.BINANCE_SPOT
    webhook_auth_token: str | None = None
    require_webhook_auth: bool = True
    allow_admin_endpoints: bool = True

    buy_bps: int = 20
    sell_bps: int = 20
    max_open_tranches_per_symbol: int = 4

    multiplier_h_bls: Decimal = Decimal("1.00")
    multiplier_h_ucz: Decimal = Decimal("0.50")
    multiplier_c_bls: Decimal = Decimal("1.00")
    multiplier_c_ucz: Decimal = Decimal("0.50")

    max_symbol_exposure_usdt: Decimal | None = None
    max_daily_loss_usdt: Decimal | None = None
    max_orders_per_day: int | None = None
    allowed_symbols_csv: str | None = None
    max_signal_age_seconds: int | None = None
    max_signal_future_skew_seconds: int = 120
    require_realtime_signals: bool = False

    binance_live_enabled: bool = False
    binance_base_url: str = "https://testnet.binance.vision"
    binance_api_key: str | None = None
    binance_secret_key: str | None = None
    binance_request_timeout_seconds: int = 10
    binance_recv_window_ms: int = 5000
    binance_buy_quote_amount_usdt: Decimal = Decimal("25")
    binance_quote_asset: str = "USDT"
    binance_dry_run_auto_fill: bool = True
    binance_check_balance: bool = True

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in {"prod", "production"}

    @cached_property
    def signal_multipliers(self) -> dict[str, Decimal]:
        return {
            "H_BLS": self.multiplier_h_bls,
            "H_UCZ": self.multiplier_h_ucz,
            "C_BLS": self.multiplier_c_bls,
            "C_UCZ": self.multiplier_c_ucz,
        }

    @cached_property
    def allowed_symbols(self) -> set[str]:
        if not self.allowed_symbols_csv:
            return set()
        return {
            item.strip().upper() for item in self.allowed_symbols_csv.split(",") if item.strip()
        }

    def validate_runtime_configuration(self) -> None:
        if self.is_production and not self.require_webhook_auth:
            raise ValueError("MW_REQUIRE_WEBHOOK_AUTH cannot be false in production")

        if self.require_webhook_auth and not (self.webhook_auth_token or "").strip():
            raise ValueError("MW_WEBHOOK_AUTH_TOKEN is required when MW_REQUIRE_WEBHOOK_AUTH=true")

        is_binance_live = (
            self.broker_name == BrokerName.BINANCE_SPOT
            and self.execution_mode == ExecutionMode.LIVE
            and self.trading_enabled
        )
        if not is_binance_live:
            return

        if not self.binance_live_enabled:
            raise ValueError(
                "MW_BINANCE_LIVE_ENABLED must be true before Binance LIVE execution is allowed"
            )

        required_binance = {
            "MW_BINANCE_API_KEY": self.binance_api_key,
            "MW_BINANCE_SECRET_KEY": self.binance_secret_key,
        }
        missing_binance = [
            key for key, value in required_binance.items() if not (value or "").strip()
        ]
        if missing_binance:
            raise ValueError(
                "Missing required Binance LIVE configuration: " + ", ".join(sorted(missing_binance))
            )


settings = MiddlewareSettings()
