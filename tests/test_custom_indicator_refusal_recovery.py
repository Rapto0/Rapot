"""Provider refusals remain explicit but temporary errors cannot poison a session forever."""

import pytest

from infrastructure.providers.custom_indicator_leases import LEASE_RETRY_MAX_SECONDS
from infrastructure.providers.custom_indicator_stream import rejection_reason
from tests.test_custom_indicator_leases import DAY, LONG, MEMBER, ROWS, event, setup_book


@pytest.mark.parametrize(
    ("method", "detail", "expected"),
    [
        ("series_error", "invalid_resolution", "unsupported_resolution"),
        ("series_error", "unsupported", "unsupported_resolution"),
        ("symbol_error", "invalid symbol", "unknown_symbol"),
        ("series_error", "permission denied for this subscription", "permission_denied"),
        ("series_error", "invalid_auth_token", "authentication_failed"),
        ("series_error", "too many requests", "rate_limited"),
        ("series_error", "temporary internal error", "temporary_unavailable"),
        ("series_error", "private unexpected payload", "provider_series_error"),
        ("symbol_error", "private unexpected payload", "provider_symbol_error"),
    ],
)
def test_reason_categories_do_not_export_provider_arguments(method, detail, expected):
    result = rejection_reason(method, ["cs_private_session", "r_private_series", detail])
    assert result == expected
    assert "private" not in result


def test_unknown_long_rejection_has_deadline_and_new_lease_not_permanent_refusal():
    book, clock = setup_book()
    book.confirm(event(book, DAY))
    rejected = event(book, LONG)
    assert book.reject({**rejected, "reason": "provider_series_error"})
    assert book.status()["lease_direct_refused"] == 1
    assert book.status()["lease_retry_waiting"] == 1
    assert not book.ready(MEMBER, {DAY, LONG})
    assert LONG not in book.desired()[1]
    assert not book.scheduling_due
    clock[0] += 29
    assert not book.scheduling_due
    clock[0] += 1
    assert book.scheduling_due
    retry = event(book, LONG)
    assert retry["native_lease_id"] != rejected["native_lease_id"]
    assert not book.reject(rejected)
    assert not book.confirm(rejected)["accepted"]
    assert book.confirm(retry)["accepted"]
    assert book.ready(MEMBER, {DAY, LONG})
    assert book.status()["lease_refused"] == 0
    assert book.status()["rejection_reasons"] == {}


def test_permission_rejection_backoff_is_capped_and_does_not_spin():
    book, clock = setup_book()
    book.confirm(event(book, DAY))
    delays = []
    for _ in range(10):
        rejected = event(book, LONG)
        assert book.reject({**rejected, "reason": "permission_denied"})
        due = book._retry[LONG][1]
        delays.append(due - clock[0])
        for _ in range(3):
            assert LONG not in book.desired()[1]
            assert not book.scheduling_due
        clock[0] = due
    assert delays[:3] == [30, 60, 120]
    assert max(delays) == LEASE_RETRY_MAX_SECONDS


def test_invalid_symbol_stays_explicit_without_daily_retry_storm():
    book, clock = setup_book()
    book.confirm(event(book, DAY))
    rejected = event(book, LONG)
    assert book.reject({**rejected, "reason": "unknown_symbol"})
    clock[0] += 100_000
    book.confirm(event(book, DAY, (ROWS[-1], (1_799_345_600, 120, 150, 100, 140))))
    assert LONG not in book.desired()[1]
    assert not book.scheduling_due
    assert book.status()["lease_direct_refused"] == 1
    assert book.status()["lease_retry_waiting"] == 0


def test_refused_period_does_not_block_unrelated_valid_period():
    other = (*MEMBER, "1W")
    book, _ = setup_book({DAY, LONG, other})
    book.confirm(event(book, DAY))
    rejected, good = event(book, LONG), event(book, other)
    assert book.reject({**rejected, "reason": "provider_series_error"})
    assert book.confirm(good)["accepted"]
    assert book.ready(MEMBER, {DAY, other})
    assert not book.ready(MEMBER, {DAY, LONG})


def test_persistent_transient_rejection_reopens_at_deadline_with_new_context():
    book, clock = setup_book({LONG})  # The implicit daily anchor also retains retry state.
    old = event(book, DAY)
    assert book.reject({**old, "reason": "temporary_unavailable"})
    book.configure({LONG}, {MEMBER: 0})
    assert DAY in book._retry
    book.desired()
    assert not book.scheduling_due
    assert book.status()["lease_retry_waiting"] == 1
    clock[0] += 29
    assert not book.scheduling_due
    clock[0] += 1
    assert book.scheduling_due
    fresh = event(book, DAY)
    assert fresh["native_request_generation"] != old["native_request_generation"]
    assert not book.confirm(old)["accepted"]
    assert not book.reject({**old, "reason": "temporary_unavailable"})
    assert book.confirm(fresh)["accepted"]
    assert book.confirm(event(book, LONG))["accepted"]
    assert book.ready(MEMBER, {DAY, LONG})
    assert not book.status()["rejection_reasons"]


def test_unknown_anchor_does_not_retry_after_time_or_new_auth():
    book, clock = setup_book()
    old = event(book, DAY)
    assert book.reject({**old, "reason": "unknown_symbol"})
    book.auth_refreshed()
    clock[0] += 100_000
    assert event(book, DAY)["native_request_generation"] == old["native_request_generation"]
    assert not book.scheduling_due
    assert not book.ready(MEMBER, {DAY, LONG})


def test_daily_auth_rejection_new_token_recreates_chart_then_prepares_live_calculation():
    from tests.test_custom_indicator_lease_integration import (
        drain,
        frame_rows,
        send_bars,
        send_quote,
        setup_native,
        stream_and_series,
    )
    from tests.test_custom_indicator_stream import packet

    clock, provider, service, pool, key = setup_native(bootstrap=False)
    stream, sid, old = stream_and_series(pool, DAY)
    packet(stream, "series_error", [old["session"], sid, "permission denied"])
    drain(service)
    assert pool.auth_refresh_required
    assert not service.live.history_ready(MEMBER, {"1D", "2D"})
    assert pool.status()["lease_anchor_blocked"] == 1
    pool.refresh_auth_token("changed-offline-token")
    pool.configure(service.live._wanted, member_slots=service.live._member_slots)
    _, fresh_sid, fresh = stream_and_series(pool, DAY)
    assert fresh_sid != sid and fresh["session"] != old["session"]
    assert not pool.confirm_native_witness(
        {
            "key": DAY,
            "rows": frame_rows(provider),
            "metadata": {"session": "synthetic"},
            **old["context"],
        }
    )["accepted"]
    send_bars(pool, DAY, frame_rows(provider))
    drain(service)
    pool.configure(service.live._wanted, member_slots=service.live._member_slots)
    send_bars(pool, LONG, frame_rows(provider))
    drain(service)
    assert service.live.history_ready(MEMBER, {"1D", "2D"})
    service.process(*service._next_job())
    clock[0] += 2
    send_quote(service, pool, clock, 150)
    assert service._results[key]["points"][-1]["ready"]
    assert not pool.status()["rejection_reasons"]
