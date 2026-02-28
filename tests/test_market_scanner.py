"""
market_scanner.py için unit testler.
ScannerState ve yardımcı fonksiyonları test eder.
"""

import json
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market_scanner import (
    ScannerState,
    format_ai_message_for_telegram,
    format_combo_debug,
    format_hunter_debug,
    generate_manual_report,
    process_symbol,
)


class TestScannerState:
    """ScannerState class testleri."""

    @pytest.mark.unit
    def test_initial_counts_zero(self):
        """Başlangıç sayaçları sıfır."""
        state = ScannerState()
        assert state.scan_count == 0
        assert state.signal_count == 0

    @pytest.mark.unit
    def test_increment_scan(self):
        """Tarama sayacı artırılabilir."""
        state = ScannerState()
        result = state.increment_scan()
        assert result == 1
        assert state.scan_count == 1

    @pytest.mark.unit
    def test_increment_signal(self):
        """Sinyal sayacı artırılabilir."""
        state = ScannerState()
        result = state.increment_signal()
        assert result == 1
        assert state.signal_count == 1

    @pytest.mark.unit
    def test_multiple_increments(self):
        """Birden fazla artırma doğru çalışır."""
        state = ScannerState()
        for _ in range(5):
            state.increment_scan()
        assert state.scan_count == 5


class TestFormatFunctions:
    """Format fonksiyonları testleri."""

    @pytest.fixture
    def combo_details(self):
        """Örnek COMBO details verisi."""
        return {
            "DATE": "2024-01-15",
            "PRICE": 100.50,
            "MACD": 0.0025,
            "RSI": 35.5,
            "WR": -75.0,
            "CCI": -120.5,
            "Score": "+3/-1",
        }

    @pytest.fixture
    def hunter_details(self):
        """Örnek HUNTER details verisi."""
        return {
            "DATE": "2024-01-15",
            "PRICE": 100.50,
            "RSI": 30.0,
            "RSI_Fast": 25.0,
            "CMO": -55.0,
            "BOP": -0.8,
            "MACD": -0.5,
            "W%R": -85.0,
            "CCI": -150.0,
            "ULT": 30.0,
            "BBP": 10.0,
            "ROC": -5.0,
            "DipScore": 8,
            "TopScore": 2,
        }

    @pytest.mark.unit
    def test_format_combo_debug_returns_string(self, combo_details):
        """format_combo_debug string döndürür."""
        result = format_combo_debug(combo_details)
        assert isinstance(result, str)
        assert "COMBO" in result

    @pytest.mark.unit
    def test_format_combo_debug_contains_values(self, combo_details):
        """format_combo_debug değerleri içerir."""
        result = format_combo_debug(combo_details)
        assert "MACD" in result
        assert "RSI" in result

    @pytest.mark.unit
    def test_format_hunter_debug_returns_string(self, hunter_details):
        """format_hunter_debug string döndürür."""
        result = format_hunter_debug(hunter_details)
        assert isinstance(result, str)
        assert "HUNTER" in result


class TestGenerateManualReport:
    """generate_manual_report fonksiyonu testleri."""

    @pytest.fixture
    def combo_result(self):
        """Örnek COMBO sonucu."""
        return {
            "buy": True,
            "sell": False,
            "details": {"PRICE": 100.50, "MACD": 0.0025, "RSI": 35.5, "Score": "+4/-1"},
        }

    @pytest.fixture
    def hunter_result(self):
        """Örnek HUNTER sonucu."""
        return {"buy": True, "sell": False, "details": {"DipScore": 8, "TopScore": 2}}

    @pytest.mark.unit
    def test_generate_report_returns_string(self, combo_result, hunter_result):
        """generate_manual_report string döndürür."""
        result = generate_manual_report("THYAO", "BIST", combo_result, hunter_result)
        assert isinstance(result, str)

    @pytest.mark.unit
    def test_generate_report_contains_symbol(self, combo_result, hunter_result):
        """Rapor sembol adını içerir."""
        result = generate_manual_report("THYAO", "BIST", combo_result, hunter_result)
        assert "THYAO" in result

    @pytest.mark.unit
    def test_generate_report_contains_market(self, combo_result, hunter_result):
        """Rapor piyasa türünü içerir."""
        result = generate_manual_report("BTCUSDT", "Kripto", combo_result, hunter_result)
        assert "Kripto" in result


class TestFormatAIMessageForTelegram:
    """AI JSON -> Telegram format dönüşüm testleri."""

    @pytest.mark.unit
    def test_formats_structured_json(self):
        payload = {
            "sentiment_score": 30,
            "sentiment_label": "SAT",
            "summary": [
                "RSI aşırı alım bölgesinde.",
                "HUNTER göstergesi pahalı sinyali veriyor.",
                "Haber akışı kısa vadede oynaklık yaratabilir.",
            ],
            "explanation": "Teknik göstergeler kısa vadede satış baskısına işaret ediyor.",
            "key_levels": {"support": ["21.50", "20.80"], "resistance": ["22.50", "23.00"]},
            "risk_level": "Orta",
        }

        result = format_ai_message_for_telegram("AYES", json.dumps(payload))

        assert "AI KARARI (AYES)" in result
        assert "<b>SAT</b>" in result
        assert "Öne Çıkanlar" in result
        assert "Destek: 21.50, 20.80" in result
        assert '"sentiment_score"' not in result

    @pytest.mark.unit
    def test_handles_error_payload(self):
        result = format_ai_message_for_telegram(
            "AYES", json.dumps({"error": "Timeout", "error_code": "timeout", "sentiment_score": 50})
        )

        assert "AI analizi üretilemedi: Timeout (timeout)" in result

    @pytest.mark.unit
    def test_fallback_for_non_json(self):
        result = format_ai_message_for_telegram("AYES", "Düz metin AI yanıtı")
        assert "Düz metin AI yanıtı" in result


