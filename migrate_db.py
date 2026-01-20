"""
Veritabanı Migration Script
Mevcut SQLite verilerini yeni SQLAlchemy modellerine taşır.

Kullanım:
    python migrate_db.py              # Migration çalıştır
    python migrate_db.py --dry-run    # Sadece analiz yap, değişiklik yapma
    python migrate_db.py --backup     # Yedek al ve migrate et
"""

import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from logger import get_logger

logger = get_logger(__name__)

# Paths
OLD_DB_PATH = Path(__file__).parent / "trading_bot.db"
BACKUP_DIR = Path(__file__).parent / "backups"


def create_backup() -> Path | None:
    """
    Mevcut veritabanının yedeğini alır.

    Returns:
        Yedek dosya yolu veya None
    """
    if not OLD_DB_PATH.exists():
        logger.warning(f"Veritabanı bulunamadı: {OLD_DB_PATH}")
        return None

    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"trading_bot_{timestamp}.db"

    shutil.copy2(OLD_DB_PATH, backup_path)
    logger.info(f"Yedek oluşturuldu: {backup_path}")

    return backup_path


def analyze_old_database() -> dict:
    """
    Mevcut veritabanını analiz eder.

    Returns:
        Tablo ve kayıt sayıları
    """
    if not OLD_DB_PATH.exists():
        return {"error": "Veritabanı bulunamadı"}

    conn = sqlite3.connect(str(OLD_DB_PATH))
    cursor = conn.cursor()

    stats = {}

    # Tabloları listele
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        stats[table] = count

    conn.close()
    return stats


