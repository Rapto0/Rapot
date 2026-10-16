"""Dated pay membership is distinct from explicit instruments and issuer research."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from application.services import bist_share_universe as registry
from application.services.advanced_alarm_data_provider import NativeMarketProvider
from application.services.advanced_alarm_market_data import AdvancedMarketData
from bist_service import BISTDataService
from tests.test_advanced_alarm_market_data import MemoryCache, rule


def test_packaged_registry_has_exact_partition_and_dated_provenance():
    snapshot = registry.share_universe()
    assert len(snapshot.symbols) == len(set(snapshot.symbols)) == 631
    assert len(snapshot.separated) == 174
    assert not set(snapshot.symbols).intersection(symbol for symbol, _ in snapshot.separated)
    metadata = snapshot.metadata()
    assert metadata["audit_as_of"] == "2026-10-12"
    assert metadata["official_corroborated_at"] == "2026-10-14T07:19:45.376269+00:00"
    assert metadata["separated_candidate_classifications"] == {
        "KAP alternatif kurum kodu": 12,
        "Borçlanma aracı ihraççısı": 124,
        "Yapılandırılmış ürün ihraççısı": 4,
        "Gayrimenkul sertifikası": 1,
        "Emtia sertifikası ihraççısı": 1,
        "Hisse kodu eşleşmesi yok": 32,
    }
    assert metadata["equity_membership_verified"] is True
    assert metadata["provider_resolution_verified"] is False
    assert metadata["live_trading_status_verified"] is False
    assert metadata["future_membership_guaranteed"] is False
    assert metadata["automatic_refresh"] is False
    metadata["separated_candidate_classifications"].clear()
    assert snapshot.metadata()["separated_candidate_classifications"]


def test_changed_or_missing_registry_cannot_fall_back_to_issuers(monkeypatch, tmp_path):
    path = tmp_path / "snapshot.json"
    with monkeypatch.context() as patch:
        patch.setattr(registry, "SNAPSHOT_PATH", path)
        registry.share_universe.cache_clear()
        with pytest.raises(FileNotFoundError):
            registry.share_universe()
        path.write_text('{"symbols": ["ACP"]}', encoding="utf-8")
        with pytest.raises(ValueError, match="özeti eşleşmiyor"):
            registry.share_universe()
    registry.share_universe.cache_clear()
    assert len(registry.share_universe().symbols) == 631


def test_all_universe_consumers_share_membership_without_provider_calls():
    gateway = SimpleNamespace(run_public=Mock(side_effect=AssertionError("unexpected network")))
    provider = NativeMarketProvider(gateway)
    first = provider.universe()
    assert first == list(registry.share_universe().symbols)
    first.clear()
    assert len(provider.universe()) == 631
    assert BISTDataService()._symbols == provider.universe()
    gateway.run_public.assert_not_called()


def test_old_candidate_cache_is_filtered_without_restricting_explicit_mixed_rules(tmp_path):
    snapshot = registry.share_universe()
    gateway = SimpleNamespace(
        run_public=Mock(side_effect=AssertionError("unexpected network")),
        memory_epoch=lambda: 1,
        create_alarm_quote_stream=Mock(return_value=object()),
    )
    provider = NativeMarketProvider(gateway)
    settings = SimpleNamespace(
        database_path=str(tmp_path / "main.sqlite3"),
        advanced_alarm_cache_path=None,
        advanced_alarm_market_enabled=True,
        advanced_alarm_all_bist_enabled=True,
        advanced_alarm_max_symbols=2000,
        advanced_alarm_history_workers=1,
        advanced_alarm_quote_stale_seconds=120,
    )
    hub = AdvancedMarketData(settings, provider=provider, cache=MemoryCache(), clock=lambda: 100)
    cached = [*snapshot.symbols, *(symbol for symbol, _ in snapshot.separated)]
    assert len(cached) == 805
    hub._set_universe(cached)
    selected = {
        **rule(),
        "symbols": [
            {"market_type": "BIST", "symbol": "ACP"},
            {"market_type": "Kripto", "symbol": "BTCUSDT"},
        ],
    }
    hub.configure([selected, {**rule(), "id": 2, "scope": "all_bist", "symbols": []}])
    assert hub.symbol_count(2) == 631
    assert {row["symbol"] for row in hub.symbols(2)} == set(snapshot.symbols)
    assert hub.symbols(1) == tuple(selected["symbols"])
    assert hub._explicit_bist == {"ACP"} and hub._crypto == {"BTCUSDT"}
    # Provider admission is independent: an explicit non-share instrument is not stripped.
    callback = Mock()
    provider.open_quotes(["THYAO", "ACP"], callback)
    gateway.create_alarm_quote_stream.assert_called_once_with(["THYAO", "ACP"], callback)
    proof = hub.coverage()
    assert proof["universe"]["candidate_count"] == 631
    assert proof["universe"]["separated_candidate_count"] == 174
    assert proof["universe"]["equity_membership_verified"] is True
    assert proof["universe"]["universe_complete"] is True
    status = hub.status()
    assert status["universe_as_of"] == "2026-10-12"
    assert status["universe_source"] == "kap_verified_share_snapshot"
    assert status["universe_source_count"] == status["universe_count"] == 631
    assert status["universe_equity_membership_verified"] is True
    extra = next(row for row in proof["rows"] if row["symbol"] == "ACP")
    assert extra["explicit"] and not extra["candidate"]
    gateway.run_public.assert_not_called()
