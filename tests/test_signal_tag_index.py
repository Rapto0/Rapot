"""Preserve complete tag results while avoiding a sort over historical matches."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine

import db_session
from infrastructure.repositories.signal_trade_repository import list_signals
from models import Base, Signal

INDEX = "idx_signals_special_tag_created"


def _assert_partial_tag_index(connection) -> None:
    indexes = connection.exec_driver_sql("PRAGMA index_list(signals)").all()
    matches = [row for row in indexes if row[1] == INDEX]
    assert len(matches) == 1 and matches[0][4] == 1
    assert [row[2] for row in connection.exec_driver_sql(f"PRAGMA index_info({INDEX})")] == [
        "special_tag",
        "created_at",
    ]


def test_fresh_metadata_creates_partial_tag_date_index(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'fresh-tag-index.sqlite3'}")
    try:
        Base.metadata.create_all(engine)
        with engine.connect() as connection:
            _assert_partial_tag_index(connection)
    finally:
        engine.dispose()


@pytest.mark.parametrize("has_special_tag", [False, True])
def test_existing_database_upgrade_is_repeatable_and_preserves_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, has_special_tag: bool
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'existing-tag-index.sqlite3'}")
    try:
        tag_column = ", special_tag VARCHAR(20)" if has_special_tag else ""
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE signals (id INTEGER PRIMARY KEY, symbol VARCHAR(20) NOT NULL, "
                "market_type VARCHAR(10) NOT NULL, strategy VARCHAR(20) NOT NULL, "
                "signal_type VARCHAR(5) NOT NULL, timeframe VARCHAR(15) NOT NULL, "
                "score VARCHAR(50), price FLOAT, details TEXT, created_at DATETIME"
                + tag_column
                + ")"
            )
            connection.exec_driver_sql(
                "INSERT INTO signals(id, symbol, market_type, strategy, signal_type, "
                "timeframe, price, created_at) "
                "VALUES (7, 'OLD', 'BIST', 'COMBO', 'AL', '1D', 10, '2020-01-01')"
            )
            if has_special_tag:
                connection.exec_driver_sql("UPDATE signals SET special_tag='BELES' WHERE id=7")
            before = connection.exec_driver_sql(
                "SELECT id, symbol, market_type, strategy, signal_type, timeframe, "
                "score, price, details, created_at FROM signals"
            ).all()
        monkeypatch.setattr(db_session, "_engine", engine)
        db_session.init_db()
        db_session.init_db()
        with engine.connect() as connection:
            _assert_partial_tag_index(connection)
            after = connection.exec_driver_sql(
                "SELECT id, symbol, market_type, strategy, signal_type, timeframe, "
                "score, price, details, created_at FROM signals"
            ).all()
            assert after == before
            assert connection.exec_driver_sql(
                "SELECT special_tag FROM signals WHERE id=7"
            ).scalar_one() == ("BELES" if has_special_tag else None)
    finally:
        engine.dispose()


@pytest.fixture
def historical_tags() -> None:
    with db_session.get_engine().begin() as connection:
        connection.exec_driver_sql(
            """WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n WHERE x<10000)
            INSERT INTO signals
                (symbol,market_type,strategy,signal_type,timeframe,price,special_tag,created_at)
            SELECT CASE x%2 WHEN 0 THEN 'TEST' ELSE 'OTHER' END,
                CASE x%3 WHEN 0 THEN 'BIST' ELSE 'Kripto' END,
                CASE x%5 WHEN 0 THEN 'HUNTER' ELSE 'COMBO' END,
                CASE x%7 WHEN 0 THEN 'SAT' ELSE 'AL' END, '1D', 100,
                CASE WHEN x<=1000 THEN 'BELES' WHEN x<=2000 THEN 'COK_UCUZ'
                     WHEN x=3000 THEN 'PAHALI' ELSE NULL END,
                datetime('2020-01-01', '+'||x||' seconds') FROM n"""
        )


@pytest.mark.parametrize("tag", ["BELES", "COK_UCUZ", "PAHALI", "MISSING"])
def test_tag_queries_keep_older_sparse_and_absent_results_without_temporary_sort(
    historical_tags, tag: str
) -> None:
    rows = list_signals(
        symbol=None,
        strategy=None,
        signal_type=None,
        market_type=None,
        special_tag=tag,
        limit=50,
    )
    with db_session.get_engine().connect() as connection:
        expected = (
            connection.exec_driver_sql(
                "SELECT id FROM signals NOT INDEXED WHERE special_tag=? "
                "ORDER BY created_at DESC LIMIT 50",
                (tag,),
            )
            .scalars()
            .all()
        )
        # Compile the real ORM selection; checking an id-only surrogate would hide row lookups.
        query = (
            Signal.__table__.select()
            .where(Signal.special_tag == tag)
            .order_by(Signal.created_at.desc())
            .limit(50)
        )
        sql = str(query.compile(connection, compile_kwargs={"literal_binds": True}))
        plan = [row[3] for row in connection.exec_driver_sql("EXPLAIN QUERY PLAN " + sql)]
    assert [row.id for row in rows] == expected
    assert all(row.special_tag == tag for row in rows)
    assert any(INDEX in step for step in plan)
    assert not any("TEMP B-TREE" in step for step in plan)


def test_combined_tag_filters_and_untagged_rows_remain_complete(historical_tags) -> None:
    rows = list_signals(
        symbol="test",
        strategy="hunter",
        signal_type="al",
        market_type="BIST",
        special_tag="BELES",
        limit=100,
    )
    with db_session.get_engine().connect() as connection:
        expected = (
            connection.exec_driver_sql(
                "SELECT id FROM signals NOT INDEXED WHERE special_tag='BELES' "
                "AND symbol='TEST' AND strategy='HUNTER' AND signal_type='AL' "
                "AND market_type='BIST' ORDER BY created_at DESC LIMIT 100"
            )
            .scalars()
            .all()
        )
    assert expected and [row.id for row in rows] == expected
    latest = list_signals(
        symbol=None,
        strategy=None,
        signal_type=None,
        market_type=None,
        special_tag=None,
        limit=50,
    )
    assert len(latest) == 50 and all(row.special_tag is None for row in latest)
    assert [row.id for row in latest] == list(range(10000, 9950, -1))


def test_index_tracks_tag_changes_and_nullable_dates_without_losing_rows() -> None:
    with db_session.get_engine().begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO signals(id, symbol, market_type, strategy, signal_type, timeframe, "
            "special_tag, created_at) VALUES "
            "(1, 'A', 'BIST', 'COMBO', 'AL', '1D', NULL, '2020-01-02'), "
            "(2, 'B', 'BIST', 'COMBO', 'AL', '1D', 'BELES', '2020-01-01'), "
            "(3, 'C', 'BIST', 'COMBO', 'AL', '1D', 'BELES', NULL)"
        )
        connection.exec_driver_sql("UPDATE signals SET special_tag='BELES' WHERE id=1")
        connection.exec_driver_sql("UPDATE signals SET special_tag=NULL WHERE id=2")
    rows = list_signals(
        symbol=None,
        strategy=None,
        signal_type=None,
        market_type=None,
        special_tag="BELES",
        limit=50,
    )
    assert [row.id for row in rows] == [1, 3]
    assert rows[-1].created_at is None
