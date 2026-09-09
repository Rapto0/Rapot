from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from infrastructure.runtime_lock import BotAlreadyRunningError, bot_instance_lock


def test_second_bot_cannot_enter_and_exception_releases_lock(tmp_path):
    path = tmp_path / "bot.lock"
    with pytest.raises(ValueError, match="simulated failure"), bot_instance_lock(path):
        with pytest.raises(BotAlreadyRunningError), bot_instance_lock(path):
            pytest.fail("second bot acquired the lock")
        raise ValueError("simulated failure")
    with bot_instance_lock(path):
        assert path.is_file()


def test_other_process_cannot_acquire_active_bot_lock(tmp_path):
    path = tmp_path / "bot.lock"
    command = [
        sys.executable,
        "-B",
        "-c",
        "from pathlib import Path; from infrastructure.runtime_lock import bot_instance_lock; "
        "import sys; lock=bot_instance_lock(Path(sys.argv[1])); lock.__enter__(); print('acquired')",
        str(path),
    ]
    root = Path(__file__).resolve().parents[1]
    with bot_instance_lock(path):
        blocked = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=10)
    assert blocked.returncode != 0
    assert "BotAlreadyRunningError" in blocked.stderr
    released = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=10)
    assert released.returncode == 0
    assert released.stdout.strip() == "acquired"


def test_scheduler_entry_point_holds_lock_for_entire_run(monkeypatch, tmp_path):
    import scheduler
    from settings import settings

    path = tmp_path / "entry.bot.lock"
    monkeypatch.setattr(settings, "bot_lock_path", str(path))
    ran = []

    def run(*, use_async):
        with pytest.raises(BotAlreadyRunningError), bot_instance_lock(path):
            pytest.fail("scheduler did not hold the lock")
        ran.append(use_async)

    monkeypatch.setattr(scheduler, "_run_bot", run)
    scheduler.start_bot(use_async=False)
    assert ran == [False]
