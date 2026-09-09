"""A process lifetime lock shared by all bot entry points on one host."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class BotAlreadyRunningError(RuntimeError):
    pass


@contextmanager
def bot_instance_lock(path: Path) -> Iterator[None]:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Never unlink this file: deleting a locked inode would allow a second process to enter.
    with path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt

            if path.stat().st_size == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise BotAlreadyRunningError(
                    f"Another bot holds the instance lock: {path}"
                ) from exc
        else:
            import fcntl

            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise BotAlreadyRunningError(
                    f"Another bot holds the instance lock: {path}"
                ) from exc
        # Closing the descriptor releases the lock, including after an exception/process exit.
        yield
