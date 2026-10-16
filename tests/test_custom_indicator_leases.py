"""Pure native witness lease lifecycle and capacity regression fixtures."""

import pytest

from infrastructure.providers.custom_indicator_leases import (
    LEASE_SLOTS_PER_CONNECTION,
    NativeLeaseBook,
    is_leased_timeframe,
    persistent_keys,
)
from infrastructure.providers.custom_indicator_stream import plan_native_subscriptions

MEMBER = ("BIST", "THYAO")
DAY = (*MEMBER, "1D")
LONG = (*MEMBER, "2D")
ROWS = ((1_799_000_000, 100, 110, 90, 101), (1_799_086_400, 100, 200, 80, 120))
META = {"timezone": "Europe/Istanbul", "session": "1000-1810"}


def setup_book(wanted=None):
    clock = [100.0]
    book = NativeLeaseBook(lambda: clock[0])
    wanted = wanted or {DAY, LONG}
    book.configure(wanted, {key[:2]: 0 for key in wanted})
    return book, clock


def event(book, key, rows=ROWS, metadata=None):
    _, contexts = book.desired()
    return {"key": key, "rows": rows, "metadata": metadata or META, **contexts[key]}


def certify(book):
    assert book.confirm(event(book, DAY)) == {"accepted": True, "invalidated": False}
    pending = event(book, LONG)
    assert book.confirm(pending) == {"accepted": True, "invalidated": False}
    return pending


@pytest.mark.parametrize(
    ("timeframe", "leased"),
    [
        ("1D", False),
        ("1", False),
        ("240", False),
        ("2D", True),
        ("1W", True),
        ("3W", True),
        ("1M", True),
        ("0D", False),
        ("1d", False),
        (None, False),
    ],
)
def test_only_native_long_periods_are_leased(timeframe, leased):
    assert is_leased_timeframe(timeframe) is leased


def test_all_markets_get_persistent_daily_anchor_and_intraday_is_preserved():
    keys = {("Kripto", "BTCUSDT", "2D"), ("Kripto", "BTCUSDT", "60"), LONG}
    assert persistent_keys(keys) == {DAY, ("Kripto", "BTCUSDT", "1D"), ("Kripto", "BTCUSDT", "60")}


def test_long_witness_needs_daily_ack_then_consumer_ack_and_is_never_reopened():
    book, _ = setup_book()
    groups, _ = book.desired()
    assert groups == {0: {DAY}}
    assert not book.ready(MEMBER, {DAY, LONG})
    daily = event(book, DAY)
    missing_metadata = {**daily, "metadata": {}}
    assert not book.confirm(missing_metadata)["accepted"]
    assert book.confirm(daily)["accepted"]
    witness = event(book, LONG)
    assert not book.ready(MEMBER, {DAY, LONG})  # Receipt without semantic ACK is insufficient.
    assert book.confirm(witness)["accepted"]
    assert book.ready(MEMBER, {DAY, LONG})
    assert book.desired()[0] == {0: {DAY}}
    assert book.witness_valid(LONG, book.certificate(witness))
    assert book.status()["witnesses_pending"] == 0
    for malformed in (None, (), (1,), "wrong", [1, 2, 3]):
        assert not book.witness_valid(LONG, malformed)


@pytest.mark.parametrize(
    "change", ["day", "previous", "opening", "high_shrink", "low_shrink", "metadata"]
)
def test_native_daily_revision_invalidates_certificates_and_old_pending_responses(change):
    book, _ = setup_book({DAY, LONG, (*MEMBER, "3W")})
    old = certify(book)
    old_pending = event(book, (*MEMBER, "3W"))
    previous, current = list(ROWS[0]), list(ROWS[1])
    metadata = META.copy()
    if change == "day":
        previous, current = current, [1_799_172_800, 120, 150, 100, 140]
    elif change == "previous":
        previous[-1] += 1
    elif change == "opening":
        current[1] += 1
    elif change == "high_shrink":
        current[2] -= 1
    elif change == "low_shrink":
        current[3] += 1
    else:
        metadata["session"] = "1000-1800"
    expected = {"accepted": True, "invalidated": True}
    if change == "day":
        expected["rollover"] = True
    assert book.confirm(event(book, DAY, (tuple(previous), tuple(current)), metadata)) == expected
    assert not book.ready(MEMBER, {DAY, LONG})
    assert not book.witness_valid(LONG, book.certificate(old))
    assert not book.confirm(old)["accepted"]
    assert not book.confirm(old_pending)["accepted"]
    assert not book.reject(old_pending)  # An old chart rejection cannot poison the new lease.
    fresh = event(book, LONG)
    assert fresh["native_day_generation"] != old["native_day_generation"]
    assert book.confirm(fresh)["accepted"]


def test_daily_range_expansion_preserves_certificates_but_explicit_gap_requires_fresh_anchor():
    book, _ = setup_book()
    witness = certify(book)
    old_anchor = event(book, DAY)
    current = (ROWS[-1][0], 100, 201, 79, 130)
    assert book.confirm(event(book, DAY, (ROWS[0], current))) == {
        "accepted": True,
        "invalidated": False,
    }
    assert book.witness_valid(LONG, book.certificate(witness))
    book.invalidate_member(MEMBER)
    assert not book.ready(MEMBER, {DAY, LONG})
    assert not book.confirm(old_anchor)["accepted"]
    assert book.desired()[0] == {0: {DAY}}
    assert book.confirm(event(book, DAY))["accepted"]
    assert not book.confirm(witness)["accepted"]


