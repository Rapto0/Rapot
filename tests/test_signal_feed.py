"""Offline feed cursor, transaction visibility and lifecycle acceptance."""

import asyncio
import sqlite3
import threading
from datetime import UTC, datetime, timedelta, timezone

import pytest

from api.runtime.signal_feed import SignalFeed
from infrastructure.persistence import signal_feed_repository as repository
from infrastructure.persistence.signal_feed_repository import SignalFeedBatch
from settings import settings


def insert(connection, symbol="BTCUSDT", special_tag=None):
    return connection.execute(
        "INSERT INTO signals "
        "(symbol,market_type,strategy,signal_type,timeframe,price,score,created_at,special_tag) "
        "VALUES (?, 'Kripto', 'COMBO', 'AL', '1D', 25, '+4/-0', ?, ?)",
        (symbol, "2026-09-10 12:30:00", special_tag),
    ).lastrowid


async def no_resync():
    raise AssertionError("unexpected resync")


@pytest.mark.asyncio
async def test_separate_sqlite_connections_expose_only_commits_and_bound_each_batch():
    with (
        sqlite3.connect(settings.database_path) as writer_a,
        sqlite3.connect(settings.database_path) as writer_b,
    ):
        insert(writer_a, "ROLLEDBACK")
        assert repository.get_signal_feed_max_id() == 0
        assert repository.read_signal_feed_batch(after_id=0, limit=2).signals == []
        writer_a.rollback()
        first_id = insert(writer_b, special_tag="COK_UCUZ")
        writer_b.commit()
        second_id = insert(writer_a, "ETHUSDT")
        third_id = insert(writer_a, "SOLUSDT")
        writer_a.commit()
        events = []

        async def emit(signal):
            events.append(signal)

        feed = SignalFeed(emit_signal=emit, emit_resync=no_resync, batch_size=2)
        feed.cursor = 0
        assert await feed.poll_once() == 2
        assert feed.cursor == second_id
        assert [event["id"] for event in events] == [first_id, second_id]
        assert events[0]["specialTag"] == "COK_UCUZ"
        assert events[0]["marketType"] == "Kripto"
        assert events[0]["createdAt"] == "2026-09-10T12:30:00Z"
        assert await feed.poll_once() == 1
        assert feed.cursor == third_id
        assert await feed.poll_once() == 0
        writer_b.execute("UPDATE signals SET special_tag='BELES' WHERE id=?", (first_id,))
        writer_b.commit()
        # This is intentionally create-only. REST must reconcile later enrichments.
        assert await feed.poll_once() == 0
        assert (
            repository.read_signal_feed_batch(after_id=0, limit=1).signals[0]["specialTag"]
            == "BELES"
        )


def test_feed_timestamp_normalizes_aware_and_naive_values_to_the_rest_utc_contract():
    assert repository._utc_timestamp(datetime(2026, 9, 10, 12)) == "2026-09-10T12:00:00Z"
    assert (
        repository._utc_timestamp(datetime(2026, 9, 10, 15, tzinfo=timezone(timedelta(hours=3))))
        == "2026-09-10T12:00:00Z"
    )
    assert (
        repository._utc_timestamp(datetime(2026, 9, 10, 12, tzinfo=UTC)) == "2026-09-10T12:00:00Z"
    )
    assert repository._utc_timestamp(None) is None


@pytest.mark.asyncio
async def test_publish_error_retains_failed_row_and_later_ids_for_retry(monkeypatch):
    attempts = []
    fail = True

    def read(*, after_id, limit):
        return SignalFeedBatch(
            5, [{"id": value} for value in (1, 3, 5) if value > after_id][:limit]
        )

    async def emit(signal):
        attempts.append(signal["id"])
        if fail and signal["id"] == 3:
            raise RuntimeError("publish failed")

    monkeypatch.setattr(repository, "read_signal_feed_batch", read)
    feed = SignalFeed(emit_signal=emit, emit_resync=no_resync)
    feed.cursor = 0
    with pytest.raises(RuntimeError, match="publish failed"):
        await feed.poll_once()
    assert feed.cursor == 1
    fail = False
    assert await feed.poll_once() == 2
    assert attempts == [1, 3, 3, 5]
    assert feed.cursor == 5


@pytest.mark.asyncio
async def test_database_error_and_failed_resync_do_not_advance_cursor(monkeypatch):
    mode = "db_error"
    resets = []

    def read(**_kwargs):
        if mode == "db_error":
            raise sqlite3.OperationalError("locked")
        return SignalFeedBatch(2, [])

    async def reset():
        resets.append(1)
        if mode == "resync_error":
            raise RuntimeError("resync failed")

    async def emit(_signal):
        raise AssertionError("reset must not replay historical rows")

    monkeypatch.setattr(repository, "read_signal_feed_batch", read)
    feed = SignalFeed(emit_signal=emit, emit_resync=reset)
    feed.cursor = 10
    with pytest.raises(sqlite3.OperationalError):
        await feed.poll_once()
    assert feed.cursor == 10
    mode = "resync_error"
    with pytest.raises(RuntimeError):
        await feed.poll_once()
    assert feed.cursor == 10
    mode = "reset"
    assert await feed.poll_once() == 0
    assert feed.cursor == 2
    assert resets == [1, 1]


@pytest.mark.asyncio
async def test_start_is_idempotent_and_stop_drains_pending_thread_read(monkeypatch):
    entered = threading.Event()
    release = threading.Event()
    reads = []
    events = []

    def read(**_kwargs):
        entered.set()
        assert release.wait(timeout=3)
        reads.append(1)
        return SignalFeedBatch(8, [{"id": 8}])

    async def emit(signal):
        events.append(signal)

    monkeypatch.setattr(repository, "get_signal_feed_max_id", lambda: 7)
    monkeypatch.setattr(repository, "read_signal_feed_batch", read)
    feed = SignalFeed(emit_signal=emit, emit_resync=no_resync)
    await feed.start()
    first_task = feed._task
    assert feed.cursor == 7
    assert await asyncio.to_thread(entered.wait, 2)
    await feed.start()
    assert feed._task is first_task
    stopping = asyncio.create_task(feed.stop())
    await asyncio.sleep(0)
    assert not stopping.done()
    release.set()
    await asyncio.wait_for(stopping, 3)
    await feed.stop()
    assert not feed.running
    assert first_task.done()
    assert reads == [1]
    assert events == []


@pytest.mark.asyncio
async def test_background_feed_recovers_readiness_without_resetting_cursor(monkeypatch):
    attempts = 0
    ready = asyncio.Event()
    states = []

    def read(**_kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise sqlite3.OperationalError("temporary")
        return SignalFeedBatch(4, [])

    async def emit(_signal):
        raise AssertionError("no new rows")

    def health(is_ready, error):
        states.append((is_ready, error))
        if is_ready and attempts >= 2:
            ready.set()

    monkeypatch.setattr(repository, "get_signal_feed_max_id", lambda: 4)
    monkeypatch.setattr(repository, "read_signal_feed_batch", read)
    feed = SignalFeed(emit_signal=emit, emit_resync=no_resync, poll_interval=0.01, on_health=health)
    try:
        await feed.start()
        await asyncio.wait_for(ready.wait(), 2)
        assert feed.cursor == 4
        assert states[0] == (True, None)
        assert states[1][0] is False
        assert states[-1] == (True, None)
    finally:
        await feed.stop()


@pytest.mark.parametrize("limit", [0, -1, 1001])
def test_repository_rejects_unbounded_batch_requests(limit):
    with pytest.raises(ValueError):
        repository.read_signal_feed_batch(after_id=0, limit=limit)
