"""Preserved scanner accounting compatibility; no automatic scanner runtime."""

import pytest

from application.scanner import scan_history


def test_monotonic_duration_and_nested_invocation_counts_are_independent(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(scan_history.time, "monotonic", lambda: now[0])
    with scan_history.track_scan(markets={"BIST"}, mode="sync") as outer:
        scan_history.record_signal_saved()
        with scan_history.track_scan(markets={"Kripto"}, mode="async") as inner:
            scan_history.record_signal_saved()
            scan_history.record_signal_saved()
            now[0] = 102.0
        now[0] = 105.0
    assert (inner.duration_seconds, outer.duration_seconds) == (2.0, 5.0)
    assert (inner.signals_found, outer.signals_found) == (2, 1)
    scan_history.record_signal_saved()
    assert outer.signals_found == 1


def test_history_write_failure_does_not_mask_original_exception(monkeypatch):
    def failed_write(**_kwargs):
        raise OSError("history storage unavailable")

    monkeypatch.setattr(scan_history, "save_scan_history", failed_write)
    with (
        pytest.raises(ValueError, match="original failure"),
        scan_history.track_scan(markets={"BIST"}, mode="sync") as progress,
    ):
        raise ValueError("original failure")
    assert progress.status == "failed" and progress.history_id is None
