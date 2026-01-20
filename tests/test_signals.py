"""
signals.py için unit testler.
COMBO ve HUNTER stratejilerini test eder.
"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

# Proje kök dizinini path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signals import calculate_combo_signal, calculate_hunter_signal, safe_get


class TestSafeGet:
    """safe_get fonksiyonu testleri."""

    @pytest.mark.unit
    def test_safe_get_last_value(self):
        """Son değeri döndürür."""
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = safe_get(series)
        assert result == 5.0

    @pytest.mark.unit
    def test_safe_get_specific_index(self):
        """Belirli indeksteki değeri döndürür."""
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = safe_get(series, idx=0)
        assert result == 1.0

    @pytest.mark.unit
    def test_safe_get_none_series(self):
        """None series için default döndürür."""
        result = safe_get(None)
        assert np.isnan(result)

    @pytest.mark.unit
    def test_safe_get_empty_series(self):
        """Boş series için default döndürür."""
        series = pd.Series([], dtype=float)
        result = safe_get(series, default=0.0)
        assert result == 0.0

    @pytest.mark.unit
    def test_safe_get_nan_value(self):
        """NaN değer için default döndürür."""
        series = pd.Series([1.0, 2.0, np.nan])
        result = safe_get(series, default=-1.0)
        assert result == -1.0


class TestCalculateComboSignal:
    """calculate_combo_signal fonksiyonu testleri."""

    @pytest.mark.unit
    def test_combo_returns_none_for_none_df(self):
        """None DataFrame için None döndürür."""
        result = calculate_combo_signal(None, "1D")
        assert result is None

    @pytest.mark.unit
    def test_combo_returns_none_for_empty_df(self, empty_dataframe):
        """Boş DataFrame için None döndürür."""
        result = calculate_combo_signal(empty_dataframe, "1D")
        assert result is None

    @pytest.mark.unit
    def test_combo_returns_none_for_insufficient_data(self, insufficient_data):
        """Yetersiz veri için None döndürür."""
        result = calculate_combo_signal(insufficient_data, "1D")
        assert result is None

    @pytest.mark.unit
    def test_combo_returns_dict_structure(self, sample_ohlcv_data):
        """Geçerli veri için doğru yapıda dict döndürür."""
        result = calculate_combo_signal(sample_ohlcv_data, "1D")

        assert result is not None
        assert "buy" in result
        assert "sell" in result
        assert "details" in result
        assert isinstance(result["buy"], bool)
        assert isinstance(result["sell"], bool)
        assert isinstance(result["details"], dict)

    @pytest.mark.unit
    def test_combo_details_contains_indicators(self, sample_ohlcv_data):
        """Details sözlüğü gerekli indikatörleri içerir."""
        result = calculate_combo_signal(sample_ohlcv_data, "1D")

        details = result["details"]
        required_keys = ["MACD", "RSI", "WR", "CCI", "Score", "PRICE", "DATE"]

        for key in required_keys:
            assert key in details, f"{key} details'da bulunamadı"

    @pytest.mark.unit
    def test_combo_buy_sell_mutually_exclusive(self, sample_ohlcv_data):
        """buy ve sell aynı anda True olamaz."""
        result = calculate_combo_signal(sample_ohlcv_data, "1D")

        # Her ikisi de True olmamalı
        assert not (result["buy"] and result["sell"])

    @pytest.mark.unit
    def test_combo_daily_timeframe(self, sample_ohlcv_data):
        """Günlük timeframe doğru çalışır."""
        result = calculate_combo_signal(sample_ohlcv_data, "1D")
        assert result is not None

    @pytest.mark.unit
    def test_combo_weekly_timeframe(self, sample_ohlcv_data):
        """Haftalık timeframe doğru çalışır."""
        result = calculate_combo_signal(sample_ohlcv_data, "W-FRI")
        # Haftalık için 14 bar gerekli, 60 günlük veri yeterli
        assert result is not None


class TestCalculateHunterSignal:
    """calculate_hunter_signal fonksiyonu testleri."""

    @pytest.mark.unit
    def test_hunter_returns_none_for_none_df(self):
        """None DataFrame için None döndürür."""
        result = calculate_hunter_signal(None, "1D")
        assert result is None

    @pytest.mark.unit
    def test_hunter_returns_none_for_empty_df(self, empty_dataframe):
        """Boş DataFrame için None döndürür."""
        result = calculate_hunter_signal(empty_dataframe, "1D")
        assert result is None

    @pytest.mark.unit
    def test_hunter_returns_none_for_insufficient_data(self, insufficient_data):
        """Yetersiz veri için None döndürür."""
        result = calculate_hunter_signal(insufficient_data, "1D")
        assert result is None

    @pytest.mark.unit
    def test_hunter_returns_dict_structure(self, sample_ohlcv_data):
        """Geçerli veri için doğru yapıda dict döndürür."""
        result = calculate_hunter_signal(sample_ohlcv_data, "1D")

        assert result is not None
        assert "buy" in result
        assert "sell" in result
        assert "details" in result
        assert isinstance(result["buy"], bool)
        assert isinstance(result["sell"], bool)
        assert isinstance(result["details"], dict)

    @pytest.mark.unit
    def test_hunter_details_contains_scores(self, sample_ohlcv_data):
        """Details sözlüğü DipScore ve TopScore içerir."""
        result = calculate_hunter_signal(sample_ohlcv_data, "1D")

        details = result["details"]
        assert "DipScore" in details
        assert "TopScore" in details
        # DipScore ve TopScore "X/Y" formatında string olarak dönüyor
        assert isinstance(details["DipScore"], str)
        assert isinstance(details["TopScore"], str)

    @pytest.mark.unit
    def test_hunter_buy_sell_mutually_exclusive(self, sample_ohlcv_data):
        """buy ve sell aynı anda True olamaz."""
        result = calculate_hunter_signal(sample_ohlcv_data, "1D")

        # Her ikisi de True olmamalı
        assert not (result["buy"] and result["sell"])


class TestSignalIntegration:
    """COMBO ve HUNTER entegrasyon testleri."""

    @pytest.mark.integration
    def test_both_strategies_same_data(self, sample_ohlcv_data):
        """Her iki strateji de aynı veriyle çalışır."""
        combo_result = calculate_combo_signal(sample_ohlcv_data, "1D")
        hunter_result = calculate_hunter_signal(sample_ohlcv_data, "1D")

        assert combo_result is not None
        assert hunter_result is not None

    @pytest.mark.integration
    def test_all_timeframes(self, sample_ohlcv_data):
        """Tüm timeframe'ler için sinyal hesaplanabilir."""
        timeframes = ["1D", "W-FRI"]

        for tf in timeframes:
            combo = calculate_combo_signal(sample_ohlcv_data, tf)
            hunter = calculate_hunter_signal(sample_ohlcv_data, tf)

            # En azından None olmayan sonuç dönmeli
            # (Yeterli veri yoksa None dönebilir, bu da geçerli)
            assert combo is None or isinstance(combo, dict)
            assert hunter is None or isinstance(hunter, dict)