class TestTelegramSignalFiltering:
    @pytest.mark.unit
    def test_regular_timeframe_signals_do_not_send_telegram(self, monkeypatch):
        df = pd.DataFrame({"Close": [1.0] * 30})
        sent_messages = []
        saved_signals = []

        monkeypatch.setattr("market_scanner.TIMEFRAMES", [("1D", "GÜNLÜK")])
        monkeypatch.setattr("market_scanner.resample_data", lambda current_df, tf: current_df)
        monkeypatch.setattr(
            "market_scanner.calculate_combo_signal",
            lambda current_df, tf: {
                "buy": True,
                "sell": False,
                "details": {"Score": "+4/-0", "PRICE": 10, "DATE": "2026-02-28"},
            },
        )
        monkeypatch.setattr(
            "market_scanner.calculate_hunter_signal",
            lambda current_df, tf: {
                "buy": True,
                "sell": False,
                "details": {"DipScore": "7/7", "PRICE": 10, "DATE": "2026-02-28"},
            },
        )
        monkeypatch.setattr(
            "market_scanner.db_save_signal", lambda **kwargs: saved_signals.append(kwargs)
        )
        monkeypatch.setattr("market_scanner.increment_signal_count", lambda: None)
        monkeypatch.setattr("market_scanner.send_message", sent_messages.append)

        process_symbol(df, "THYAO", "BIST")

        assert len(saved_signals) == 2
        assert sent_messages == []

    @pytest.mark.unit
    def test_special_signals_still_send_ai_messages(self, monkeypatch):
        df = pd.DataFrame({"Close": [1.0] * 30})
        sent_messages = []
        saved_signals = []
        tagged_signals = []

        monkeypatch.setattr(
            "market_scanner.TIMEFRAMES",
            [("1D", "GÜNLÜK"), ("W-FRI", "1 HAFTALIK"), ("3W-FRI", "3 HAFTALIK")],
        )
        monkeypatch.setattr("market_scanner.resample_data", lambda current_df, tf: current_df)
        monkeypatch.setattr(
            "market_scanner.calculate_combo_signal",
            lambda current_df, tf: {
                "buy": True,
                "sell": False,
                "details": {"Score": "+4/-0", "PRICE": 10, "DATE": "2026-02-28"},
            },
        )
        monkeypatch.setattr(
            "market_scanner.calculate_hunter_signal",
            lambda current_df, tf: {
                "buy": False,
                "sell": False,
                "details": {
                    "DipScore": "0/7",
                    "TopScore": "0/10",
                    "PRICE": 10,
                    "DATE": "2026-02-28",
                },
            },
        )
        monkeypatch.setattr(
            "market_scanner.db_save_signal", lambda **kwargs: saved_signals.append(kwargs)
        )
        monkeypatch.setattr("market_scanner.increment_signal_count", lambda: None)
        monkeypatch.setattr("market_scanner.send_message", sent_messages.append)
        monkeypatch.setattr("market_scanner.fetch_market_news", lambda symbol, market_type: [])
        monkeypatch.setattr(
            "market_scanner.analyze_with_gemini", lambda **kwargs: '{"summary":["ok"]}'
        )
        monkeypatch.setattr(
            "market_scanner.inspect_strategy_dataframe",
            lambda **kwargs: {
                "symbol": "THYAO",
                "market_type": "BIST",
                "strategy": "COMBO",
                "indicator_order": ["MACD", "RSI", "WR", "CCI"],
                "indicator_labels": {
                    "MACD": "MACD",
                    "RSI": "RSI (14)",
                    "WR": "W%R",
                    "CCI": "CCI (20)",
                },
                "generated_at": "2026-02-28T12:00:00Z",
                "timeframes": [],
            },
        )
        monkeypatch.setattr(
            "market_scanner.build_strategy_ai_payload",
            lambda **kwargs: {"timeframes": [], "special_tag": "COK_UCUZ"},
        )
        monkeypatch.setattr(
            "market_scanner.db_set_signal_special_tag",
            lambda **kwargs: tagged_signals.append(kwargs) or True,
        )

        process_symbol(df, "THYAO", "BIST")

        assert len(saved_signals) == 3
        assert tagged_signals
        assert any("AI; Teknik ve Haberleri inceliyor" in message for message in sent_messages)

    @pytest.mark.unit
    def test_special_signal_ai_uses_multitimeframe_payload(self, monkeypatch):
        df = pd.DataFrame({"Close": [1.0] * 30})
        sent_messages = []
        builder_calls = []
        ai_calls = []

        monkeypatch.setattr(
            "market_scanner.TIMEFRAMES",
            [("1D", "GUNLUK"), ("2W-FRI", "2 HAFTALIK"), ("ME", "1 AYLIK")],
        )
        monkeypatch.setattr("market_scanner.resample_data", lambda current_df, tf: current_df)
        monkeypatch.setattr(
            "market_scanner.calculate_combo_signal",
            lambda current_df, tf: {
                "buy": True,
                "sell": False,
                "details": {"Score": "+4/-0", "PRICE": 10, "DATE": "2026-02-28"},
            },
        )
        monkeypatch.setattr(
            "market_scanner.calculate_hunter_signal",
            lambda current_df, tf: {
                "buy": False,
                "sell": False,
                "details": {
                    "DipScore": "0/7",
                    "TopScore": "0/10",
                    "PRICE": 10,
                    "DATE": "2026-02-28",
                },
            },
        )
        monkeypatch.setattr("market_scanner.db_save_signal", lambda **kwargs: None)
        monkeypatch.setattr("market_scanner.increment_signal_count", lambda: None)
        monkeypatch.setattr("market_scanner.send_message", sent_messages.append)
        monkeypatch.setattr("market_scanner.fetch_market_news", lambda symbol, market_type: [])
        monkeypatch.setattr("market_scanner.db_set_signal_special_tag", lambda **kwargs: True)
        monkeypatch.setattr(
            "market_scanner.inspect_strategy_dataframe",
            lambda **kwargs: {
                "symbol": "THYAO",
                "market_type": "BIST",
                "strategy": "COMBO",
                "indicator_order": ["MACD", "RSI", "WR", "CCI"],
                "indicator_labels": {
                    "MACD": "MACD",
                    "RSI": "RSI (14)",
                    "WR": "W%R",
                    "CCI": "CCI (20)",
                },
                "generated_at": "2026-02-28T12:00:00Z",
                "timeframes": [
                    {
                        "code": "1D",
                        "label": "GUNLUK",
                        "available": True,
                        "signal_status": "AL",
                        "reason": None,
                        "price": 10,
                        "date": "2026-02-28",
                        "active_indicators": "4/4",
                        "primary_score": "4/4",
                        "primary_score_label": "AL Skoru",
                        "secondary_score": "0/3",
                        "secondary_score_label": "SAT Skoru",
                        "raw_score": "+4/-0",
                        "indicators": {"MACD": -1, "RSI": 25, "WR": -90, "CCI": -120},
                    },
                    {
                        "code": "2W-FRI",
                        "label": "2 HAFTALIK",
                        "available": True,
                        "signal_status": "AL",
                        "reason": None,
                        "price": 10,
                        "date": "2026-02-28",
                        "active_indicators": "4/4",
                        "primary_score": "4/3",
                        "primary_score_label": "AL Skoru",
                        "secondary_score": "0/3",
                        "secondary_score_label": "SAT Skoru",
                        "raw_score": "+4/-0",
                        "indicators": {"MACD": -1, "RSI": 25, "WR": -90, "CCI": -120},
                    },
                    {
                        "code": "ME",
                        "label": "1 AYLIK",
                        "available": True,
                        "signal_status": "AL",
                        "reason": None,
                        "price": 10,
                        "date": "2026-02-28",
                        "active_indicators": "4/4",
                        "primary_score": "3/3",
                        "primary_score_label": "AL Skoru",
                        "secondary_score": "0/3",
                        "secondary_score_label": "SAT Skoru",
                        "raw_score": "+4/-0",
                        "indicators": {"MACD": -1, "RSI": 25, "WR": -90, "CCI": -120},
                    },
                ],
            },
        )

        def fake_build_strategy_ai_payload(**kwargs):
            builder_calls.append(kwargs)
            return {
                "strategy": "COMBO",
                "special_tag": "BELES",
                "trigger_rule": ["1D", "2W-FRI", "ME"],
                "matched_timeframes": [{"code": "1D"}, {"code": "2W-FRI"}, {"code": "ME"}],
                "timeframes": [{"code": "1D"}, {"code": "2W-FRI"}, {"code": "ME"}],
            }

        monkeypatch.setattr(
            "market_scanner.build_strategy_ai_payload", fake_build_strategy_ai_payload
        )
        monkeypatch.setattr(
            "market_scanner.analyze_with_gemini",
            lambda **kwargs: ai_calls.append(kwargs) or '{"summary":["ok"]}',
        )

        process_symbol(df, "THYAO", "BIST")

        assert builder_calls
        assert builder_calls[0]["special_tag"] == "BELES"
        assert builder_calls[0]["trigger_rule"] == ["1D", "2W-FRI", "ME"]
        assert ai_calls
        assert ai_calls[0]["technical_data"]["special_tag"] == "BELES"
        assert ai_calls[0]["technical_data"]["trigger_rule"] == ["1D", "2W-FRI", "ME"]
        assert any("AI; Teknik ve Haberleri inceliyor" in message for message in sent_messages)
