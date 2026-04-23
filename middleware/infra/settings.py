from __future__ import annotations

import json
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
    broker_name: BrokerName = BrokerName.MOCK
    webhook_auth_token: str | None = None
    require_webhook_auth: bool = True
    allow_admin_endpoints: bool = True

    base_budget_tl: Decimal = Decimal("10000")
    buy_bps: int = 20
    sell_bps: int = 20
    max_open_tranches_per_symbol: int = 4

    multiplier_h_bls: Decimal = Decimal("1.00")
    multiplier_h_ucz: Decimal = Decimal("0.50")
    multiplier_c_bls: Decimal = Decimal("1.00")
    multiplier_c_ucz: Decimal = Decimal("0.50")

    default_tick_size: Decimal = Decimal("0.01")
    symbol_tick_overrides_json: str = "{}"

    max_symbol_exposure_tl: Decimal | None = None
    max_daily_loss_tl: Decimal | None = None
    max_orders_per_day: int | None = None
    allowed_symbols_csv: str | None = None
    max_signal_age_seconds: int | None = None
    max_signal_future_skew_seconds: int = 120
    require_realtime_signals: bool = False

    mock_auto_fill: bool = True

    osmanli_live_enabled: bool = False
    osmanli_base_url: str | None = None
    osmanli_token_url: str | None = None
    osmanli_account_id: str | None = None
    osmanli_client_id: str | None = None
    osmanli_client_secret: str | None = None
    osmanli_request_timeout_seconds: int = 10

    @cached_property
    def signal_multipliers(self) -> dict[str, Decimal]:
        return {
            "H_BLS": self.multiplier_h_bls,
            "H_UCZ": self.multiplier_h_ucz,
            "C_BLS": self.multiplier_c_bls,
            "C_UCZ": self.multiplier_c_ucz,
        }

    @cached_property
    def symbol_tick_overrides(self) -> dict[str, Decimal]:
        try:
            raw = json.loads(self.symbol_tick_overrides_json or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError("MW_SYMBOL_TICK_OVERRIDES_JSON must be valid JSON") from exc
        parsed: dict[str, Decimal] = {}
        if isinstance(raw, dict):
            for symbol, tick in raw.items():
                parsed[str(symbol).upper()] = Decimal(str(tick))
        return parsed

    @cached_property
    def allowed_symbols(self) -> set[str]:
        if not self.allowed_symbols_csv:
            return set()
        return {
            item.strip().upper() for item in self.allowed_symbols_csv.split(",") if item.strip()
        }

    def validate_runtime_configuration(self) -> None:
        if self.require_webhook_auth and not (self.webhook_auth_token or "").strip():
            raise ValueError("MW_WEBHOOK_AUTH_TOKEN is required when MW_REQUIRE_WEBHOOK_AUTH=true")

        is_osmanli_live = (
            self.broker_name == BrokerName.OSMANLI
            and self.execution_mode == ExecutionMode.LIVE
            and self.trading_enabled
        )
        if not is_osmanli_live:
            return

        if not self.osmanli_live_enabled:
            raise ValueError(
                "MW_OSMANLI_LIVE_ENABLED must be true before Osmanli LIVE execution is allowed"
            )

        required_fields = {
            "MW_OSMANLI_BASE_URL": self.osmanli_base_url,
            "MW_OSMANLI_TOKEN_URL": self.osmanli_token_url,
            "MW_OSMANLI_ACCOUNT_ID": self.osmanli_account_id,
            "MW_OSMANLI_CLIENT_ID": self.osmanli_client_id,
            "MW_OSMANLI_CLIENT_SECRET": self.osmanli_client_secret,
        }
        missing = [key for key, value in required_fields.items() if not (value or "").strip()]
        if missing:
            raise ValueError(
                "Missing required Osmanli LIVE configuration: " + ", ".join(sorted(missing))
            )


settings = MiddlewareSettings()
