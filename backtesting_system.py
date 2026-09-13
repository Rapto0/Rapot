import math
import multiprocessing
import traceback
import warnings
from collections import deque
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from isyatirimhisse import fetch_stock_data

from data_loader import (
    get_crypto_data,
    resample_market_data,
)
from infrastructure.time import utc_now_naive
from isyatirim_ssl import ensure_isyatirim_ca_bundle
from signals import calculate_combo_signal, calculate_hunter_signal

warnings.filterwarnings("ignore")


def get_bist_data_isyatirim_only(
    symbol: str, start_date: str = "01-01-2006"
) -> pd.DataFrame | None:
    """
    Backtest tarafında BIST verisini yalnızca İş Yatırım kaynağından kabul eder.
    """
    ensure_isyatirim_ca_bundle()

    try:
        raw_df = fetch_stock_data(symbols=[symbol], start_date=start_date)
    except Exception as exc:
        print(f"[WARN] {symbol}: Is Yatirim veri cekimi basarisiz: {exc}")
        return None

    if raw_df is None or raw_df.empty:
        print(f"[WARN] {symbol}: Is Yatirim veri kaynaginda veri bulunamadi.")
        return None

    rename_map = {
        "HGDG_TARIH": "Date",
        "HGDG_KAPANIS": "Close",
        "HGDG_MIN": "Low",
        "HGDG_MAX": "High",
        "HGDG_HACIM": "Volume",
    }
    df = raw_df.rename(columns=rename_map).copy()

    if "Date" not in df.columns:
        print(f"[WARN] {symbol}: Is Yatirim verisinde tarih kolonu bulunamadi.")
        return None

    open_candidates = (
        "HGDG_ACILIS",
        "HGDG_ACIK",
        "HGDG_OPEN",
        "ACILIS",
        "ACIK",
        "OPEN",
        "HGDG_AOF",
        "HG_AOF",
    )

    open_quality = "provider"
    discovered_open = next((column for column in open_candidates if column in raw_df.columns), None)
    if discovered_open is not None:
        df["Open"] = raw_df[discovered_open]
        if discovered_open in {"HGDG_AOF", "HG_AOF"}:
            open_quality = "aof_proxy"
    elif "Close" in df.columns:
        df["Open"] = df["Close"]
        open_quality = "close_proxy"
    else:
        print(f"[WARN] {symbol}: Is Yatirim verisinde Open/Close kolonu bulunamadi.")
        return None

    required = ("Open", "High", "Low", "Close", "Volume")
    missing = [column for column in required if column not in df.columns]
    if missing:
        print(f"[WARN] {symbol}: Is Yatirim verisinde eksik kolonlar: {', '.join(missing)}")
        return None

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).set_index("Date")

    for column in required:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df[list(required)].dropna().sort_index()
    if df.empty:
        print(f"[WARN] {symbol}: Is Yatirim verisi normalize sonrasi bos kaldi.")
        return None

    fetched_at = utc_now_naive().isoformat()
    df.attrs["source_hint"] = "isyatirim"
    df.attrs["open_quality"] = open_quality
    df.attrs["fetched_at_iso"] = fetched_at

    return df


# ============================================================
# İŞLEM MALİYETLERİ KONFÜGÜRASYONU
# ============================================================
@dataclass
class TradingCosts:
    """Tek yönlü, referans tutar üzerinden toplamsal backtest varsayımları.

    Komisyon ve kayma ayrı nakit maliyetleridir; gerçekleşme fiyatı modeli veya
    güncel bir aracı kurum ücret tarifesi değildir.
    """

    bist_commission: float = 0.001
    crypto_commission: float = 0.001
    bist_slippage: float = 0.0005
    crypto_slippage: float = 0.0003

    def __post_init__(self) -> None:
        self.get_components("BIST")
        self.get_components("CRYPTO")

    def get_components(self, market_type: str) -> tuple[float, float]:
        """Değiştirilebilir ayarları her işlemden önce yeniden doğrula."""
        if market_type == "BIST":
            commission, slippage = self.bist_commission, self.bist_slippage
        elif market_type == "CRYPTO":
            commission, slippage = self.crypto_commission, self.crypto_slippage
        else:
            raise ValueError("market_type must be BIST or CRYPTO")
        if not all(_finite_nonnegative(value) for value in (commission, slippage)):
            raise ValueError("Cost rates must be finite and nonnegative")
        if commission + slippage >= 1:
            raise ValueError("Combined one-way cost rate must be below one")
        return commission, slippage

    def get_total_cost(self, market_type: str) -> float:
        """Toplam işlem maliyeti (tek yön)"""
        return sum(self.get_components(market_type))


def _finite_nonnegative(value: float) -> bool:
    try:
        return not isinstance(value, bool) and math.isfinite(value) and value >= 0
    except (TypeError, ValueError, OverflowError):
        return False


def _valid_trade_input(price: float, date: datetime) -> bool:
    return (
        _finite_nonnegative(price)
        and price > 0
        and isinstance(date, datetime)
        and not pd.isna(date)
    )


# Global trading costs instance
trading_costs = TradingCosts()


class Lot:
    """Tek alışın miktarı, referans fiyatı ve tüm alış maliyetleri."""

    def __init__(
        self,
        symbol: str,
        shares: float,
        price: float,
        date: datetime,
        signal: str,
        *,
        commission: float = 0.0,
        slippage: float = 0.0,
    ) -> None:
        self.symbol = symbol
        self.shares = shares
        self.price = price
        self.date = date
        self.signal = signal
        self.commission = commission
        self.slippage = slippage
        self.invested = shares * price + commission + slippage


