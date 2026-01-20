"""
Memory Profiling Modülü
DataFrame ve uygulama bellek kullanımı takibi.
"""

import gc
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from typing import Any

import pandas as pd

from logger import get_logger

logger = get_logger(__name__)


@dataclass
class MemoryStats:
    """Bellek istatistikleri."""

    total_mb: float = 0.0
    used_mb: float = 0.0
    available_mb: float = 0.0
    percent: float = 0.0
    dataframes_mb: float = 0.0
    dataframe_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        return (
            f"RAM: {self.used_mb:.1f}MB / {self.total_mb:.1f}MB ({self.percent:.1f}%) | "
            f"DataFrames: {self.dataframe_count} ({self.dataframes_mb:.1f}MB)"
        )


def get_object_size_mb(obj: Any) -> float:
    """
    Objenin bellek kullanımını MB cinsinden döndürür.

    Args:
        obj: Boyutu ölçülecek obje

    Returns:
        Boyut (MB)
    """
    try:
        if isinstance(obj, pd.DataFrame):
            return obj.memory_usage(deep=True).sum() / (1024 * 1024)
        else:
            return sys.getsizeof(obj) / (1024 * 1024)
    except Exception:
        return 0.0


def get_dataframe_size_mb(df: pd.DataFrame) -> float:
    """
    DataFrame'in bellek kullanımını MB cinsinden döndürür.

    Args:
        df: DataFrame

    Returns:
        Boyut (MB)
    """
    try:
        return df.memory_usage(deep=True).sum() / (1024 * 1024)
    except Exception:
        return 0.0


def get_system_memory() -> MemoryStats:
    """
    Sistem bellek durumunu döndürür.

    Returns:
        MemoryStats objesi
    """
    try:
        import psutil

        mem = psutil.virtual_memory()
        return MemoryStats(
            total_mb=mem.total / (1024 * 1024),
            used_mb=mem.used / (1024 * 1024),
            available_mb=mem.available / (1024 * 1024),
            percent=mem.percent,
        )
    except ImportError:
        # psutil yoksa basit tahmin
        return MemoryStats()


def track_dataframes(namespace: dict | None = None) -> MemoryStats:
    """
    Bellekteki tüm DataFrame'leri takip eder.

    Args:
        namespace: Aranacak namespace (varsayılan: globals)

    Returns:
        MemoryStats objesi
    """
    if namespace is None:
        namespace = {}

    stats = get_system_memory()
    total_df_size = 0.0
    df_count = 0

    # Garbage collector'dan tüm DataFrame'leri bul
    for obj in gc.get_objects():
        if isinstance(obj, pd.DataFrame):
            total_df_size += get_dataframe_size_mb(obj)
            df_count += 1

    stats.dataframes_mb = total_df_size
    stats.dataframe_count = df_count

    return stats


def optimize_dataframe(df: pd.DataFrame, inplace: bool = False) -> pd.DataFrame:
    """
    DataFrame'in bellek kullanımını optimize eder.

    Optimizasyonlar:
    - Float64 -> Float32
    - Int64 -> Int32/Int16/Int8 (değer aralığına göre)
    - Object -> Category (az unique değer varsa)

    Args:
        df: Optimize edilecek DataFrame
        inplace: True ise aynı DataFrame'i değiştir

    Returns:
        Optimize edilmiş DataFrame
    """
    if not inplace:
        df = df.copy()

    original_mb = get_dataframe_size_mb(df)

    for col in df.columns:
        col_type = df[col].dtype

        # Float optimizasyonu
        if col_type == "float64":
            df[col] = df[col].astype("float32")

        # Integer optimizasyonu
        elif col_type == "int64":
            c_min = df[col].min()
            c_max = df[col].max()

            if c_min >= 0:
                if c_max < 255:
                    df[col] = df[col].astype("uint8")
                elif c_max < 65535:
                    df[col] = df[col].astype("uint16")
                elif c_max < 4294967295:
                    df[col] = df[col].astype("uint32")
            else:
                if c_min > -128 and c_max < 127:
                    df[col] = df[col].astype("int8")
                elif c_min > -32768 and c_max < 32767:
                    df[col] = df[col].astype("int16")
                elif c_min > -2147483648 and c_max < 2147483647:
                    df[col] = df[col].astype("int32")

        # Category optimizasyonu (string sütunlar için)
        elif col_type == "object":
            num_unique = df[col].nunique()
            num_total = len(df[col])
            if num_unique / num_total < 0.5:  # %50'den az unique ise
                df[col] = df[col].astype("category")

    optimized_mb = get_dataframe_size_mb(df)
    reduction = ((original_mb - optimized_mb) / original_mb) * 100 if original_mb > 0 else 0

    logger.debug(
        f"DataFrame optimize edildi: {original_mb:.2f}MB -> {optimized_mb:.2f}MB (-%{reduction:.1f})"
    )

    return df


