"""Exercise persisted trade status aggregation through the public stats contract."""

from datetime import datetime

from sqlalchemy import text

from db_session import get_session
from models import Trade


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
