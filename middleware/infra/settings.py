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

    mock_auto_fill: bool = True

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


settings = MiddlewareSettings()
