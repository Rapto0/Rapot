"""
Veritabanı Oturum Yönetimi
SQLAlchemy engine, session ve connection pooling.
"""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from logger import get_logger
from models import Base
from settings import settings

logger = get_logger(__name__)

# Default database path
DEFAULT_DB_PATH = Path(__file__).parent / "trading_bot.db"

# Official migration policy for this project:
# - Alembic is intentionally not used.
# - Schema changes are applied via init_db() and ensure_sqlite_columns().
# - Data/backfill migrations are handled in migrate_db.py.
MIGRATION_POLICY = "init_db + ensure_sqlite_columns (No Alembic)"


def get_database_url(db_path: Path | str | None = None) -> str:
    """
    Veritabanı URL'sini oluşturur.

    Args:
        db_path: Veritabanı dosya yolu (None ise default)

    Returns:
        SQLite connection URL
    """
    if db_path is None:
        configured_url = str(settings.database_url or "").strip()
        if configured_url:
            return configured_url
        configured_path = str(settings.database_path or "").strip()
        db_path = Path(configured_path) if configured_path else DEFAULT_DB_PATH

    if isinstance(db_path, str) and "://" in db_path:
        return db_path

    return f"sqlite:///{Path(db_path)}"


def _sanitize_database_url_for_log(database_url: str) -> str:
    """
    Mask credentials from DB URL before logging.
    """
    try:
        parsed = urlsplit(database_url)
    except Exception:
        return "<invalid-db-url>"

    if not parsed.scheme:
        return database_url

    username = parsed.username
    password = parsed.password
    hostname = parsed.hostname

    if username is None or password is None or hostname is None:
        return database_url

    netloc = f"{username}:***@{hostname}"
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"

    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


# Engine oluştur
_engine = None
_SessionFactory = None
_ScopedSession = None


def get_engine(db_path: Path | str | None = None):
    """
    SQLAlchemy engine döndürür (singleton).

    Args:
        db_path: Veritabanı dosya yolu

    Returns:
        SQLAlchemy Engine
    """
    global _engine

    if _engine is None:
        database_url = get_database_url(db_path)

        _engine = create_engine(
            database_url,
            # SQLite için özel ayarlar
            connect_args={"check_same_thread": False, "timeout": 30},
            # Connection pool ayarları
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_pre_ping=True,  # Bağlantı sağlığı kontrolü
            echo=False,  # SQL loglaması (debug için True yapılabilir)
        )

        # SQLite için WAL mode ve diğer optimizasyonlar
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=10000")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.close()

        logger.info("Database engine oluşturuldu: %s", _sanitize_database_url_for_log(database_url))

    return _engine


def get_session_factory():
    """Session factory döndürür."""
    global _SessionFactory

    if _SessionFactory is None:
        engine = get_engine()
        _SessionFactory = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,  # Commit sonrası lazy loading sorunlarını önler
        )

    return _SessionFactory


def get_scoped_session():
    """Thread-safe scoped session döndürür."""
    global _ScopedSession

    if _ScopedSession is None:
        _ScopedSession = scoped_session(get_session_factory())

    return _ScopedSession


def init_db() -> None:
    """
    Veritabanı tablolarını oluşturur.

    Mevcut tablolar varsa dokunmaz, yoksa oluşturur.
    """
    engine = get_engine()
    # Policy step 1: create any missing tables from SQLAlchemy models.
    Base.metadata.create_all(bind=engine)

    # Policy step 2: apply backward-compatible schema updates.
    ensure_sqlite_columns(
        engine,
        "signals",
        {"special_tag": "VARCHAR(20)"},
        indexes=("CREATE INDEX IF NOT EXISTS idx_signals_special_tag ON signals(special_tag)",),
    )
    ensure_sqlite_columns(
        engine,
        "ai_analyses",
        {
            "provider": "VARCHAR(20)",
            "model": "VARCHAR(100)",
            "backend": "VARCHAR(50)",
            "prompt_version": "VARCHAR(50)",
            "sentiment_score": "INTEGER",
            "sentiment_label": "VARCHAR(20)",
            "confidence_score": "INTEGER",
            "risk_level": "VARCHAR(20)",
            "technical_bias": "VARCHAR(20)",
            "technical_strength": "INTEGER",
            "news_bias": "VARCHAR(20)",
            "news_strength": "INTEGER",
            "headline_count": "INTEGER",
            "latency_ms": "INTEGER",
            "error_code": "VARCHAR(40)",
        },
    )
    logger.info("Veritabanı tabloları oluşturuldu/kontrol edildi")


def ensure_sqlite_columns(
    engine,
    table_name: str,
    columns: dict[str, str],
    indexes: tuple[str, ...] = (),
) -> None:
    """SQLite tablo kolonlarını geriye uyumlu şekilde tamamlar."""
    with engine.connect() as conn:
        existing_columns = {
            row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table_name})").fetchall()
        }
        for column_name, column_type in columns.items():
            if column_name not in existing_columns:
                conn.exec_driver_sql(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                )
        for index_sql in indexes:
            conn.exec_driver_sql(index_sql)
        conn.commit()


def drop_all_tables() -> None:
    """
    Tüm tabloları siler.

    DIKKAT: Tüm veriler silinir! Sadece test için kullanın.
    """
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    logger.warning("Tüm veritabanı tabloları silindi!")


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Thread-safe session context manager.

    Kullanım:
        with get_session() as session:
            session.add(signal)
            session.commit()

    Yields:
        SQLAlchemy Session
    """
    session = get_scoped_session()()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Session hatası: {e}")
        raise
    finally:
        session.close()


def get_db_session() -> Session:
    """
    Yeni bir session döndürür.

    NOT: Manuel kapatma gerektirir. Tercihen get_session() context manager kullanın.

    Returns:
        SQLAlchemy Session
    """
    return get_session_factory()()


# ==================== CONVENIENCE FUNCTIONS ====================


def execute_raw_sql(sql: str, params: dict | None = None) -> list:
    """
    Raw SQL çalıştırır.

    Args:
        sql: SQL sorgusu
        params: Parametre dictionary'si

    Returns:
        Sonuç listesi
    """
    from sqlalchemy import text

    with get_session() as session:
        result = session.execute(text(sql), params or {})
        if result.returns_rows:
            return [dict(row._mapping) for row in result]
        return []


def get_table_stats() -> dict:
    """
    Tablo istatistiklerini döndürür.

    Returns:
        Her tablo için kayıt sayısı
    """
    stats = {}
    tables = ["signals", "trades", "orders", "scan_history", "bot_stats", "ai_analyses"]

    for table in tables:
        try:
            result = execute_raw_sql(f"SELECT COUNT(*) as count FROM {table}")
            stats[table] = result[0]["count"] if result else 0
        except Exception:
            stats[table] = 0

    return stats


def vacuum_database() -> None:
    """Veritabanını optimize eder (VACUUM)."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute("VACUUM")
    logger.info("Veritabanı optimize edildi (VACUUM)")
