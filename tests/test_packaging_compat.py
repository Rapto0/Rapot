from api.repositories.analysis_repository import get_ai_analysis_by_id as legacy_analysis
from api.services.analysis_service import get_ai_analysis_by_id as legacy_analysis_service
from application.scanner.signal_handlers import (
    persist_and_publish_signal_event as app_persist_and_publish_signal_event,
)
from application.services.analysis_service import get_ai_analysis_by_id as app_analysis
from domain.events import SignalDomainEvent as DomainSignalDomainEvent
from infrastructure.persistence.ops_repository import get_bot_stat as infra_get_bot_stat
from infrastructure.persistence.signal_repository import save_signal as infra_save_signal
from infrastructure.persistence.trade_repository import create_trade as infra_create_trade
from infrastructure.repositories.analysis_repository import get_ai_analysis_by_id as infra_analysis
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
    assert legacy_analysis_service is app_analysis


def test_api_repository_wrapper_alias_points_to_infrastructure_module():
    assert legacy_analysis is infra_analysis


def test_scanner_side_effect_wrapper_alias_points_to_application_module():
    assert legacy_persist_and_publish_signal_event is app_persist_and_publish_signal_event