class Portfolio:
    """FIFO mantığıyla lot bazlı portföy yönetimi - Komisyon destekli"""

    def __init__(
        self,
        initial_cash: float,
        market_type: str,
        trade_amount: float,
        costs: TradingCosts | None = None,
    ) -> None:
        if not all(
            _finite_nonnegative(value) and value > 0 for value in (initial_cash, trade_amount)
        ):
            raise ValueError("Initial cash and trade amount must be finite and positive")
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self._cash_compensation = 0.0
        self.market_type = market_type
        self.trade_amount = trade_amount
        self.costs = costs or trading_costs
        self.costs.get_components(market_type)

        # Sembol bazlı lot kuyrukları (FIFO için)
        self.lots = {}  # {symbol: deque([Lot1, Lot2, ...])}

        # Tüm işlemler
        self.all_trades = []

        # Sembol bazlı performans
        self.symbol_performance = {}

        # Portföy değeri takibi
        self.equity_curve = []

        # Kayma komisyon değildir; iki gider ayrı izlenir.
        self.total_commission_paid = 0.0
        self.total_slippage_cost = 0.0

    @property
    def total_transaction_cost(self) -> float:
        return self.total_commission_paid + self.total_slippage_cost

    def _cash_after(self, amount: float) -> tuple[float, float]:
        """Kahan toplamıyla çok sayıda kesirli nakit hareketinin hatasını sınırla."""
        adjusted = amount - self._cash_compensation
        balance = self.cash + adjusted
        return balance, (balance - self.cash) - adjusted

    def buy(self, symbol: str, price: float, date: datetime, signal_type: str) -> bool:
        """Sabit bütçenin içinde referans tutar, komisyon ve kayma bulunur."""
        if not isinstance(symbol, str) or not symbol.strip() or not _valid_trade_input(price, date):
            return False
        commission_rate, slippage_rate = self.costs.get_components(self.market_type)
        cost_rate = commission_rate + slippage_rate
        if not _finite_nonnegative(self.trade_amount) or self.trade_amount <= 0:
            return False
        if not _finite_nonnegative(self.cash):
            return False
        balance, compensation = self._cash_after(-self.trade_amount)
        if balance < 0:
            # Temsil artığı için ULP sınırını ayrıca mevcut bütçeye göre daralt.
            tolerance = min(
                8
                * max(
                    math.ulp(value) for value in (self.initial_cash, self.cash, self.trade_amount)
                ),
                self.trade_amount * 1e-12,
            )
            if balance < -tolerance:
                return False
            balance, compensation = 0.0, 0.0

        shares = self.trade_amount / (price * (1 + cost_rate))
        gross_cost = shares * price
        commission = gross_cost * commission_rate
        slippage = gross_cost * slippage_rate
        if not all(_finite_nonnegative(value) and value > 0 for value in (shares, gross_cost)):
            return False
        # Bütçe doğrudan kullanılır; float çarpımındaki son bit nakdi eksiye indirmez.
        actual_cost = self.trade_amount
        new_lot = Lot(
            symbol, shares, price, date, signal_type, commission=commission, slippage=slippage
        )
        new_lot.invested = actual_cost
        if not all(
            _finite_nonnegative(value)
            for value in (
                balance,
                self.total_commission_paid + commission,
                self.total_slippage_cost + slippage,
            )
        ):
            return False

        # Nakit düş
        self.cash, self._cash_compensation = balance, compensation
        self.total_commission_paid += commission
        self.total_slippage_cost += slippage

        # Sembol için kuyruk yoksa oluştur
        if symbol not in self.lots:
            self.lots[symbol] = deque()

        # Kuyruğa ekle
        self.lots[symbol].append(new_lot)

        # İşlemi kaydet
        self.all_trades.append(
            {
                "Tarih": date,
                "Sembol": symbol,
                "İşlem": "ALIM",
                "Fiyat": round(price, 4),
                "Miktar": round(shares, 6),
                "Tutar": round(gross_cost, 2),
                "Komisyon": round(commission, 2),
                "Kayma Maliyeti": round(slippage, 2),
                "Toplam İşlem Maliyeti": round(commission + slippage, 2),
                "Maliyet Tabanı": round(actual_cost, 2),
                "Nakit Akışı": round(-actual_cost, 2),
                "Sinyal": signal_type,
                "Kalan Nakit": round(self.cash, 2),
                "Toplam Lot": len(self.lots[symbol]),
            }
        )

        return True

    def sell(self, symbol: str, price: float, date: datetime, signal_type: str) -> bool:
        """En eski lot'u sat (FIFO) - Komisyon dahil"""

        # Sembol için lot var mı?
        if (
            not isinstance(symbol, str)
            or not symbol.strip()
            or not _valid_trade_input(price, date)
            or not self.lots.get(symbol)
        ):
            return False

        # Hesaplama/validasyon hatası FIFO kuyruğundan lot kaybettirmemeli.
        oldest_lot = self.lots[symbol][0]
        commission_rate, slippage_rate = self.costs.get_components(self.market_type)
        try:
            if date < oldest_lot.date:
                return False
            holding_days = (date - oldest_lot.date).days
        except (TypeError, ValueError, OverflowError):
            return False

        # İki gider de aynı referans tutardan düşülür; kayma ikinci kez fiyatlanmaz.
        gross_revenue = oldest_lot.shares * price
        commission = gross_revenue * commission_rate
        slippage = gross_revenue * slippage_rate
        net_revenue = gross_revenue - commission - slippage
        if not all(_finite_nonnegative(value) for value in (gross_revenue, net_revenue)):
            return False

        # Kar/Zarar (komisyonlar dahil)
        profit = net_revenue - oldest_lot.invested
        profit_pct = (profit / oldest_lot.invested) * 100
        if not math.isfinite(profit) or not math.isfinite(profit_pct):
            return False
        balance, compensation = self._cash_after(net_revenue)
        if not all(
            _finite_nonnegative(value)
            for value in (
                balance,
                self.total_commission_paid + commission,
                self.total_slippage_cost + slippage,
            )
        ):
            return False

        # Nakde ekle
        self.lots[symbol].popleft()
        self.cash, self._cash_compensation = balance, compensation
        self.total_commission_paid += commission
        self.total_slippage_cost += slippage

        # İşlemi kaydet
        self.all_trades.append(
            {
                "Tarih": date,
                "Sembol": symbol,
                "İşlem": "SATIM",
                "Fiyat": round(price, 4),
                "Miktar": round(oldest_lot.shares, 6),
                "Tutar": round(gross_revenue, 2),
                "Komisyon": round(commission, 2),
                "Kayma Maliyeti": round(slippage, 2),
                "Toplam İşlem Maliyeti": round(commission + slippage, 2),
                "Net Tutar": round(net_revenue, 2),
                "Nakit Akışı": round(net_revenue, 2),
                "Maliyet Tabanı": round(oldest_lot.invested, 2),
                "Alış Komisyonu": round(oldest_lot.commission, 2),
                "Alış Kayma Maliyeti": round(oldest_lot.slippage, 2),
                "Alış Fiyatı": round(oldest_lot.price, 4),
                "Alış Tarihi": oldest_lot.date,
                "Tutma Süresi (Gün)": holding_days,
                "Kar/Zarar": round(profit, 2),
                "Kar/Zarar %": round(profit_pct, 2),
                "Sinyal": signal_type,
                "Kalan Nakit": round(self.cash, 2),
                "Kalan Lot": len(self.lots[symbol]),
            }
        )

        # Sembol performansını güncelle
        if symbol not in self.symbol_performance:
            self.symbol_performance[symbol] = {
                "Toplam Kar/Zarar": 0,
                "Toplam Yatırım": 0,
                "Tamamlanan İşlem": 0,
                "Kazanan": 0,
                "Kaybeden": 0,
                "Toplam Alım": 0,
                "Toplam Satım": 0,
                "Ortalama Tutma Süresi": [],
            }

        self.symbol_performance[symbol]["Toplam Kar/Zarar"] += profit
        self.symbol_performance[symbol]["Toplam Yatırım"] += oldest_lot.invested
        self.symbol_performance[symbol]["Tamamlanan İşlem"] += 1
        self.symbol_performance[symbol]["Toplam Satım"] += 1
        self.symbol_performance[symbol]["Ortalama Tutma Süresi"].append(holding_days)

        if profit > 0:
            self.symbol_performance[symbol]["Kazanan"] += 1
        else:
            self.symbol_performance[symbol]["Kaybeden"] += 1

        # Kuyruk boşaldıysa sil
        if len(self.lots[symbol]) == 0:
            del self.lots[symbol]

        return True

    def get_portfolio_value(self, current_prices):
        """Toplam portföy değeri"""
        position_value = 0

        for symbol, lot_queue in self.lots.items():
            current_price = current_prices.get(symbol, 0)
            if current_price == 0:
                # Fiyat yoksa son lot fiyatını kullan
                current_price = lot_queue[-1].price if lot_queue else 0

            for lot in lot_queue:
                position_value += lot.shares * current_price

        return self.cash + position_value

    def record_equity(self, date, current_prices):
        """Portföy değerini kaydet"""
        total_value = self.get_portfolio_value(current_prices)
        position_value = total_value - self.cash

        self.equity_curve.append(
            {
                "Tarih": date,
                "Toplam Değer": round(total_value, 2),
                "Nakit": round(self.cash, 2),
                "Pozisyon Değeri": round(position_value, 2),
            }
        )

    def get_open_positions_summary(self):
        """Açık pozisyonların özeti"""
        summary = []
        for symbol, lot_queue in self.lots.items():
            total_shares = sum(lot.shares for lot in lot_queue)
            total_invested = sum(lot.invested for lot in lot_queue)
            reference_value = sum(lot.shares * lot.price for lot in lot_queue)
            avg_price = reference_value / total_shares if total_shares > 0 else 0
            avg_cost = total_invested / total_shares if total_shares > 0 else 0

            summary.append(
                {
                    "Sembol": symbol,
                    "Lot Sayısı": len(lot_queue),
                    "Toplam Miktar": round(total_shares, 6),
                    "Toplam Yatırım": round(total_invested, 2),
                    "Ortalama Fiyat": round(avg_price, 4),
                    "Ortalama Maliyet": round(avg_cost, 4),
                    "Alış Komisyonu": round(sum(lot.commission for lot in lot_queue), 2),
                    "Alış Kayma Maliyeti": round(sum(lot.slippage for lot in lot_queue), 2),
                }
            )

        return summary


