"""
config.py için unit testler.
Konfigürasyon değerlerinin doğruluğunu test eder.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    MIN_PERIODS,
    TIMEFRAMES,
    combo_thresholds,
    hunter_thresholds,
    rate_limits,
    scan_settings,
)


class TestRateLimits:
    """RateLimits konfigürasyon testleri."""

    @pytest.mark.unit
    def test_rate_limits_exist(self):
        """Rate limit değerleri mevcut."""
        assert rate_limits.BIST_DELAY > 0
        assert rate_limits.CRYPTO_DELAY > 0
        assert rate_limits.TELEGRAM_DELAY > 0
        assert rate_limits.MAX_RETRIES > 0
        assert rate_limits.RETRY_WAIT > 0

    @pytest.mark.unit
    def test_rate_limits_immutable(self):
        """RateLimits frozen dataclass."""
        with pytest.raises(Exception):
            rate_limits.BIST_DELAY = 999


class TestScanSettings:
    """ScanSettings konfigürasyon testleri."""

    @pytest.mark.unit
    def test_scan_interval_reasonable(self):
        """Tarama aralığı mantıklı (1-24 saat)."""
        assert 1 <= scan_settings.SCAN_INTERVAL_HOURS <= 24

    @pytest.mark.unit
    def test_min_data_days_positive(self):
        """Minimum veri günü pozitif."""
        assert scan_settings.MIN_DATA_DAYS > 0


class TestMinPeriods:
    """MIN_PERIODS konfigürasyon testleri."""

    @pytest.mark.unit
    def test_all_timeframes_have_min_periods(self):
        """Tüm timeframe'ler için minimum periyot tanımlı."""
        expected_timeframes = ["1D", "W-FRI", "2W-FRI", "3W-FRI", "ME"]

        for tf in expected_timeframes:
            # En az bir eşleşme olmalı
            found = any(tf in key for key in MIN_PERIODS.keys())
            assert found or tf in MIN_PERIODS, f"{tf} için min period bulunamadı"

    @pytest.mark.unit
    def test_min_periods_positive(self):
        """Tüm minimum periyotlar pozitif."""
        for tf, period in MIN_PERIODS.items():
            assert period > 0, f"{tf} için period negatif: {period}"


class TestTimeframes:
    """TIMEFRAMES konfigürasyon testleri."""

    @pytest.mark.unit
    def test_timeframes_not_empty(self):
        """Timeframe listesi boş değil."""
        assert len(TIMEFRAMES) > 0

    @pytest.mark.unit
    def test_timeframes_tuple_structure(self):
        """Her timeframe (kod, label) tuple'ı."""
        for item in TIMEFRAMES:
            assert isinstance(item, tuple)
            assert len(item) == 2
            code, label = item
            assert isinstance(code, str)
            assert isinstance(label, str)


class TestThresholds:
    """Strateji eşik değerleri testleri."""

    @pytest.mark.unit
    def test_combo_rsi_thresholds_valid(self):
        """COMBO RSI eşikleri 0-100 arasında."""
        assert 0 <= combo_thresholds.RSI_OVERSOLD <= 100
        assert 0 <= combo_thresholds.RSI_OVERBOUGHT <= 100
        assert combo_thresholds.RSI_OVERSOLD < combo_thresholds.RSI_OVERBOUGHT

    @pytest.mark.unit
    def test_hunter_rsi_thresholds_valid(self):
        """HUNTER RSI eşikleri 0-100 arasında."""
        assert 0 <= hunter_thresholds.RSI_DIP <= 100
        assert 0 <= hunter_thresholds.RSI_TOP <= 100
        assert hunter_thresholds.RSI_DIP < hunter_thresholds.RSI_TOP