@pytest.mark.parametrize(
    "change",
    ["range_expansion", "final_close", "previous_identity", "opening", "high", "low", "session"],
)
def test_rollover_carries_seeds_only_when_exact_observed_daily_bucket_closes(change):
    book, _ = setup_book()
    witness = certify(book)
    previous = list(ROWS[-1])
    metadata = META.copy()
    if change == "range_expansion":
        previous[2] += 2
        previous[3] -= 2
    elif change == "final_close":
        previous[-1] += 2
    elif change == "previous_identity":
        previous[0] += 86400
    elif change == "opening":
        previous[1] += 1
    elif change == "high":
        previous[2] -= 1
    elif change == "low":
        previous[3] += 1
    else:
        metadata["session"] = "1000-1800"
    current = (1_799_259_200, 120, 150, 100, 140)
    result = book.confirm(event(book, DAY, (tuple(previous), current), metadata))
    assert result["accepted"] and result["invalidated"]
    assert result.get("rollover", False) == (change in {"range_expansion", "final_close"})
    assert not book.witness_valid(LONG, book.certificate(witness))


def test_retry_clock_begins_when_registered_and_old_lease_cannot_certify_retry():
    book, clock = setup_book()
    book.confirm(event(book, DAY))
    old = event(book, LONG)
    clock[0] += 200  # Queued behind persistent admission, not sent yet.
    assert book.desired()[1][LONG] == {k: old[k] for k in book.desired()[1][LONG]}
    book.mark_started({LONG})
    clock[0] += 30
    assert book.desired()[0] == {0: {DAY}}
    assert not book.confirm(old)["accepted"]
    assert book.status()["lease_retry_waiting"] == 1
    clock[0] += 29
    assert LONG not in book.desired()[1]
    clock[0] += 1
    fresh = event(book, LONG)
    assert fresh["native_lease_id"] != old["native_lease_id"]
    assert not book.reject(old)
    assert book.confirm(fresh)["accepted"]
    assert book.status()["lease_retry_waiting"] == 0


def test_removed_then_readded_member_rejects_every_old_anchor_and_lease_context():
    book, _ = setup_book()
    witness = certify(book)
    old_anchor = event(book, DAY)
    book.invalidate_member(MEMBER)
    gap_anchor = event(book, DAY)
    book.configure(set(), {})
    book.configure({DAY, LONG}, {MEMBER: 0})
    assert not book.confirm(old_anchor)["accepted"]
    assert not book.confirm(gap_anchor)["accepted"]
    assert not book.confirm(witness)["accepted"]
    assert not book.reject(old_anchor)
    assert book.confirm(event(book, DAY))["accepted"]
    assert book.confirm(event(book, LONG))["accepted"]


def test_rejected_long_series_is_not_retried_on_daily_rollover_or_reconfigure():
    book, _ = setup_book()
    book.confirm(event(book, DAY))
    rejected = event(book, LONG)
    assert book.reject(rejected)
    book.configure({DAY, LONG}, {MEMBER: 0})
    book.confirm(event(book, DAY, (ROWS[-1], (1_799_172_800, 120, 150, 100, 140))))
    assert LONG not in book.desired()[1]
    assert not book.ready(MEMBER, {DAY, LONG})
    assert book.status()["lease_refused"] == 1


def test_rejected_anchor_cannot_leave_long_certificates_ready_or_create_retry_storm():
    book, _ = setup_book()
    witness = certify(book)
    anchor = event(book, DAY)
    assert book.reject(anchor)
    assert not book.witness_valid(LONG, book.certificate(witness))
    for _ in range(5):
        assert book.desired()[0] == {0: {DAY}}
        assert book.desired()[1][DAY] == {k: anchor[k] for k in book.desired()[1][DAY]}


def test_805_members_ten_native_periods_fit_with_bounded_transient_sessions():
    timeframes = ("1D", "2D", "3D", "4D", "5D", "6D", "1W", "2W", "3W", "1M")
    wanted = {("BIST", f"SYM{i:04}", tf) for i in range(805) for tf in timeframes}
    groups, slots, refused = plan_native_subscriptions(wanted)
    assert not refused and len(slots) == 805
    assert sum(map(len, groups.values())) == 8050
    assert max(len(persistent_keys(keys)) for keys in groups.values()) == 202
    book = NativeLeaseBook(lambda: 100)
    book.configure(wanted, slots)
    initial, contexts = book.desired()
    assert sum(map(len, initial.values())) == 805
    for key, context in contexts.items():
        book.confirm({"key": key, "rows": ROWS, "metadata": META, **context})
    seen = set()
    for _ in range(70):
        actual, contexts = book.desired()
        assert all(len(keys) <= 202 + LEASE_SLOTS_PER_CONNECTION < 500 for keys in actual.values())
        leases = {key: context for key, context in contexts.items() if is_leased_timeframe(key[2])}
        assert len(leases) <= 4 * LEASE_SLOTS_PER_CONNECTION
        assert not (seen & leases.keys())
        for key, context in leases.items():
            assert book.confirm({"key": key, "rows": ROWS, "metadata": META, **context})["accepted"]
        seen.update(leases)
        if not leases:
            break
    assert len(seen) == 7245
    assert book.status()["witnesses_confirmed"] == 7245
    assert book.status()["witnesses_pending"] == 0


def test_persistent_admission_reserves_lease_capacity_and_does_not_move_incumbents():
    wanted = {("BIST", f"SYM{i:04}", "2D") for i in range(1873)}
    groups, slots, refused = plan_native_subscriptions(wanted)
    assert len(slots) == 1872 and len(refused) == 1
    assert all(len(persistent_keys(keys)) == 468 for keys in groups.values())
    extended = wanted | {("BIST", "EARLIER", "2D")}
    _, updated, _ = plan_native_subscriptions(extended, slots)
    assert all(updated[member] == slot for member, slot in slots.items())
