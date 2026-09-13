"""Exercise persisted trade status aggregation through the public stats contract."""

from datetime import datetime

import pytest
from sqlalchemy import event, text

from db_session import get_engine, get_session
from infrastructure.repositories.signal_trade_repository import get_trade_stats_aggregate
from models import Signal, Trade


def test_stats_counts_only_closed_trades_and_realized_pnl(authenticated_api_client) -> None:
    with get_session() as session:
        for status, pnl in (
            ("CLOSED", 50.0),
            ("CLOSED", -20.0),
            ("CLOSED", 0.0),
            ("OPEN", 900.0),
            ("CANCELLED", 800.0),
            ("LEGACY", 700.0),
        ):
            session.add(
                Trade(
                    symbol="TESTUSDT",
                    market_type="Kripto",
                    direction="BUY",
                    price=100.0,
                    quantity=5.0,
                    status=status,
                    pnl=pnl,
                    created_at=datetime(2026, 9, 10),
                )
            )

    response = authenticated_api_client.get("/stats")
    assert response.status_code == 200
    stats = response.json()
    assert stats["total_trades"] == 6
    assert stats["open_trades"] == 1
    assert stats["closed_trades"] == 3
    assert stats["total_pnl"] == 30.0
    assert stats["win_rate"] == 33.33


def test_empty_stats_exposes_zero_closed_trades(authenticated_api_client) -> None:
    response = authenticated_api_client.get("/stats")
    assert response.status_code == 200
    stats = response.json()
    assert stats["total_trades"] == 0
    assert stats["open_trades"] == 0
    assert stats["closed_trades"] == 0
    assert stats["total_pnl"] == 0.0
    assert stats["win_rate"] == 0.0


@pytest.mark.parametrize("tags", [[], [None] * 7, ["BELES", "", "LEGACY"], [None, "", "BELES"]])
def test_total_signals_counts_every_tag_in_one_snapshot_using_covering_indexes(tags) -> None:
    with get_session() as session:
        session.add_all(
            Signal(
                symbol="TEST",
                market_type="BIST",
                strategy="COMBO",
                signal_type="AL",
                timeframe="1D",
                special_tag=tag,
            )
            for tag in tags
        )
    engine = get_engine()
    statements = []

    def capture(_connection, _cursor, statement, parameters, _context, _many):
        statements.append((statement, parameters))

    event.listen(engine, "before_cursor_execute", capture)
    try:
        stats = get_trade_stats_aggregate()
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert stats["total_signals"] == len(tags)
    assert stats["total_trades"] == 0
    assert len(statements) == 1  # Both partitions and trade statistics share one read snapshot.
    with engine.begin() as connection:
        statement, parameters = statements[0]
        plan = [
            row[3]
            for row in connection.exec_driver_sql("EXPLAIN QUERY PLAN " + statement, parameters)
        ]
        assert any("COVERING INDEX" in step and "special_tag=?" in step for step in plan)
        assert any("COVERING INDEX" in step and "special_tag>?" in step for step in plan)
        connection.exec_driver_sql(
            "UPDATE signals SET special_tag=CASE WHEN special_tag IS NULL THEN 'BELES' ELSE NULL END"
        )
    assert get_trade_stats_aggregate()["total_signals"] == len(tags)


def test_legacy_unmeasured_pnl_is_returned_as_null(authenticated_api_client) -> None:
    with get_session() as session:
        session.add(
            Trade(
                symbol="TESTUSDT",
                market_type="Kripto",
                direction="BUY",
                price=100.0,
                quantity=5.0,
                status="CLOSED",
                created_at=datetime(2026, 9, 10),
            )
        )
        session.flush()
        # The existing schema allows NULL; do not let the ORM's insert default mask it.
        session.execute(text("UPDATE trades SET pnl = NULL WHERE symbol = 'TESTUSDT'"))

    response = authenticated_api_client.get("/trades")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["pnl"] is None
    assert response.json()[0]["status"] == "CLOSED"
