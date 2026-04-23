from __future__ import annotations

from middleware.broker_adapters.base import BrokerClient
from middleware.broker_adapters.mock_broker import MockBrokerClient
from middleware.broker_adapters.osmanli import OsmanliBrokerClient
from middleware.domain.enums import BrokerName
from middleware.domain.errors import UnsupportedBrokerError
from middleware.infra.settings import MiddlewareSettings


def build_broker_client(cfg: MiddlewareSettings) -> BrokerClient:
    if cfg.broker_name == BrokerName.MOCK:
        return MockBrokerClient(auto_fill=cfg.mock_auto_fill)

    if cfg.broker_name == BrokerName.OSMANLI:
        return OsmanliBrokerClient(cfg=cfg)

    raise UnsupportedBrokerError(f"unsupported broker: {cfg.broker_name}")