def migrate_signals(dry_run: bool = False) -> int:
    """
    Signals tablosunu migrate eder.

    Args:
        dry_run: True ise sadece analiz yap

    Returns:
        Migrate edilen kayıt sayısı
    """
    from db_session import get_session, init_db
    from models import Signal

    if not OLD_DB_PATH.exists():
        return 0

    # Yeni tabloları oluştur
    if not dry_run:
        init_db()

    conn = sqlite3.connect(str(OLD_DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM signals ORDER BY created_at")
    rows = cursor.fetchall()

    migrated = 0

    if dry_run:
        logger.info(f"[DRY-RUN] {len(rows)} sinyal migrate edilecek")
        conn.close()
        return len(rows)

    with get_session() as session:
        for row in rows:
            try:
                # Mevcut kayıt var mı kontrol et
                existing = (
                    session.query(Signal)
                    .filter_by(
                        symbol=row["symbol"],
                        strategy=row["strategy"],
                        timeframe=row["timeframe"],
                    )
                    .first()
                )

                if existing:
                    # Zaten var, atla
                    continue

                signal = Signal(
                    symbol=row["symbol"],
                    market_type=row["market_type"],
                    strategy=row["strategy"],
                    signal_type=row["signal_type"],
                    timeframe=row["timeframe"],
                    score=row["score"] or "",
                    price=row["price"] or 0.0,
                    details=row["details"] or "",
                    created_at=datetime.fromisoformat(row["created_at"])
                    if row["created_at"]
                    else datetime.utcnow(),
                )
                session.add(signal)
                migrated += 1
            except Exception as e:
                logger.error(f"Sinyal migrate hatası: {e}")

        session.commit()

    conn.close()
    logger.info(f"✅ {migrated} sinyal migrate edildi")
    return migrated


def migrate_trades(dry_run: bool = False) -> int:
    """
    Trades tablosunu migrate eder.

    Args:
        dry_run: True ise sadece analiz yap

    Returns:
        Migrate edilen kayıt sayısı
    """
    from db_session import get_session, init_db
    from models import Trade

    if not OLD_DB_PATH.exists():
        return 0

    if not dry_run:
        init_db()

    conn = sqlite3.connect(str(OLD_DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM trades ORDER BY created_at")
    rows = cursor.fetchall()

    migrated = 0

    if dry_run:
        logger.info(f"[DRY-RUN] {len(rows)} trade migrate edilecek")
        conn.close()
        return len(rows)

    with get_session() as session:
        for row in rows:
            try:
                trade = Trade(
                    symbol=row["symbol"],
                    market_type=row["market_type"],
                    direction=row["direction"],
                    entry_price=row["price"],
                    quantity=row["quantity"] or 1.0,
                    pnl=row["pnl"] or 0.0,
                    status=row["status"] or "OPEN",
                    signal_id=row["signal_id"],
                    created_at=datetime.fromisoformat(row["created_at"])
                    if row["created_at"]
                    else datetime.utcnow(),
                    closed_at=datetime.fromisoformat(row["closed_at"])
                    if row["closed_at"]
                    else None,
                )
                session.add(trade)
                migrated += 1
            except Exception as e:
                logger.error(f"Trade migrate hatası: {e}")

        session.commit()

    conn.close()
    logger.info(f"✅ {migrated} trade migrate edildi")
    return migrated


def migrate_scan_history(dry_run: bool = False) -> int:
    """
    Scan history tablosunu migrate eder.

    Returns:
        Migrate edilen kayıt sayısı
    """
    from db_session import get_session, init_db
    from models import ScanHistory

    if not OLD_DB_PATH.exists():
        return 0

    if not dry_run:
        init_db()

    conn = sqlite3.connect(str(OLD_DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM scan_history ORDER BY created_at")
    rows = cursor.fetchall()

    migrated = 0

    if dry_run:
        logger.info(f"[DRY-RUN] {len(rows)} tarama kaydı migrate edilecek")
        conn.close()
        return len(rows)

    with get_session() as session:
        for row in rows:
            try:
                scan = ScanHistory(
                    scan_type=row["scan_type"],
                    symbols_scanned=row["symbols_scanned"] or 0,
                    signals_found=row["signals_found"] or 0,
                    duration_seconds=row["duration_seconds"] or 0.0,
                    created_at=datetime.fromisoformat(row["created_at"])
                    if row["created_at"]
                    else datetime.utcnow(),
                )
                session.add(scan)
                migrated += 1
            except Exception as e:
                logger.error(f"Scan history migrate hatası: {e}")

        session.commit()

    conn.close()
    logger.info(f"✅ {migrated} tarama kaydı migrate edildi")
    return migrated


def migrate_bot_stats(dry_run: bool = False) -> int:
    """
    Bot stats tablosunu migrate eder.

    Returns:
        Migrate edilen kayıt sayısı
    """
    from db_session import get_session, init_db
    from models import BotStat

    if not OLD_DB_PATH.exists():
        return 0

    if not dry_run:
        init_db()

    conn = sqlite3.connect(str(OLD_DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM bot_stats")
    rows = cursor.fetchall()

    migrated = 0

    if dry_run:
        logger.info(f"[DRY-RUN] {len(rows)} bot stat migrate edilecek")
        conn.close()
        return len(rows)

    with get_session() as session:
        for row in rows:
            try:
                stat = BotStat(
                    stat_name=row["stat_name"],
                    stat_value=row["stat_value"],
                    updated_at=datetime.fromisoformat(row["updated_at"])
                    if row["updated_at"]
                    else datetime.utcnow(),
                )
                session.add(stat)
                migrated += 1
            except Exception as e:
                logger.error(f"Bot stat migrate hatası: {e}")

        session.commit()

    conn.close()
    logger.info(f"✅ {migrated} bot stat migrate edildi")
    return migrated


def run_migration(dry_run: bool = False, backup: bool = True) -> dict:
    """
    Tüm migration işlemlerini çalıştırır.

    Args:
        dry_run: True ise sadece analiz yap
        backup: True ise önce yedek al

    Returns:
        Migration sonuçları
    """
    print("=" * 50)
    print("🔄 Veritabanı Migration")
    print("=" * 50)

    results = {
        "backup_path": None,
        "old_stats": {},
        "migrated": {},
        "success": False,
    }

    # Mevcut durumu analiz et
    print("\n📊 Mevcut Veritabanı Analizi:")
    old_stats = analyze_old_database()
    results["old_stats"] = old_stats

    if "error" in old_stats:
        print(f"❌ {old_stats['error']}")
        return results

    for table, count in old_stats.items():
        print(f"   • {table}: {count} kayıt")

    # Yedek al
    if backup and not dry_run:
        print("\n💾 Yedek Alınıyor...")
        backup_path = create_backup()
        results["backup_path"] = str(backup_path) if backup_path else None

    # Migration
    mode = "[DRY-RUN] " if dry_run else ""
    print(f"\n{mode}🚀 Migration Başlıyor...")

    results["migrated"]["signals"] = migrate_signals(dry_run)
    results["migrated"]["trades"] = migrate_trades(dry_run)
    results["migrated"]["scan_history"] = migrate_scan_history(dry_run)
    results["migrated"]["bot_stats"] = migrate_bot_stats(dry_run)

    # Sonuç
    total = sum(results["migrated"].values())
    results["success"] = True

    print("\n" + "=" * 50)
    if dry_run:
        print(f"📋 [DRY-RUN] Toplam {total} kayıt migrate edilecek")
    else:
        print(f"✅ Migration Tamamlandı! Toplam {total} kayıt")
    print("=" * 50)

    return results


def main():
    parser = argparse.ArgumentParser(description="Veritabanı Migration Script")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Sadece analiz yap, değişiklik yapma",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        default=True,
        help="Migration öncesi yedek al (varsayılan: True)",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Yedek alma",
    )

    args = parser.parse_args()

    backup = not args.no_backup
    results = run_migration(dry_run=args.dry_run, backup=backup)

    if not results["success"]:
        exit(1)


if __name__ == "__main__":
    main()
