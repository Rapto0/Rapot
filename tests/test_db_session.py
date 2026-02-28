from pathlib import Path

from sqlalchemy import create_engine

from db_session import ensure_sqlite_columns


def test_ensure_sqlite_columns_adds_ai_analysis_metadata_columns(tmp_path: Path):
    db_path = tmp_path / "phase5.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )

    with engine.connect() as conn:
        conn.exec_driver_sql(
            """
            CREATE TABLE ai_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                analysis_text TEXT NOT NULL
            )
            """
        )
        conn.commit()

    ensure_sqlite_columns(
        engine,
        "ai_analyses",
        {
            "provider": "VARCHAR(20)",
            "model": "VARCHAR(100)",
            "confidence_score": "INTEGER",
            "risk_level": "VARCHAR(20)",
            "latency_ms": "INTEGER",
        },
    )

    with engine.connect() as conn:
        columns = {
            row[1] for row in conn.exec_driver_sql("PRAGMA table_info(ai_analyses)").fetchall()
        }

    assert "provider" in columns
    assert "model" in columns
    assert "confidence_score" in columns
    assert "risk_level" in columns
    assert "latency_ms" in columns
