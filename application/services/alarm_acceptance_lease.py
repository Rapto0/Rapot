"""Fail-closed, file-leased evaluation for the reserved acceptance owner namespace.

Ordinary rules never read these files. A lease grants no notification permission.
Only the private server controller creates leases; no API can write them.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import time
from datetime import datetime
from pathlib import Path

PREFIX = "__acceptance__:"
MAX_RULES = 3000
MAX_BYTES = 1024**2
PAYLOAD_FIELDS = (
    "name",
    "category",
    "scope",
    "symbols",
    "watchlist_id",
    "timeframe",
    "trigger",
    "condition",
    "mode",
    "cooldown_seconds",
    "enabled",
    "notify_telegram",
)


def is_acceptance_owner(owner) -> bool:
    return isinstance(owner, str) and owner.startswith(PREFIX)


def _hash(value) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def lease_entries(rules: list[dict]) -> list[dict]:
    if len(rules) > MAX_RULES:
        raise ValueError("Acceptance rule limit exceeded")
    return sorted(
        [
            {
                "id": row["id"],
                "revision": row["revision"],
                "payload_sha256": _hash({key: row.get(key) for key in PAYLOAD_FIELDS}),
            }
            for row in rules
        ],
        key=lambda row: row["id"],
    )


def lease_manifest_sha256(entries: list[dict]) -> str:
    return _hash(entries)


def _timestamp(value) -> float:
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError("Invalid lease timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Lease timezone missing")
    return parsed.timestamp()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate lease field")
        result[key] = value
    return result


def validate_lease(value: dict, run_id: str, now: float) -> dict[str, dict]:
    if not re.fullmatch(r"[a-f0-9]{32}", run_id):
        raise ValueError("Invalid acceptance identity")
    if value.get("schema") != "rapot-alarm-acceptance-lease-v1":
        raise ValueError("Invalid lease schema")
    if value.get("run_id") != run_id or value.get("owner") != PREFIX + run_id:
        raise ValueError("Lease identity mismatch")
    start, end, heartbeat = (
        _timestamp(value.get(key)) for key in ("not_before", "expires_at", "heartbeat_at")
    )
    if not (0 < end - start <= 86400 and start <= now < end and 0 <= now - heartbeat <= 90):
        raise ValueError("Lease inactive or heartbeat expired")
    if not re.fullmatch(r"[a-f0-9]{64}", value.get("controller_manifest_sha256", "")):
        raise ValueError("Controller manifest missing")
    entries = value.get("approved_rules")
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_RULES:
        raise ValueError("Invalid approved rules")
    result = {}
    for item in entries:
        if not isinstance(item, dict) or set(item) != {"id", "revision", "payload_sha256"}:
            raise ValueError("Invalid approved identity")
        rule_id = item["id"]
        if (
            not isinstance(rule_id, str)
            or not re.fullmatch(r"[a-f0-9-]{36}", rule_id)
            or rule_id in result
        ):
            raise ValueError("Duplicate or invalid rule identity")
        if type(item["revision"]) is not int or item["revision"] < 1:
            raise ValueError("Invalid rule revision")
        if not re.fullmatch(r"[a-f0-9]{64}", item["payload_sha256"]):
            raise ValueError("Invalid payload fingerprint")
        result[rule_id] = item
    if entries != sorted(entries, key=lambda item: item["id"]):
        raise ValueError("Unordered approved rules")
    if lease_manifest_sha256(entries) != value.get("manifest_sha256"):
        raise ValueError("Lease manifest mismatch")
    return result


class AcceptanceLeaseGate:
    def __init__(self, directory: Path, *, clock=None, reader=None):
        self.directory = directory
        self._clock = clock or time.time
        self._reader = reader or self._read_private
        self._payloads = {}
        self.status = {"blocked_rules": 0, "allowed_rules": 0, "invalid_leases": 0}

    def _read_private(self, run_id):
        if os.name != "posix":
            raise ValueError("Private server lease requires POSIX permissions")
        directory = self.directory
        if directory.resolve() != directory:
            raise ValueError("Lease directory is not canonical")
        directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.fstat(directory_fd)
            if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
                raise ValueError("Unsafe lease directory")
            fd = os.open(run_id + ".json", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
        finally:
            os.close(directory_fd)
        with os.fdopen(fd, "rb") as source:
            info = os.fstat(source.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_size > MAX_BYTES
            ):
                raise ValueError("Unsafe lease file")
            raw = source.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Lease exceeds byte budget")
        return json.loads(raw, object_pairs_hook=_unique_object)

    def filter_rules(self, rules: list[dict]) -> list[dict]:
        leases, accepted, payloads = {}, [], {}
        blocked = allowed = invalid = 0
        now = self._clock()
        for rule in rules:
            owner = rule.get("owner")
            if not is_acceptance_owner(owner):
                accepted.append(rule)
                continue
            run_id = owner[len(PREFIX) :]
            if run_id not in leases:
                try:
                    if not re.fullmatch(r"[a-f0-9]{32}", run_id):
                        raise ValueError("Invalid acceptance owner")
                    leases[run_id] = validate_lease(self._reader(run_id), run_id, now)
                except Exception:
                    leases[run_id] = {}
                    invalid += 1
            entry = leases[run_id].get(rule["id"])
            if (
                rule.get("notify_telegram") is not False
                or not entry
                or entry["revision"] != rule["revision"]
            ):
                blocked += 1
                continue
            cache_key = (rule["id"], rule["revision"])
            cached = self._payloads.get(cache_key)
            fingerprint = (
                cached[1]
                if cached and cached[0] is rule
                else lease_entries([rule])[0]["payload_sha256"]
            )
            payloads[cache_key] = (rule, fingerprint)
            if fingerprint != entry["payload_sha256"]:
                blocked += 1
                continue
            accepted.append(rule)
            allowed += 1
        self._payloads = payloads
        self.status = {
            "blocked_rules": blocked,
            "allowed_rules": allowed,
            "invalid_leases": invalid,
        }
        return accepted
