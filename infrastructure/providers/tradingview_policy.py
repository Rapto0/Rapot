"""Shared outbound pacing and a durable, credential-free provider restriction latch."""

import json
import os
import re
import stat
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

REASONS = frozenset(
    {"http_rejected", "account_restricted", "authentication_failed", "provider_rate_limited"}
)
PAUSED_MESSAGE = (
    "TradingView erişimi sağlayıcı kısıtlaması nedeniyle durduruldu; yönetici incelemesi gerekiyor."
)


class TradingViewPolicyError(RuntimeError):
    def __init__(self, message=PAUSED_MESSAGE, *, status_code=503, retry_after_seconds=0):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds


def restriction_reason(error):
    """Only structured denial signals; no arbitrary exception/URL/cookie text."""
    reason = getattr(error, "protection_reason", None)
    if isinstance(reason, str) and reason in REASONS:
        return reason
    status = getattr(error, "status_code", None)
    if status is None:
        status = getattr(getattr(error, "response", None), "status_code", None)
    if isinstance(status, int) and status in {401, 403, 429}:
        return "http_rejected"
    # borsapy 0.11 serializes websocket-client's handshake exception. Accept
    # only its pinned wrapper/prefix, never an arbitrary mention of a number.
    if (
        type(error).__module__ == "borsapy.exceptions"
        and type(error).__name__ == "APIError"
        and re.match(
            r"^API Error: TradingView error: Handshake status (401|403|429)(?:\s|$)", str(error)
        )
    ):
        return "http_rejected"
    return None


def packet_restriction(packet):
    if not isinstance(packet, dict) or packet.get("m") not in {
        "critical_error",
        "protocol_error",
        "series_error",
        "symbol_error",
        "auth_error",
    }:
        return None
    if packet.get("m") == "auth_error":
        return "authentication_failed"
    params = packet.get("p")
    if not isinstance(params, list):
        return None
    detail = " ".join(
        value[:2048].lower().replace("_", " ") for value in params if isinstance(value, str)
    )
    if any(text in detail for text in ("suspicious activity", "account banned", "account blocked")):
        return "account_restricted"
    if any(
        text in detail
        for text in ("invalid auth", "invalid token", "authentication failed", "unauthorized")
    ):
        return "authentication_failed"
    if packet.get("m") in {"critical_error", "protocol_error"} and any(
        text in detail for text in ("permission denied", "not authorized")
    ):
        return "authentication_failed"
    if any(
        text in detail
        for text in (
            "rate limit",
            "too many requests",
            "max sessions rate",
            "max charts per connection",
        )
    ):
        return "provider_rate_limited"
    return None


class TradingViewPolicy:
    def __init__(self, path, *, rate=4.0, burst=4.0, auth_interval=300.0, clock=time.monotonic):
        if rate <= 0 or burst < 1 or auth_interval < 0:
            raise ValueError("Invalid provider budget")
        self.path = Path(path)
        self._clock, self._rate, self._burst = clock, rate, burst
        self._auth_interval = auth_interval
        self._tokens, self._updated = burst, clock()
        self._next_auth = 0.0
        self._lock = threading.RLock()
        self._wake = threading.Event()
        self._reason = None
        self._requests = self._waits = 0
        self._load()

    def _check_path(self):
        if self.path.is_symlink() or any(parent.is_symlink() for parent in self.path.parents):
            raise ValueError("Unsafe policy path")
        if self.path.exists():
            info = self.path.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_size > 4096:
                raise ValueError("Invalid policy file")

    def _load(self):
        try:
            self._check_path()
            if self.path.exists():
                record = json.loads(self.path.read_text(encoding="utf-8"))
                if (
                    not isinstance(record, dict)
                    or record.get("version") != 1
                    or record.get("reason") not in REASONS
                ):
                    raise ValueError("Invalid policy marker")
                self._reason = record["reason"]
        except Exception:
            self._reason = "policy_storage_error"
        if self._reason:
            self._wake.set()

    @property
    def blocked(self):
        return self._reason is not None

    def status(self):
        with self._lock:
            return {
                "blocked": self.blocked,
                "reason": self._reason,
                "requests_admitted": self._requests,
                "budget_waits": self._waits,
                "requests_per_second": self._rate,
                "burst": self._burst,
                "auth_minimum_seconds": self._auth_interval,
            }

    def trip(self, reason):
        if not isinstance(reason, str) or reason not in REASONS:
            return False
        with self._lock:
            if self.blocked:
                return False
            # The memory latch is immediate even if disk persistence fails.
            self._reason = reason
            self._wake.set()
            temporary = None
            try:
                self._check_path()
                self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                descriptor, temporary = tempfile.mkstemp(
                    prefix=".tv-protection-", dir=self.path.parent
                )
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    json.dump(
                        {
                            "version": 1,
                            "reason": reason,
                            "recorded_at": datetime.now(UTC).isoformat(),
                        },
                        handle,
                    )
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, self.path)
                temporary = None
                if os.name != "nt":
                    directory = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
                    try:
                        os.fsync(directory)
                    finally:
                        os.close(directory)
            except Exception:
                self._reason = "policy_storage_error"
            finally:
                if temporary:
                    Path(temporary).unlink(missing_ok=True)
            return True

    def before_request(self, kind, *, stop=None):
        if kind not in {"connect", "history", "chart", "request", "auth"}:
            raise ValueError("Unknown provider request class")
        while True:
            if self.blocked:
                raise TradingViewPolicyError()
            if stop is not None and stop.is_set():
                raise TradingViewPolicyError("TradingView isteği durduruldu.")
            with self._lock:
                if self.blocked:
                    raise TradingViewPolicyError()
                now = self._clock()
                if kind == "auth" and now < self._next_auth:
                    raise TradingViewPolicyError(
                        "TradingView oturum doğrulaması bekleme aralığında.",
                        status_code=429,
                        retry_after_seconds=int(self._next_auth - now) + 1,
                    )
                self._tokens = min(
                    self._burst, self._tokens + max(0, now - self._updated) * self._rate
                )
                self._updated = now
                if self._tokens >= 1:
                    self._tokens -= 1
                    self._requests += 1
                    if kind == "auth":
                        self._next_auth = now + self._auth_interval
                    return
                self._waits += 1
                delay = min(0.1, (1 - self._tokens) / self._rate)
            self._wake.wait(delay)