class BacktestEngine:
    """Backtesting Motoru - FIFO Lot Sistemi"""

    TIMEFRAMES = [
        ("1D", "GÜNLÜK"),
        ("W-FRI", "1 HAFTALIK"),
        ("2W-FRI", "2 HAFTALIK"),
        ("3W-FRI", "3 HAFTALIK"),
        ("ME", "1 AYLIK"),
    ]

    # ============================================================
    # YENİ: Timeframe bazlı minimum periyot ayarları
    # TradingView ile uyumlu hale getirildi
    # ============================================================
    MIN_PERIODS = {
        "1D": 30,  # Günlük: 30 gün yeterli
        "W-FRI": 14,  # Haftalık: 14 hafta (~3.5 ay)
        "2W-FRI": 10,  # 2 Haftalık: 10 periyot (~5 ay)
        "3W-FRI": 8,  # 3 Haftalık: 8 periyot (~6 ay)
        "ME": 8,  # Aylık: 8 ay (ÖNCEKİ: 20 ay - ÇOK UZUNDU!)
    }

    def __init__(self, start_date="2006-01-01", end_date=None):
        self.start_date = start_date
        self.end_date = end_date or datetime.now().strftime("%Y-%m-%d")

    def check_signals(self, df_daily, market_type, strategy="combo"):
        """Sinyal kontrolü"""

        signals = {"buy": {"cok_ucuz": False, "beles": False}, "sell": {"pahali": False}}

        hits = {"buy": {}, "sell": {}}

        for tf_code, _ in self.TIMEFRAMES:
            try:
                df_resampled = resample_market_data(df_daily.copy(), tf_code, market_type)

                # ============================================================
                # DÜZELTME: Timeframe'e özel minimum periyot kontrolü
                # ============================================================
                min_periods = self.MIN_PERIODS.get(tf_code, 14)

                if df_resampled is None or len(df_resampled) < min_periods:
                    continue

                if strategy == "combo":
                    result = calculate_combo_signal(df_resampled, tf_code)
                else:
                    result = calculate_hunter_signal(df_resampled, tf_code)

                if result:
                    if result["buy"]:
                        hits["buy"][tf_code] = True
                    if result["sell"]:
                        hits["sell"][tf_code] = True
            except (ValueError, KeyError, TypeError, IndexError, ZeroDivisionError):
                continue

        # ALIM SİGNALLERİ
        if "1D" in hits["buy"] and "W-FRI" in hits["buy"] and "3W-FRI" in hits["buy"]:
            signals["buy"]["cok_ucuz"] = True

        if "1D" in hits["buy"] and "2W-FRI" in hits["buy"] and "ME" in hits["buy"]:
            signals["buy"]["beles"] = True

        # SATIM SİGNALLERİ
        if "1D" in hits["sell"] and "W-FRI" in hits["sell"]:
            signals["sell"]["pahali"] = True

        return signals

    def run_single_symbol(self, symbol, market_type, portfolio, pbar=None):
        """Tek sembol için backtest"""

        # Veri çek - TÜM geçmiş veriyi al
        if market_type == "BIST":
            df = get_bist_data_isyatirim_only(symbol, start_date="01-01-2006")
        else:
            # Crypto için daha uzun süre - en az 8 yıl
            df = get_crypto_data(symbol, start_str="8 years ago")

        if df is None:
            print(f"\n⚠️  {symbol}: Veri çekilemedi (None döndü)")
            return None

        if len(df) < 30:
            print(f"\n⚠️  {symbol}: Yetersiz veri ({len(df)} gün)")
            return None

        print(
            f"\n✓ {symbol}: {len(df)} günlük veri çekildi (İlk: {df.index[0].date()}, Son: {df.index[-1].date()})"
        )

        # ============================================================
        # DÜZELTME: Minimum gün kontrolü azaltıldı
        # ============================================================
        min_days_required = 120  # ~4 ay

        if len(df) < min_days_required:
            print(
                f"⚠️  {symbol}: Backtest için yetersiz veri ({len(df)} gün, min {min_days_required} gerekli)"
            )
            return None

        # ============================================================
        # DÜZELTME: Warm-up süresi azaltıldı
        # ============================================================
        warmup_days = 60  # ~2 ay
        backtest_start_idx = warmup_days

        # Eğer kullanıcı özel bir start_date verdiyse onu kullan
        if self.start_date:
            user_start_idx = df.index.searchsorted(pd.Timestamp(self.start_date))
            if user_start_idx >= warmup_days:
                backtest_start_idx = user_start_idx
            elif user_start_idx > 0:
                # Kullanıcı tarihi çok erken, minimum warm-up'tan başla
                backtest_start_idx = warmup_days
                print(
                    f"  → Kullanıcı tarihi ({self.start_date}) erken, warm-up sonrası {df.index[backtest_start_idx].date()} tarihinden başlatılıyor"
                )

        print(
            f"  → Backtest başlangıcı: İndeks {backtest_start_idx} (Tarih: {df.index[backtest_start_idx].date()})"
        )

        if backtest_start_idx >= len(df):
            print(f"⚠️  {symbol}: Backtest başlangıç tarihi veri aralığının dışında")
            return None

        if pbar:
            with suppress(Exception):
                pbar.set_postfix({"Islenen": symbol})

        # ============================================================
        # DÜZELTME: Döngü artık backtest_start_idx'ten başlıyor!
        # ÖNCEKİ: for i in range(30, len(df))  ← backtest_start_idx kullanılmıyordu!
        # ============================================================
        for i in range(backtest_start_idx, len(df)):
            current_date = df.index[i]
            current_price = df["Close"].iloc[i]

            # Geçmiş veri
            historical_data = df.iloc[: i + 1].copy()
            df_daily = resample_market_data(historical_data, "1D", market_type)

            if df_daily is None or len(df_daily) < 14:
                continue

            # Her iki stratejiyi test et
            for strategy in ["combo", "hunter"]:
                signals = self.check_signals(df_daily, market_type, strategy)
                strategy_name = strategy.upper()

                # ALIM SİGNALLERİ
                if signals["buy"]["cok_ucuz"]:
                    portfolio.buy(symbol, current_price, current_date, f"{strategy_name}: ÇOK UCUZ")

                if signals["buy"]["beles"]:
                    portfolio.buy(symbol, current_price, current_date, f"{strategy_name}: BELEŞ")

                # SATIM SİGNALLERİ (lot varsa sat)
                if signals["sell"]["pahali"]:
                    portfolio.sell(symbol, current_price, current_date, f"{strategy_name}: PAHALI")

            # Her 10 günde bir portföy değerini kaydet
            if i % 10 == 0:
                portfolio.record_equity(current_date, {symbol: current_price})

        return True

    def run_backtest(self, symbols_list, market_type, initial_cash, trade_amount):
        """Ana backtest"""
        from tqdm import tqdm

        portfolio = Portfolio(initial_cash, market_type, trade_amount)

        print(f"\n{'=' * 70}")
        print(f"🔄 {market_type} Backtest Başlatılıyor...")
        print(f"📊 Sembol Sayısı: {len(symbols_list)}")
        print(f"💰 Başlangıç Sermayesi: {initial_cash:,.2f}")
        print(f"💵 İşlem Başına Tutar: {trade_amount:,.2f}")
        print(f"{'=' * 70}\n")

        success_count = 0

        with tqdm(total=len(symbols_list), desc=f"{market_type}") as pbar:
            for symbol in symbols_list:
                try:
                    result = self.run_single_symbol(symbol, market_type, portfolio, pbar)
                    if result:
                        success_count += 1
                        # Alım sayısını güncelle
                        if symbol in portfolio.symbol_performance:
                            portfolio.symbol_performance[symbol]["Toplam Alım"] = len(
                                [
                                    t
                                    for t in portfolio.all_trades
                                    if t["Sembol"] == symbol and t["İşlem"] == "ALIM"
                                ]
                            )
                except Exception:
                    print(f"[ERROR] {symbol}: backtest sirasinda beklenmeyen hata.")
                    traceback.print_exc()
                finally:
                    pbar.update(1)

        print(f"✅ Tamamlandı: {success_count}/{len(symbols_list)} sembol işlendi\n")

        return portfolio

    def generate_excel_report(self, portfolio_bist, portfolio_crypto):
        """Detaylı Excel raporu"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backtest_raporu_{timestamp}.xlsx"

        with pd.ExcelWriter(filename, engine="openpyxl") as writer:
            # 1. GENEL ÖZET
            bist_total_profit = sum(
                s["Toplam Kar/Zarar"] for s in portfolio_bist.symbol_performance.values()
            )
            crypto_total_profit = sum(
                s["Toplam Kar/Zarar"] for s in portfolio_crypto.symbol_performance.values()
            )

            bist_open_lots = sum(len(q) for q in portfolio_bist.lots.values())
            crypto_open_lots = sum(len(q) for q in portfolio_crypto.lots.values())

            summary = {
                "Metrik": [
                    "Başlangıç Sermayesi",
                    "Güncel Nakit",
                    "Gerçekleşen Kar/Zarar",
                    "Ödenen Komisyon",
                    "Kayma Maliyeti",
                    "Toplam İşlem Maliyeti",
                    "Getiri %",
                    "Toplam İşlem",
                    "Alım İşlemi",
                    "Satım İşlemi",
                    "Açık Lot Sayısı",
                    "İşlem Gören Sembol",
                ],
                "BIST": [
                    f"{portfolio_bist.initial_cash:,.2f} TL",
                    f"{portfolio_bist.cash:,.2f} TL",
                    f"{bist_total_profit:,.2f} TL",
                    f"{portfolio_bist.total_commission_paid:,.2f} TL",
                    f"{portfolio_bist.total_slippage_cost:,.2f} TL",
                    f"{portfolio_bist.total_transaction_cost:,.2f} TL",
                    f"{(bist_total_profit / portfolio_bist.initial_cash * 100):.2f}%",
                    len(portfolio_bist.all_trades),
                    len([t for t in portfolio_bist.all_trades if t["İşlem"] == "ALIM"]),
                    len([t for t in portfolio_bist.all_trades if t["İşlem"] == "SATIM"]),
                    bist_open_lots,
                    len(portfolio_bist.symbol_performance),
                ],
                "CRYPTO": [
                    f"{portfolio_crypto.initial_cash:,.2f} USD",
                    f"{portfolio_crypto.cash:,.2f} USD",
                    f"{crypto_total_profit:,.2f} USD",
                    f"{portfolio_crypto.total_commission_paid:,.2f} USD",
                    f"{portfolio_crypto.total_slippage_cost:,.2f} USD",
                    f"{portfolio_crypto.total_transaction_cost:,.2f} USD",
                    f"{(crypto_total_profit / portfolio_crypto.initial_cash * 100):.2f}%",
                    len(portfolio_crypto.all_trades),
                    len([t for t in portfolio_crypto.all_trades if t["İşlem"] == "ALIM"]),
                    len([t for t in portfolio_crypto.all_trades if t["İşlem"] == "SATIM"]),
                    crypto_open_lots,
                    len(portfolio_crypto.symbol_performance),
                ],
            }
            pd.DataFrame(summary).to_excel(writer, sheet_name="Genel Özet", index=False)

            # 2. BIST - TÜM İŞLEMLER
            if portfolio_bist.all_trades:
                df = pd.DataFrame(portfolio_bist.all_trades)
                df.to_excel(writer, sheet_name="BIST Tüm İşlemler", index=False)

            # 3. CRYPTO - TÜM İŞLEMLER
            if portfolio_crypto.all_trades:
                df = pd.DataFrame(portfolio_crypto.all_trades)
                df.to_excel(writer, sheet_name="Crypto Tüm İşlemler", index=False)

            # 4. BIST - SEMBOL PERFORMANSI
            if portfolio_bist.symbol_performance:
                perf_data = []
                for symbol, stats in portfolio_bist.symbol_performance.items():
                    avg_holding = (
                        np.mean(stats["Ortalama Tutma Süresi"])
                        if stats["Ortalama Tutma Süresi"]
                        else 0
                    )
                    perf_data.append(
                        {
                            "Sembol": symbol,
                            "Toplam Kar/Zarar (TL)": round(stats["Toplam Kar/Zarar"], 2),
                            "Toplam Yatırım (TL)": round(stats["Toplam Yatırım"], 2),
                            "Getiri %": round(
                                (stats["Toplam Kar/Zarar"] / stats["Toplam Yatırım"]) * 100, 2
                            ),
                            "Tamamlanan İşlem": stats["Tamamlanan İşlem"],
                            "Kazanan": stats["Kazanan"],
                            "Kaybeden": stats["Kaybeden"],
                            "Başarı Oranı %": round(
                                (stats["Kazanan"] / stats["Tamamlanan İşlem"]) * 100, 2
                            )
                            if stats["Tamamlanan İşlem"] > 0
                            else 0,
                            "Toplam Alım": stats["Toplam Alım"],
                            "Toplam Satım": stats["Toplam Satım"],
                            "Ort. Tutma Süresi (Gün)": round(avg_holding, 1),
                        }
                    )

                df = pd.DataFrame(perf_data).sort_values("Toplam Kar/Zarar (TL)", ascending=False)
                df.to_excel(writer, sheet_name="BIST Sembol Performans", index=False)

            # 5. CRYPTO - SEMBOL PERFORMANSI
            if portfolio_crypto.symbol_performance:
                perf_data = []
                for symbol, stats in portfolio_crypto.symbol_performance.items():
                    avg_holding = (
                        np.mean(stats["Ortalama Tutma Süresi"])
                        if stats["Ortalama Tutma Süresi"]
                        else 0
                    )
                    perf_data.append(
                        {
                            "Sembol": symbol,
                            "Toplam Kar/Zarar (USD)": round(stats["Toplam Kar/Zarar"], 2),
                            "Toplam Yatırım (USD)": round(stats["Toplam Yatırım"], 2),
                            "Getiri %": round(
                                (stats["Toplam Kar/Zarar"] / stats["Toplam Yatırım"]) * 100, 2
                            ),
                            "Tamamlanan İşlem": stats["Tamamlanan İşlem"],
                            "Kazanan": stats["Kazanan"],
                            "Kaybeden": stats["Kaybeden"],
                            "Başarı Oranı %": round(
                                (stats["Kazanan"] / stats["Tamamlanan İşlem"]) * 100, 2
                            )
                            if stats["Tamamlanan İşlem"] > 0
                            else 0,
                            "Toplam Alım": stats["Toplam Alım"],
                            "Toplam Satım": stats["Toplam Satım"],
                            "Ort. Tutma Süresi (Gün)": round(avg_holding, 1),
                        }
                    )

                df = pd.DataFrame(perf_data).sort_values("Toplam Kar/Zarar (USD)", ascending=False)
                df.to_excel(writer, sheet_name="Crypto Sembol Performans", index=False)

            # 6. BIST - AÇIK POZISYONLAR (LOT BAZLI)
            open_pos = portfolio_bist.get_open_positions_summary()
            if open_pos:
                pd.DataFrame(open_pos).to_excel(
                    writer, sheet_name="BIST Açık Pozisyonlar", index=False
                )

            # 7. CRYPTO - AÇIK POZISYONLAR (LOT BAZLI)
            open_pos = portfolio_crypto.get_open_positions_summary()
            if open_pos:
                pd.DataFrame(open_pos).to_excel(
                    writer, sheet_name="Crypto Açık Pozisyonlar", index=False
                )

            # 8. PORTFÖY DEĞERİ (BIST)
            if portfolio_bist.equity_curve:
                df = pd.DataFrame(portfolio_bist.equity_curve)
                df.to_excel(writer, sheet_name="BIST Portföy Değeri", index=False)

            # 9. PORTFÖY DEĞERİ (CRYPTO)
            if portfolio_crypto.equity_curve:
                df = pd.DataFrame(portfolio_crypto.equity_curve)
                df.to_excel(writer, sheet_name="Crypto Portföy Değeri", index=False)

        print(f"💾 Excel Rapor: {filename}")
        return filename

    def plot_results(self, portfolio_bist, portfolio_crypto):
        """Görsel raporlar"""
        import matplotlib.pyplot as plt

        fig = plt.figure(figsize=(18, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

        # 1. BIST Portföy Değeri
        if portfolio_bist.equity_curve:
            ax1 = fig.add_subplot(gs[0, :2])
            df = pd.DataFrame(portfolio_bist.equity_curve)
            ax1.plot(
                df["Tarih"], df["Toplam Değer"], linewidth=2, color="blue", label="Portföy Değeri"
            )
            ax1.axhline(
                y=portfolio_bist.initial_cash,
                color="red",
                linestyle="--",
                label="Başlangıç",
                alpha=0.6,
            )
            ax1.fill_between(
                df["Tarih"], portfolio_bist.initial_cash, df["Toplam Değer"], alpha=0.3
            )
            ax1.set_title("🇹🇷 BIST Portföy Büyümesi", fontsize=12, fontweight="bold")
            ax1.set_ylabel("Değer (TL)")
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            ax1.tick_params(axis="x", rotation=45)

        # 2. CRYPTO Portföy Değeri
        if portfolio_crypto.equity_curve:
            ax2 = fig.add_subplot(gs[1, :2])
            df = pd.DataFrame(portfolio_crypto.equity_curve)
            ax2.plot(
                df["Tarih"], df["Toplam Değer"], linewidth=2, color="orange", label="Portföy Değeri"
            )
            ax2.axhline(
                y=portfolio_crypto.initial_cash,
                color="red",
                linestyle="--",
                label="Başlangıç",
                alpha=0.6,
            )
            ax2.fill_between(
                df["Tarih"],
                portfolio_crypto.initial_cash,
                df["Toplam Değer"],
                alpha=0.3,
                color="orange",
            )
            ax2.set_title("💰 CRYPTO Portföy Büyümesi", fontsize=12, fontweight="bold")
            ax2.set_ylabel("Değer (USD)")
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            ax2.tick_params(axis="x", rotation=45)

        # 3. BIST Top 10 Performans
        if portfolio_bist.symbol_performance:
            ax3 = fig.add_subplot(gs[0, 2])
            sorted_perf = sorted(
                portfolio_bist.symbol_performance.items(),
                key=lambda x: x[1]["Toplam Kar/Zarar"],
                reverse=True,
            )[:10]
            symbols = [x[0] for x in sorted_perf]
            profits = [x[1]["Toplam Kar/Zarar"] for x in sorted_perf]
            colors = ["green" if p > 0 else "red" for p in profits]
            ax3.barh(symbols, profits, color=colors, alpha=0.7)
            ax3.set_title("BIST Top 10", fontsize=10, fontweight="bold")
            ax3.set_xlabel("Kar/Zarar (TL)", fontsize=9)
            ax3.tick_params(labelsize=8)
            ax3.grid(True, alpha=0.3, axis="x")

        # 4. CRYPTO Top 10 Performans
        if portfolio_crypto.symbol_performance:
            ax4 = fig.add_subplot(gs[1, 2])
            sorted_perf = sorted(
                portfolio_crypto.symbol_performance.items(),
                key=lambda x: x[1]["Toplam Kar/Zarar"],
                reverse=True,
            )[:10]
            symbols = [x[0] for x in sorted_perf]
            profits = [x[1]["Toplam Kar/Zarar"] for x in sorted_perf]
            colors = ["green" if p > 0 else "red" for p in profits]
            ax4.barh(symbols, profits, color=colors, alpha=0.7)
            ax4.set_title("Crypto Top 10", fontsize=10, fontweight="bold")
            ax4.set_xlabel("Kar/Zarar (USD)", fontsize=9)
            ax4.tick_params(labelsize=8)
            ax4.grid(True, alpha=0.3, axis="x")

        # 5. İstatistikler
        ax5 = fig.add_subplot(gs[2, :])
        ax5.axis("off")

        bist_stats = self._calculate_stats(portfolio_bist)
        crypto_stats = self._calculate_stats(portfolio_crypto)

        stats_text = f"""
        ╔═══════════════════════════════════════════════════════════════════════════════╗
        ║                            📊 BACKTEST İSTATİSTİKLERİ                        ║
        ╠═══════════════════════════════════════════════════════════════════════════════╣
        ║  BIST:                                     │  CRYPTO:                         ║
        ║  • Toplam Kar/Zarar: {bist_stats["profit"]:>10.2f} TL    │  • Toplam Kar/Zarar: {crypto_stats["profit"]:>10.2f} USD ║
        ║  • Başarı Oranı: {bist_stats["win_rate"]:>14.1f}%        │  • Başarı Oranı: {crypto_stats["win_rate"]:>14.1f}%      ║
        ║  • Tamamlanan İşlem: {bist_stats["trades"]:>11}         │  • Tamamlanan İşlem: {crypto_stats["trades"]:>11}       ║
        ║  • Açık Lot: {bist_stats["open_lots"]:>20}         │  • Açık Lot: {crypto_stats["open_lots"]:>20}       ║
        ╚═══════════════════════════════════════════════════════════════════════════════╝
        """
        ax5.text(
            0.5,
            0.5,
            stats_text,
            fontsize=10,
            family="monospace",
            ha="center",
            va="center",
            bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.3},
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backtest_grafik_{timestamp}.png"
        plt.savefig(filename, dpi=300, bbox_inches="tight")
        print(f"📈 Grafik: {filename}")
        plt.close()

    def _calculate_stats(self, portfolio):
        """İstatistik hesapla"""
        total_profit = sum(s["Toplam Kar/Zarar"] for s in portfolio.symbol_performance.values())

        completed_trades = sum(s["Tamamlanan İşlem"] for s in portfolio.symbol_performance.values())
        winning_trades = sum(s["Kazanan"] for s in portfolio.symbol_performance.values())
        win_rate = (winning_trades / completed_trades * 100) if completed_trades > 0 else 0

        open_lots = sum(len(q) for q in portfolio.lots.values())

        return {
            "profit": total_profit,
            "win_rate": win_rate,
            "trades": completed_trades,
            "open_lots": open_lots,
        }

    def print_summary(self, portfolio_bist, portfolio_crypto):
        """Konsol özeti"""

        print("\n" + "=" * 70)
        print("📊 BACKTEST SONUÇ ÖZETİ")
        print("=" * 70)

        # BIST
        bist_stats = self._calculate_stats(portfolio_bist)
        print("\n🇹🇷 BIST:")
        print("-" * 50)
        print(f"  Başlangıç: {portfolio_bist.initial_cash:,.2f} TL")
        print(f"  Güncel Nakit: {portfolio_bist.cash:,.2f} TL")
        print(f"  Gerçekleşen Kar/Zarar: {bist_stats['profit']:,.2f} TL")
        print(f"  Ödenen Komisyon: {portfolio_bist.total_commission_paid:,.2f} TL")
        print(f"  Kayma Maliyeti: {portfolio_bist.total_slippage_cost:,.2f} TL")
        print(f"  Toplam İşlem Maliyeti: {portfolio_bist.total_transaction_cost:,.2f} TL")
        print(f"  Toplam İşlem: {len(portfolio_bist.all_trades)}")
        print(f"  Tamamlanan İşlem: {bist_stats['trades']}")
        print(f"  Başarı Oranı: {bist_stats['win_rate']:.1f}%")
        print(f"  Açık Lot Sayısı: {bist_stats['open_lots']}")

        # CRYPTO
        crypto_stats = self._calculate_stats(portfolio_crypto)
        print("\n💰 CRYPTO:")
        print("-" * 50)
        print(f"  Başlangıç: {portfolio_crypto.initial_cash:,.2f} USD")
        print(f"  Güncel Nakit: {portfolio_crypto.cash:,.2f} USD")
        print(f"  Gerçekleşen Kar/Zarar: {crypto_stats['profit']:,.2f} USD")
        print(f"  Ödenen Komisyon: {portfolio_crypto.total_commission_paid:,.2f} USD")
        print(f"  Kayma Maliyeti: {portfolio_crypto.total_slippage_cost:,.2f} USD")
        print(f"  Toplam İşlem Maliyeti: {portfolio_crypto.total_transaction_cost:,.2f} USD")
        print(f"  Toplam İşlem: {len(portfolio_crypto.all_trades)}")
        print(f"  Tamamlanan İşlem: {crypto_stats['trades']}")
        print(f"  Başarı Oranı: {crypto_stats['win_rate']:.1f}%")
        print(f"  Açık Lot Sayısı: {crypto_stats['open_lots']}")

        print("\n" + "=" * 70 + "\n")


# ============================================================
# BENCHMARK KARŞILAŞTIRMA
# ============================================================
class BenchmarkComparison:
    """Strateji performansını benchmark ile karşılaştırır"""

    BENCHMARKS = {
        # XU100, İş Yatırım hisse veri kaynağında doğrudan desteklenmediği için devre dışı.
        "BIST": None,
        "CRYPTO": "BTCUSDT",  # Bitcoin
    }

    def __init__(self, start_date: str, end_date: str = None):
        self.start_date = start_date
        self.end_date = end_date or datetime.now().strftime("%Y-%m-%d")
        self.benchmark_data = {}

    def fetch_benchmark(self, market_type: str) -> pd.DataFrame | None:
        """Benchmark verisini çeker"""
        symbol = self.BENCHMARKS.get(market_type)
        if not symbol:
            return None

        try:
            if market_type == "BIST":
                df = get_bist_data_isyatirim_only(symbol, start_date="01-01-2006")
            else:
                df = get_crypto_data(symbol, start_str="8 years ago")

            if df is not None and not df.empty:
                self.benchmark_data[market_type] = df
                return df
        except Exception as e:
            print(f"Benchmark veri hatası ({symbol}): {e}")

        return None

    def calculate_benchmark_return(
        self, market_type: str, start_date: pd.Timestamp, end_date: pd.Timestamp
    ) -> float:
        """Benchmark getirisini hesaplar"""
        df = self.benchmark_data.get(market_type)
        if df is None or df.empty:
            return 0.0

        try:
            # Tarih aralığına filtrele
            mask = (df.index >= start_date) & (df.index <= end_date)
            filtered = df.loc[mask]

            if len(filtered) < 2:
                return 0.0

            start_price = filtered["Close"].iloc[0]
            end_price = filtered["Close"].iloc[-1]

            return ((end_price - start_price) / start_price) * 100
        except Exception:
            return 0.0

    def compare(self, portfolio: Portfolio, market_type: str) -> dict[str, Any]:
        """Portföy vs Benchmark karşılaştırması"""
        # Benchmark verisini çek
        self.fetch_benchmark(market_type)

        # Portföy getirisi
        total_profit = sum(s["Toplam Kar/Zarar"] for s in portfolio.symbol_performance.values())
        portfolio_return = (total_profit / portfolio.initial_cash) * 100

        # Benchmark getirisi (equity curve'dan tarih al)
        benchmark_return = 0.0
        if portfolio.equity_curve:
            start_date = portfolio.equity_curve[0]["Tarih"]
            end_date = portfolio.equity_curve[-1]["Tarih"]
            benchmark_return = self.calculate_benchmark_return(market_type, start_date, end_date)

        # Alpha (fazla getiri)
        alpha = portfolio_return - benchmark_return

        return {
            "portfolio_return": portfolio_return,
            "benchmark_return": benchmark_return,
            "alpha": alpha,
            "benchmark_symbol": self.BENCHMARKS.get(market_type) or "N/A",
        }


# ============================================================
# WALK-FORWARD ANALİZ
# ============================================================
class WalkForwardAnalysis:
    """
    Walk-Forward Optimization/Validation
    Veri: [Train 70% | Test 30%] x N pencere
    """

    def __init__(self, n_splits: int = 5, train_ratio: float = 0.7):
        self.n_splits = n_splits
        self.train_ratio = train_ratio
        self.results = []

    def split_data(self, df: pd.DataFrame) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
        """Veriyi train/test parçalarına böler"""
        splits = []
        total_len = len(df)
        window_size = total_len // self.n_splits

        for i in range(self.n_splits):
            start_idx = i * (window_size // 2)  # Overlap için yarım kaydır
            end_idx = start_idx + window_size

            if end_idx > total_len:
                break

            window = df.iloc[start_idx:end_idx]
            train_size = int(len(window) * self.train_ratio)

            train = window.iloc[:train_size]
            test = window.iloc[train_size:]

            if len(train) > 30 and len(test) > 10:
                splits.append((train, test))

        return splits

    def run_walk_forward(
        self, symbol: str, market_type: str, strategy: str = "combo"
    ) -> dict[str, Any]:
        """Walk-forward analiz çalıştır"""
        # Veri çek
        if market_type == "BIST":
            df = get_bist_data_isyatirim_only(symbol, start_date="01-01-2006")
        else:
            df = get_crypto_data(symbol, start_str="8 years ago")

        if df is None or len(df) < 120:
            return {"error": "Yetersiz veri"}

        splits = self.split_data(df)

        window_results = []
        for i, (train, test) in enumerate(splits):
            # Test döneminde strateji performansını ölç
            # (Basitleştirilmiş versiyon)
            test_return = (
                (test["Close"].iloc[-1] - test["Close"].iloc[0]) / test["Close"].iloc[0]
            ) * 100

            window_results.append(
                {
                    "window": i + 1,
                    "train_start": train.index[0],
                    "train_end": train.index[-1],
                    "test_start": test.index[0],
                    "test_end": test.index[-1],
                    "test_return": round(test_return, 2),
                }
            )

        self.results = window_results

        # Özet istatistikler
        returns = [w["test_return"] for w in window_results]

        return {
            "symbol": symbol,
            "strategy": strategy,
            "n_windows": len(window_results),
            "avg_return": round(np.mean(returns), 2) if returns else 0,
            "std_return": round(np.std(returns), 2) if returns else 0,
            "min_return": round(min(returns), 2) if returns else 0,
            "max_return": round(max(returns), 2) if returns else 0,
            "windows": window_results,
        }


# ============================================================
# PARALEL BACKTEST
# ============================================================
def _run_symbol_backtest(args: tuple) -> dict[str, Any]:
    """
    Tek sembol için backtest (multiprocessing worker)
    Not: Bu fonksiyon modül seviyesinde olmalı (pickle için)
    """
    symbol, market_type, start_date, trade_amount = args

    try:
        # Engine oluştur (her worker için ayrı)
        engine = BacktestEngine(start_date=start_date)

        # Sadece trade sayısı ve kar/zarar döndür (hafıza optimizasyonu)
        if market_type == "BIST":
            df = get_bist_data_isyatirim_only(symbol, start_date="01-01-2006")
            initial_cash = 100000
        else:
            df = get_crypto_data(symbol, start_str="8 years ago")
            initial_cash = 20000

        if df is None or len(df) < 120:
            return {"symbol": symbol, "success": False, "error": "Yetersiz veri"}

        # Mini portfolio ile test
        portfolio = Portfolio(initial_cash, market_type, trade_amount)
        result = engine.run_single_symbol(symbol, market_type, portfolio)

        if result:
            total_profit = sum(s["Toplam Kar/Zarar"] for s in portfolio.symbol_performance.values())
            return {
                "symbol": symbol,
                "success": True,
                "profit": total_profit,
                "trades": len(portfolio.all_trades),
                "commission_paid": portfolio.total_commission_paid,
                "slippage_cost": portfolio.total_slippage_cost,
                "transaction_cost": portfolio.total_transaction_cost,
            }

        return {"symbol": symbol, "success": False, "error": "İşlem yok"}

    except Exception as e:
        return {"symbol": symbol, "success": False, "error": str(e)}


def run_parallel_backtest(
    symbols: list[str], market_type: str, start_date: str = "2006-01-01", max_workers: int = None
) -> list[dict[str, Any]]:
    """
    Paralel backtest çalıştır

    Args:
        symbols: Sembol listesi
        market_type: BIST veya CRYPTO
        start_date: Başlangıç tarihi
        max_workers: Maksimum worker sayısı (None = CPU sayısı)

    Returns:
        Her sembol için sonuç listesi
    """
    from tqdm import tqdm

    if max_workers is None:
        max_workers = min(multiprocessing.cpu_count(), 8)

    trade_amount = 1000 if market_type == "BIST" else 100

    # Worker argümanları hazırla
    args_list = [(sym, market_type, start_date, trade_amount) for sym in symbols]

    results = []

    print(f"\n⚡ Paralel Backtest: {len(symbols)} sembol, {max_workers} worker")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_run_symbol_backtest, args): args[0] for args in args_list}

        with tqdm(total=len(futures), desc="Paralel") as pbar:
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    result = future.result(timeout=300)  # 5 dakika timeout
                    results.append(result)
                except Exception as e:
                    results.append({"symbol": symbol, "success": False, "error": str(e)})
                pbar.update(1)

    # Özet
    successful = [r for r in results if r.get("success")]
    total_profit = sum(r.get("profit", 0) for r in successful)

    print(f"\n✅ Tamamlandı: {len(successful)}/{len(symbols)} başarılı")
    print(f"💰 Toplam Kar/Zarar: {total_profit:,.2f}")

    return results


def main():
    """Ana fonksiyon"""

    print("\n" + "=" * 70)
    print("🚀 BACKTEST SİSTEMİ v2.0 - Komisyon + Benchmark + Paralel")
    print("=" * 70)
    print("\n⚙️  Yeni Özellikler:")
    print("   • Komisyon + Slippage desteği (%0.15 toplam)")
    print("   • Benchmark karşılaştırma (Crypto/BTC)")
    print("   • Walk-Forward analiz")
    print("   • Paralel backtest (multiprocessing)\n")

    engine = BacktestEngine(start_date="2006-01-01")

    # Test sembolleri
    bist_symbols = [
        "BSOKE",  # BIST100'den
    ]
    crypto_symbols = ["BTCUSDT"]

    # BIST Backtest (normal)
    portfolio_bist = engine.run_backtest(
        bist_symbols, "BIST", initial_cash=100000, trade_amount=1000
    )

    # Crypto Backtest (normal)
    portfolio_crypto = engine.run_backtest(
        crypto_symbols, "CRYPTO", initial_cash=20000, trade_amount=100
    )

    # Sonuçlar
    engine.print_summary(portfolio_bist, portfolio_crypto)

    # Benchmark karşılaştırma
    print("\n📊 BENCHMARK KARŞILAŞTIRMA")
    print("-" * 50)
    benchmark = BenchmarkComparison(start_date="2006-01-01")

    bist_comp = benchmark.compare(portfolio_bist, "BIST")
    print(f"  BIST Strateji: {bist_comp['portfolio_return']:.2f}%")
    print("  BIST Benchmark: Devre dışı (XU100 İş Yatırım kaynağında yok)")

    crypto_comp = benchmark.compare(portfolio_crypto, "CRYPTO")
    print(f"\n  Crypto Strateji: {crypto_comp['portfolio_return']:.2f}%")
    print(f"  Bitcoin ({crypto_comp['benchmark_symbol']}): {crypto_comp['benchmark_return']:.2f}%")
    print(f"  Alpha: {crypto_comp['alpha']:+.2f}%")

    # Raporlar
    engine.generate_excel_report(portfolio_bist, portfolio_crypto)
    engine.plot_results(portfolio_bist, portfolio_crypto)

    print("\n✅ Backtest tamamlandı!\n")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