def memory_limit_decorator(max_mb: float = 500.0):
    """
    Fonksiyonun bellek limitini kontrol eden decorator.

    Args:
        max_mb: Maksimum izin verilen bellek artışı (MB)

    Returns:
        Decorator fonksiyonu
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Başlangıç belleği
            gc.collect()
            before_stats = track_dataframes()

            try:
                result = func(*args, **kwargs)

                # Bitiş belleği
                gc.collect()
                after_stats = track_dataframes()

                memory_increase = after_stats.dataframes_mb - before_stats.dataframes_mb

                if memory_increase > max_mb:
                    logger.warning(
                        f"⚠️ {func.__name__}: Bellek limiti aşıldı! "
                        f"+{memory_increase:.1f}MB (limit: {max_mb}MB)"
                    )

                return result

            except MemoryError as e:
                logger.error(f"❌ {func.__name__}: MemoryError! {e}")
                gc.collect()
                raise

        return wrapper

    return decorator


def profile_memory(func: Callable) -> Callable:
    """
    Fonksiyonun bellek kullanımını profillayan decorator.

    Args:
        func: Profillenecek fonksiyon

    Returns:
        Wrapped fonksiyon
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        gc.collect()
        before_stats = track_dataframes()

        start_time = datetime.now()
        result = func(*args, **kwargs)
        elapsed = (datetime.now() - start_time).total_seconds()

        gc.collect()
        after_stats = track_dataframes()

        memory_change = after_stats.dataframes_mb - before_stats.dataframes_mb
        df_change = after_stats.dataframe_count - before_stats.dataframe_count

        logger.info(
            f"📊 {func.__name__}: {elapsed:.2f}s | "
            f"Memory: {memory_change:+.1f}MB | "
            f"DataFrames: {df_change:+d}"
        )

        return result

    return wrapper


class MemoryTracker:
    """
    Bellek kullanımını sürekli takip eden sınıf.

    Kullanım:
        tracker = MemoryTracker()
        tracker.checkpoint("başlangıç")
        # ... işlemler ...
        tracker.checkpoint("işlem_sonrası")
        tracker.report()
    """

    def __init__(self):
        self._checkpoints: list[tuple[str, MemoryStats]] = []
        self._start_time = datetime.now()

    def checkpoint(self, name: str) -> MemoryStats:
        """
        Bellek durumunu kaydet.

        Args:
            name: Checkpoint ismi

        Returns:
            MemoryStats objesi
        """
        stats = track_dataframes()
        self._checkpoints.append((name, stats))
        logger.debug(f"Checkpoint [{name}]: {stats}")
        return stats

    def report(self) -> str:
        """
        Tüm checkpoint'lerin raporunu oluştur.

        Returns:
            Rapor string'i
        """
        if not self._checkpoints:
            return "Checkpoint yok."

        lines = ["📊 Memory Profiling Report", "=" * 50]

        for i, (name, stats) in enumerate(self._checkpoints):
            lines.append(f"\n[{i + 1}] {name}")
            lines.append(f"    RAM: {stats.used_mb:.1f}MB ({stats.percent:.1f}%)")
            lines.append(f"    DataFrames: {stats.dataframe_count} ({stats.dataframes_mb:.1f}MB)")

            if i > 0:
                prev_stats = self._checkpoints[i - 1][1]
                mem_diff = stats.dataframes_mb - prev_stats.dataframes_mb
                df_diff = stats.dataframe_count - prev_stats.dataframe_count
                lines.append(f"    Δ Memory: {mem_diff:+.1f}MB | Δ DataFrames: {df_diff:+d}")

        elapsed = (datetime.now() - self._start_time).total_seconds()
        lines.append(f"\n{'=' * 50}")
        lines.append(f"Total time: {elapsed:.2f}s")

        report = "\n".join(lines)
        logger.info(report)
        return report

    def clear(self) -> None:
        """Checkpoint'leri temizle."""
        self._checkpoints.clear()
        self._start_time = datetime.now()


def cleanup_memory(aggressive: bool = False) -> float:
    """
    Belleği temizle ve boşaltılan miktarı döndür.

    Args:
        aggressive: True ise daha agresif temizlik yap

    Returns:
        Boşaltılan bellek (MB)
    """
    before = track_dataframes()

    # Normal garbage collection
    gc.collect()

    if aggressive:
        # Tüm nesilleri temizle
        gc.collect(0)
        gc.collect(1)
        gc.collect(2)

    after = track_dataframes()
    freed = before.dataframes_mb - after.dataframes_mb

    if freed > 0:
        logger.info(f"🧹 Bellek temizlendi: {freed:.1f}MB boşaltıldı")

    return freed


# ==================== CONVENIENCE FUNCTIONS ====================


def log_memory_status() -> None:
    """Mevcut bellek durumunu logla."""
    stats = track_dataframes()
    logger.info(f"💾 {stats}")


def get_memory_summary() -> dict:
    """
    Bellek özetini dictionary olarak döndür.

    Returns:
        Bellek istatistikleri dictionary'si
    """
    stats = track_dataframes()
    return {
        "total_mb": round(stats.total_mb, 2),
        "used_mb": round(stats.used_mb, 2),
        "percent": round(stats.percent, 2),
        "dataframes_mb": round(stats.dataframes_mb, 2),
        "dataframe_count": stats.dataframe_count,
        "timestamp": stats.timestamp.isoformat(),
    }
