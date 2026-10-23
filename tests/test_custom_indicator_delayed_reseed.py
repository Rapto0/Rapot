"""A bounded raw cache must not turn a slow reseed queue into endless revisions."""

import pytest

from tests.test_custom_indicator_batch_reentry import expired_preview


def test_delayed_reseed_after_cache_eviction_does_not_repeat_same_revision():
    clock, provider, service, key, config, _ = expired_preview()
    service.process(key, config, service._generation)
    reset = service.publication_token(key[:2])
    assert not service.live.has_seed(key, 1)
    # A large universe can evict this member's 10 raw frames before native
    # witnesses return and the bounded FIFO reaches its second preparation.
    service._native.clear()
    clock[0] += 181
    service.process(key, config, service._generation)
    assert service.publication_token(key[:2]) == reset
    assert service.live.has_seed(key, 1)
    assert len(provider.batches) == 2


@pytest.mark.parametrize("change", ["history", "member_gap", "global_gap", "epoch"])
def test_pending_reset_does_not_hide_a_new_revision_or_continuity_loss(change):
    clock, provider, service, key, config, _ = expired_preview()
    service.process(key, config, service._generation)
    if change == "history":
        provider.data.iloc[5, provider.data.columns.get_loc("Close")] += 0.1
    elif change == "member_gap":
        service.live_gap("Synthetic member gap", key[:2])
    elif change == "global_gap":
        service.live_gap("Synthetic global gap")
    else:
        provider.generation += 1
    service._native.clear()
    clock[0] += 181
    before = service.publication_token(key[:2])
    service.process(key, config, service._generation)
    assert service.publication_token(key[:2]) != before
    assert not service.live.has_seed(key, provider.generation)


def test_delayed_reseed_still_waits_for_current_native_witnesses():
    clock, provider, service, key, config, _ = expired_preview()
    service.process(key, config, service._generation)
    service._native.clear()
    clock[0] += 181
    service._running = True
    assert service._next_job() is None
    assert len(provider.batches) == 1
    assert not service.live.has_seed(key, 1)
