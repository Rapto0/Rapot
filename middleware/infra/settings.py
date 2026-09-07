from __future__ import annotations

import re
from decimal import Decimal
from functools import cached_property
from typing import Any
from urllib.parse import urlparse

from pydantic import field_validator
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
    inventory_account_id: str | None = None
    webhook_auth_token: str | None = None
    require_webhook_auth: bool = True
    allow_admin_endpoints: bool = True
    admin_auth_token: str | None = None

    buy_bps: int = 20
    sell_bps: int = 20
    max_open_tranches_per_symbol: int | None = None

    multiplier_h_bls: Decimal = Decimal("1.00")
    multiplier_h_ucz: Decimal = Decimal("1.00")
    multiplier_c_bls: Decimal = Decimal("1.00")
    multiplier_c_ucz: Decimal = Decimal("1.00")

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
    binance_buy_quote_amount_usdt: Decimal = Decimal("10")
    binance_quote_asset: str = "USDT"
    binance_dry_run_auto_fill: bool = True
    binance_check_balance: bool = True

    @field_validator(
        "webhook_auth_token",
        "admin_auth_token",
        "inventory_account_id",
        "max_open_tranches_per_symbol",
        "max_symbol_exposure_usdt",
        "max_daily_loss_usdt",
        "max_orders_per_day",
        "allowed_symbols_csv",
        "max_signal_age_seconds",
        "binance_api_key",
        "binance_secret_key",
        mode="before",
    )
    @classmethod
    def _blank_string_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in {"prod", "production"}

    @staticmethod
    def _scope_part(value: str, *, setting: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", normalized):
            raise ValueError(f"{setting} must use 1-64 letters, numbers, '.', '_' or '-'")
        return normalized

    @property
    def inventory_scope(self) -> str:
        """Stable non-secret boundary for orders, risk totals, and open inventory."""
        mode = self.execution_mode.value
        broker = self.broker_name.value
        if self.execution_mode == ExecutionMode.DRY_RUN:
            environment = self._scope_part(self.app_env, setting="MW_APP_ENV")
            account = self._scope_part(
                self.inventory_account_id or "simulation-default",
                setting="MW_INVENTORY_ACCOUNT_ID",
            )
            return f"{mode}|{broker}|{environment}|{account}"

        account_id = self.inventory_account_id
        if not account_id:
            raise ValueError("MW_INVENTORY_ACCOUNT_ID is required in LIVE mode")
        hostname = (urlparse(self.binance_base_url).hostname or "").strip().lower()
        if not hostname:
            raise ValueError("MW_BINANCE_BASE_URL must include a hostname in LIVE mode")
        venue = self._scope_part(hostname, setting="MW_BINANCE_BASE_URL hostname")
        account = self._scope_part(account_id, setting="MW_INVENTORY_ACCOUNT_ID")
        return f"{mode}|{broker}|{venue}|{account}"

    @cached_property
    def signal_multipliers(self) -> dict[str, Decimal]:
        return {
            "H_BLS": self.multiplier_h_bls,
            "H_UCZ": self.multiplier_h_ucz,
            "C_BLS": self.multiplier_c_bls,
            "C_UCZ": self.multiplier_c_ucz,
        }

    def quote_budget_for_signal(self, signal_code: str) -> Decimal:
        return self.binance_buy_quote_amount_usdt * self.signal_multipliers[signal_code]

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

        # Resolve on every startup so LIVE can never operate in an implicit account scope.
        _ = self.inventory_scope

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
