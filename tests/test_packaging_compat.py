from api.repositories.system_repository import (
    get_ops_overview_read_model as legacy_get_ops_overview_read_model,
)
from api.services.system_service import get_ops_overview as legacy_get_ops_overview
from application.scanner.signal_handlers import (
    persist_and_publish_signal_event as app_persist_and_publish_signal_event,
)
from application.services.system_service import get_ops_overview as app_get_ops_overview
from domain.events import SignalDomainEvent as DomainSignalDomainEvent
from infrastructure.persistence.ops_repository import get_bot_stat as infra_get_bot_stat
from infrastructure.persistence.signal_repository import save_signal as infra_save_signal
from infrastructure.persistence.trade_repository import create_trade as infra_create_trade
from infrastructure.repositories.system_repository import (
    get_ops_overview_read_model as infra_get_ops_overview_read_model,
)
from ops_repository import get_bot_stat as legacy_get_bot_stat
from scanner_events import SignalDomainEvent as LegacySignalDomainEvent
from scanner_side_effects import (
    persist_and_publish_signal_event as legacy_persist_and_publish_signal_event,
)
from signal_repository import save_signal as legacy_save_signal
from trade_repository import create_trade as legacy_create_trade


def test_signal_domain_event_legacy_alias_points_to_domain_class():
    assert LegacySignalDomainEvent is DomainSignalDomainEvent


def test_signal_repository_legacy_alias_points_to_infrastructure_module():
    assert legacy_save_signal is infra_save_signal


def test_trade_repository_legacy_alias_points_to_infrastructure_module():
    assert legacy_create_trade is infra_create_trade


def test_ops_repository_legacy_alias_points_to_infrastructure_module():
    assert legacy_get_bot_stat is infra_get_bot_stat


def test_api_service_wrapper_alias_points_to_application_module():
    assert legacy_get_ops_overview is app_get_ops_overview


def test_api_repository_wrapper_alias_points_to_infrastructure_module():
    assert legacy_get_ops_overview_read_model is infra_get_ops_overview_read_model


def test_scanner_side_effect_wrapper_alias_points_to_application_module():
    assert legacy_persist_and_publish_signal_event is app_persist_and_publish_signal_event
