from __future__ import annotations

from middleware.broker_adapters.base import BrokerClient
from middleware.broker_adapters.binance_spot import BinanceSpotBrokerClient
from middleware.domain.enums import BrokerName
from middleware.domain.errors import UnsupportedBrokerError
from middleware.infra.settings import MiddlewareSettings


def build_broker_client(cfg: MiddlewareSettings) -> BrokerClient:
    if cfg.broker_name == BrokerName.BINANCE_SPOT:
        return BinanceSpotBrokerClient(cfg=cfg)

    raise UnsupportedBrokerError(f"unsupported broker: {cfg.broker_name}")
