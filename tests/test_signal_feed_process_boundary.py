"""A real independent writer reaches the signal route without an in-process callback."""

import json
import os
import subprocess
import sys
from pathlib import Path


def test_signal_feed_crosses_process_boundary_and_recovers_restart():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-B", "-m", "scripts.smoke_signal_feed"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=45,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    assert result.returncode == 0, result.stderr[-3000:]
    evidence = json.loads(result.stdout.splitlines()[-1])
    assert evidence == {
        "status": "verified",
        "live_events": 5,
        "offline_rows_recovered_by_read_model": 2,
        "events_after_restart": 1,
        "rolled_back_rows": 0,
        "publisher_registered_in_writer": False,
        "remaining_connections": 0,
    }
