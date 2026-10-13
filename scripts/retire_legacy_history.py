"""Explicit, offline SQLite retirement of legacy scanner history.

No application imports, provider calls, schema migration, VACUUM or automatic backup.
Default CLI does no I/O. A reviewed host operator must quiesce all writers and supply
fresh, hash-pinned retirement and independently restored binary-backup evidence.
Plans/receipts contain counts and typed hashes, never row contents or credentials.
An apply uses one transaction; deleted pages remain reusable inside the database.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import struct
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

MIB = 1024 * 1024
MODULUS = 1 << 256
CHUNK_ROWS = 128
MAX_ROW_BYTES = 8 * MIB
MAX_PROOF_BYTES = 256 * 1024
RESERVE_BYTES = 528 * MIB
WORKING_BYTES = 64 * MIB
BACKUP_MAX_AGE = 6 * 3600
RETIREMENT_MAX_AGE = 300
STRATEGIES = ("COMBO", "HUNTER")
# Exact literals from market_scanner.py in 2b090a3 (SHA256
# 9acf52284d4ef3a4d61e4de0923bc51c704ac1615bfca4e057b7071691b6083e).
# Later source had mojibake; do not normalize or broaden database predicates.
LEGACY_AI_SCENARIOS = (
    "🔥🔥 COMBO: ÇOK UCUZ!",
    "🔥🔥 HUNTER: ÇOK UCUZ!",
    "💎💎💎 COMBO: BELEŞ (TARİHİ FIRSAT)!",
    "💎💎💎 HUNTER: BELEŞ (TARİHİ FIRSAT)!",
    "⚠️⚠️ COMBO: PAHALI!",
    "⚠️⚠️ HUNTER: PAHALI!",
    "🚨🚨🚨 COMBO: FAHİŞ FİYAT!",
    "🚨🚨🚨 HUNTER: FAHİŞ FİYAT!",
)
LEGACY_STATS = (
    "sync_scan_count",
    "sync_signal_count",
    "async_scan_count",
    "async_signal_count",
    "runtime_is_running",
    "runtime_is_scanning",
    "runtime_last_scan_time",
    "runtime_error_count",
    "runtime_last_error",
    "special_tag_health_state",
    "special_tag_health_summary",
    "distributed_lock:scheduled_scan",
)
ALARM_TABLES = frozenset(
    {
        "advanced_alarm_watchlists",
        "advanced_alarm_rules",
        "advanced_alarm_states",
        "advanced_alarm_events",
        "server_alarm_rules",
        "server_alarm_symbol_states",
        "server_alarm_events",
    }
)
REQUIRED_TABLES = ALARM_TABLES | {
    "signals",
    "scan_history",
    "ai_analyses",
    "bot_stats",
    "trades",
    "orders",
    "research_workspaces",
}
TARGETS = ("signals", "scan_history", "ai_analyses", "bot_stats", "trades")
RECOVERED_TABLE = "lost_and_found"
RECOVERED_COLUMNS = ["rootpgno", "pgno", "nfield", "id", *[f"c{i}" for i in range(10)]]
RECOVERED_TIMEFRAMES = ("1D", "W-FRI", "2W-FRI", "3W-FRI", "ME")
MAX_RECOVERED_INDEX_ROWS = 20_000
MAX_RECOVERED_INDEX_BYTES = 8 * MIB
RECOVERED_BODY = (
    "t.nfield=10 AND typeof(t.id)='integer' AND t.c0 IS NULL "
    "AND typeof(t.c1)='text' AND t.c2 IN ('BIST','Kripto') "
    "AND t.c3 IN ('COMBO','HUNTER') AND t.c4 IN ('AL','SAT') "
    "AND typeof(t.c5)='text' AND typeof(t.c6)='text' "
    "AND typeof(t.c7) IN ('integer','real') "
    "AND typeof(t.c8)='text' AND typeof(t.c9)='text'"
)
RECOVERED_LOOKUP = (
    "t.nfield=4 AND typeof(t.c0)='text' AND t.c1 IN ('COMBO','HUNTER') "
    "AND t.c2 IN ('1D','W-FRI','2W-FRI','3W-FRI','ME') AND typeof(t.c3)='integer' AND "
    + " AND ".join(f"t.c{i} IS NULL" for i in range(4, 10))
)
RECOVERED_INDEX = (
    "t.nfield=2 AND typeof(t.c0)='text' AND typeof(t.c1)='integer' AND "
    + " AND ".join(f"t.c{i} IS NULL" for i in range(2, 10))
)
SIGNAL_MATCH = "strategy IN ('COMBO','HUNTER')"
RELATED_SIGNAL = (
    "EXISTS (SELECT 1 FROM signals s WHERE s.id=t.signal_id AND s.strategy IN ('COMBO','HUNTER'))"
)


class CleanupError(RuntimeError):
    """Static, secret-free error code suitable for an operator receipt."""


def require(condition: Any, code: str) -> None:
    if not condition:
        raise CleanupError(code)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def row_digest(row: tuple[Any, ...]) -> bytes:
    """Byte-compatible with reviewed rapot-sqlite-logical-v1 backup codec."""
    result = hashlib.sha256(b"rapot-sqlite-row-v1\0")
    result.update(struct.pack(">I", len(row)))
    total = 0
    for value in row:
        if value is None:
            tag, payload = b"N", b""
        elif type(value) is int:
            tag, payload = b"I", struct.pack(">q", value)
        elif type(value) is float:
            tag, payload = b"F", struct.pack(">d", value)
        elif type(value) is str:
            tag, payload = b"T", value.encode("utf-8")
        elif type(value) is bytes:
            tag, payload = b"B", value
        else:
            raise CleanupError("unsupported_sqlite_value")
        total += len(payload)
        require(total <= MAX_ROW_BYTES, "row_budget_exceeded")
        result.update(tag)
        result.update(struct.pack(">Q", len(payload)))
        result.update(payload)
    return result.digest()


@dataclass
class Accumulator:
    count: int = 0
    summed: int = 0
    xored: int = 0

    def add(self, value: bytes) -> None:
        number = int.from_bytes(value, "big")
        self.count += 1
        self.summed = (self.summed + number) % MODULUS
        self.xored ^= number

    def result(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "sum256": f"{self.summed:064x}",
            "xor256": f"{self.xored:064x}",
        }


class Budget:
    """Bound SQL and Python work; leave room for transaction rollback at every check."""

    def __init__(self, seconds: float = 1800) -> None:
        require(0 < seconds <= 3600, "invalid_timeout")
        self.deadline = time.monotonic() + seconds
        self.last_disk_check = 0.0
        self.path: Path | None = None
        self.journal_limit = 0
        self.initial_journal = 0
        self.failure: str | None = None

    def check(self, *, force: bool = False) -> None:
        current = time.monotonic()
        require(current < self.deadline, "deadline_exceeded")
        if self.path is not None and (force or current - self.last_disk_check >= 0.5):
            require(
                shutil.disk_usage(self.path.parent).free >= RESERVE_BYTES + WORKING_BYTES,
                "disk_reserve_reached",
            )
            require(
                journal_bytes(self.path) <= self.initial_journal + self.journal_limit,
                "journal_budget_exceeded",
            )
            self.last_disk_check = current

    def progress(self) -> int:
        try:
            self.check()
        except CleanupError as exc:
            self.failure = str(exc)
            return 1
        return 0


def file_identity(path: Path) -> dict[str, Any]:
    require(path.is_absolute(), "absolute_database_path_required")
    # Reject aliases through symlinked parents as well as the final file.
    for item in (path, *path.parents):
        require(not item.is_symlink(), "symlink_path_rejected")
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "database_not_single_regular_file")
    return {"path": str(path), "device": info.st_dev, "inode": info.st_ino}


def journal_bytes(path: Path) -> int:
    size = 0
    for suffix in ("-wal", "-journal"):
        journal = Path(str(path) + suffix)
        require(not journal.is_symlink(), "journal_symlink_rejected")
        if journal.exists():
            info = journal.stat()
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "invalid_journal_file")
            size += info.st_size
    return size


def connect(path: Path, *, write: bool, budget: Budget) -> sqlite3.Connection:
    file_identity(path)
    connection = sqlite3.connect(
        "file:" + quote(path.as_posix(), safe="/:") + ("?mode=rw" if write else "?mode=ro"),
        uri=True,
        timeout=1,
        isolation_level=None,
    )
    try:
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_ROW_BYTES)
        connection.execute("PRAGMA busy_timeout=1000")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute("PRAGMA cache_size=-2048")
        connection.execute("PRAGMA temp_store=MEMORY")
        if not write:
            connection.execute("PRAGMA query_only=ON")
        require(connection.execute("PRAGMA foreign_keys").fetchone() == (1,), "foreign_keys_off")
        connection.set_progress_handler(budget.progress, 10000)
        return connection
    except BaseException:
        connection.close()
        raise


def schema(connection: sqlite3.Connection) -> tuple[dict, dict[str, list[str]]]:
    rows = connection.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
    ).fetchmany(257)
    require(len(rows) <= 256, "schema_budget_exceeded")
    require(not any(row[0] == "trigger" for row in rows), "triggers_not_supported")
    hashed = hashlib.sha256(b"rapot-sqlite-schema-v1\0")
    columns = {}
    for row in rows:
        hashed.update(row_digest(row))
        kind, name, _, sql = row
        if kind != "table":
            continue
        require(not sql or "VIRTUAL TABLE" not in sql.upper(), "virtual_table_not_supported")
        info = connection.execute(f"PRAGMA table_xinfo({identifier(name)})").fetchall()
        require(info and all(column[6] == 0 for column in info), "generated_columns_not_supported")
        columns[name] = [column[1] for column in info]
        if name == RECOVERED_TABLE:
            require(columns[name] == RECOVERED_COLUMNS, "recovered_schema_changed")
            require("WITHOUT ROWID" not in sql.upper(), "recovered_rowid_required")
        if name in TARGETS:
            require(
                any(c[1] == "id" and c[2].upper() == "INTEGER" and c[5] == 1 for c in info),
                "target_primary_key_changed",
            )
        for fk in connection.execute(f"PRAGMA foreign_key_list({identifier(name)})"):
            if fk[2] in (*TARGETS, RECOVERED_TABLE):
                require(
                    name in {"ai_analyses", "trades"}
                    and fk[2:5] == ("signals", "signal_id", "id")
                    and fk[5] in {"NO ACTION", "RESTRICT"}
                    and fk[6] in {"NO ACTION", "RESTRICT"},
                    "unexpected_target_foreign_key",
                )
    require(columns.keys() >= REQUIRED_TABLES, "required_table_missing")
    for name, needed in {
        "signals": {"id", "strategy", "symbol", "created_at"},
        "scan_history": {"id"},
        "ai_analyses": {"id", "signal_id", "scenario_name"},
        "trades": {"id", "signal_id"},
        "bot_stats": {"id", "stat_name"},
    }.items():
        require(needed <= set(columns[name]), "required_column_missing")
    require(
        connection.execute("PRAGMA foreign_key_check").fetchone() is None,
        "existing_foreign_key_violation",
    )
    return {
        "format": "rapot-sqlite-logical-v1",
        "schema_sha256": hashed.hexdigest(),
        "schema_objects": len(rows),
        "pragmas": {
            name: connection.execute("PRAGMA " + name).fetchone()[0]
            for name in ("user_version", "application_id", "encoding")
        },
    }, columns


def target_predicate(table: str) -> tuple[str, tuple]:
    if table == RECOVERED_TABLE:
        return f"({RECOVERED_BODY}) OR ({RECOVERED_LOOKUP})", ()
    if table == "signals":
        return "t." + SIGNAL_MATCH, ()
    if table == "scan_history":
        return "1", ()
    if table == "ai_analyses":
        placeholders = ",".join("?" for _ in LEGACY_AI_SCENARIOS)
        return (
            f"({RELATED_SIGNAL}) OR (t.signal_id IS NULL AND t.scenario_name IN ({placeholders}))",
            LEGACY_AI_SCENARIOS,
        )
    if table == "trades":
        return RELATED_SIGNAL, ()
    require(table == "bot_stats", "unknown_target")
    return f"t.stat_name IN ({','.join('?' for _ in LEGACY_STATS)})", LEGACY_STATS


def recovered_index_targets(connection: sqlite3.Connection, budget: Budget) -> set[int]:
    """Prove small index fragments by PK lookup and one streamed recovered-body scan.

    The recovery table's id is an original record id, NOT its unique row identity.
    Retain bounded candidate keys only; never materialize the multi-million signal table.
    """
    candidates: dict[tuple[int, str], list[int]] = {}
    text_bytes = 0
    for count, (rowid, text, signal_id) in enumerate(
        connection.execute(
            f"SELECT t.rowid,t.c0,t.c1 FROM lost_and_found t WHERE {RECOVERED_INDEX}"
        ),
        1,
    ):
        budget.check()
        text_bytes += len(text.encode("utf-8"))
        require(
            count <= MAX_RECOVERED_INDEX_ROWS and text_bytes <= MAX_RECOVERED_INDEX_BYTES,
            "recovered_index_budget_exceeded",
        )
        candidates.setdefault((signal_id, text), []).append(rowid)
    selected: set[int] = set()
    for signal_id, text in candidates:
        budget.check()
        row = connection.execute(
            "SELECT symbol,created_at FROM signals WHERE id=? AND " + SIGNAL_MATCH,
            (signal_id,),
        ).fetchone()
        if row is not None and text in row:
            selected.update(candidates[(signal_id, text)])
    if candidates:
        for signal_id, symbol, created_at in connection.execute(
            f"SELECT t.id,t.c1,t.c9 FROM lost_and_found t WHERE {RECOVERED_BODY}"
        ):
            budget.check()
            selected.update(candidates.get((signal_id, symbol), ()))
            selected.update(candidates.get((signal_id, created_at), ()))
    return selected


def measure(connection: sqlite3.Connection, budget: Budget) -> dict:
    """One streaming traversal per table, including unrelated/recovery tables."""
    common, columns = schema(connection)
    recovered = recovered_index_targets(connection, budget) if RECOVERED_TABLE in columns else set()
    before, after, targets = {}, {}, {}
    for table, names in columns.items():
        total, kept, selected = Accumulator(), Accumulator(), Accumulator()
        if table in (*TARGETS, RECOVERED_TABLE):
            predicate, params = target_predicate(table)
            key = "t.rowid" if table == RECOVERED_TABLE else "0"
            sql = f"SELECT t.*, ({predicate}), {key} FROM {identifier(table)} t"
        else:
            sql, params = f"SELECT t.*, 0, 0 FROM {identifier(table)} t", ()
        for row in connection.execute(sql, params):
            budget.check()
            values = row[:-2]
            target = bool(row[-2]) or (table == RECOVERED_TABLE and row[-1] in recovered)
            hashed = row_digest(values)
            total.add(hashed)
            if not target:
                kept.add(hashed)
            else:
                selected.add(hashed)
                if table == "trades":
                    changed = list(values)
                    changed[names.index("signal_id")] = None
                    kept.add(row_digest(tuple(changed)))
        before[table], after[table] = total.result(), kept.result()
        if table in (*TARGETS, RECOVERED_TABLE):
            targets[table] = selected.result()
    return {
        "before": {**common, "tables": before},
        "expected_after": {**common, "tables": after},
        "targets": targets,
    }


def plan_body(connection: sqlite3.Connection, path: Path, budget: Budget) -> dict:
    return {
        "schema": "rapot-legacy-history-plan-v1",
        "database": file_identity(path),
        "scope": {
            "signal_strategies": list(STRATEGIES),
            "scan_history": "all_legacy_scanner_rows",
            "ai_analyses": "target_signal_id_or_unlinked_exact_legacy_scenario",
            "unlinked_ai_scenarios": list(LEGACY_AI_SCENARIOS),
            "trades": "preserve_row_only_clear_target_signal_id",
            "bot_stat_keys": list(LEGACY_STATS),
            "lost_and_found": "exact_legacy_body_lookup_or_proven_symbol_date_index",
            "recovered_lookup_timeframes": list(RECOVERED_TIMEFRAMES),
            "recovered_index_max_rows": MAX_RECOVERED_INDEX_ROWS,
            "other_tables": "preserve_all",
        },
        **measure(connection, budget),
    }


def create_plan(path: Path, *, budget: Budget | None = None) -> dict:
    budget = budget or Budget()
    original = file_identity(path)
    connection = connect(path, write=False, budget=budget)
    try:
        connection.execute("BEGIN")
        body = plan_body(connection, path, budget)
        require(file_identity(path) == original, "database_identity_changed")
        return {**body, "plan_sha256": digest(body), "observed_at": datetime.now(UTC).isoformat()}
    finally:
        connection.rollback()
        connection.close()


def read_proof(path: Path, expected: str) -> dict:
    require(bool(re.fullmatch(r"[a-f0-9]{64}", expected)), "invalid_proof_hash")
    file_identity(path)
    require(path.stat().st_size <= MAX_PROOF_BYTES, "proof_budget_exceeded")
    with path.open("rb") as stream:
        raw = stream.read(MAX_PROOF_BYTES + 1)
    require(len(raw) <= MAX_PROOF_BYTES, "proof_budget_exceeded")
    require(hashlib.sha256(raw).hexdigest() == expected, "proof_hash_mismatch")
    value = json.loads(raw)
    require(isinstance(value, dict), "invalid_proof")
    return value


def recent(raw: Any, now: datetime, maximum: int) -> None:
    require(isinstance(raw, str), "proof_timestamp_missing")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        require(parsed.tzinfo is not None, "proof_timezone_missing")
        age = (now - parsed).total_seconds()
    except (TypeError, ValueError):
        raise CleanupError("invalid_proof_timestamp") from None
    require(0 <= age <= maximum, "proof_not_fresh")


def verify_evidence(plan: dict, backup: dict, retirement: dict, now: datetime) -> None:
    require(
        backup.get("schema") == "rapot-sqlite-binary-backup-v1"
        and backup.get("stage") == "binary_snapshot_independent_restore_verified"
        and backup.get("verified") is True
        and backup.get("source_read_only") is True
        and backup.get("production_restore_performed") is False
        and backup.get("integrity_snapshot") == "ok"
        and backup.get("integrity_restored") == "ok"
        and backup.get("verification_method") == "local_sql_dump_restore_and_typed_fingerprint",
        "backup_not_independently_verified",
    )
    recent(backup.get("snapshot_at"), now, BACKUP_MAX_AGE)
    require(backup.get("fingerprint") == plan["before"], "backup_database_mismatch")
    fingerprint_hash = hashlib.sha256(
        json.dumps(plan["before"], sort_keys=True).encode()
    ).hexdigest()
    require(
        backup.get("snapshot_fingerprint_sha256") == fingerprint_hash
        and backup.get("restored_fingerprint_sha256") == fingerprint_hash,
        "backup_fingerprint_mismatch",
    )
    snapshot = backup.get("remote_snapshot_receipt", {})
    transfer = backup.get("remote_transfer_receipt", {})
    snapshot_hash = backup.get("snapshot_sha256", "")
    require(
        isinstance(snapshot_hash, str)
        and re.fullmatch(r"[a-f0-9]{64}", snapshot_hash)
        and snapshot.get("snapshot_sha256") == snapshot_hash
        and transfer.get("snapshot_sha256") == snapshot_hash
        and backup.get("local_artifact_sha256") == snapshot_hash
        and snapshot.get("source_path") == plan["database"]["path"]
        and type(backup.get("snapshot_bytes")) is int
        and backup["snapshot_bytes"] > 0
        and snapshot.get("snapshot_bytes") == backup["snapshot_bytes"]
        and transfer.get("snapshot_bytes") == backup["snapshot_bytes"],
        "backup_artifact_binding_failed",
    )
    require(
        retirement.get("schema") == "rapot-legacy-history-retirement-v1"
        and retirement.get("database") == plan["database"]
        and bool(re.fullmatch(r"[a-f0-9]{40}", str(retirement.get("source_sha", ""))))
        and bool(re.fullmatch(r"[a-f0-9]{40}", str(backup.get("api_source_sha", ""))))
        and bool(re.fullmatch(r"sha256:[a-f0-9]{64}", str(retirement.get("api_image", ""))))
        and bool(re.fullmatch(r"sha256:[a-f0-9]{64}", str(backup.get("source_image", ""))))
        and all(
            retirement.get(key) is True
            for key in (
                "legacy_bot_absent",
                "api_stopped",
                "other_writers_stopped",
                "observer_units_inactive",
                "retired_runtime_verified",
            )
        ),
        "writers_not_proven_quiescent",
    )
    recent(retirement.get("observed_at"), now, RETIREMENT_MAX_AGE)


def chunks(connection: sqlite3.Connection, table: str, budget: Budget) -> Iterator[list[int]]:
    if table == RECOVERED_TABLE:
        yield from recovered_chunks(connection, budget)
        return
    predicate, params = target_predicate(table)
    last = None
    while True:
        budget.check(force=True)
        position = "t.id>? AND " if last is not None else ""
        bindings = (last, *params, CHUNK_ROWS) if last is not None else (*params, CHUNK_ROWS)
        rows = connection.execute(
            f"SELECT t.id FROM {identifier(table)} t WHERE {position}({predicate}) "
            "ORDER BY t.id LIMIT ?",
            bindings,
        ).fetchall()
        if not rows:
            break
        result = [row[0] for row in rows]
        last = result[-1]
        yield result


def recovered_chunks(connection: sqlite3.Connection, budget: Budget) -> Iterator[list[int]]:
    selected = recovered_index_targets(connection, budget)
    predicate, _ = target_predicate(RECOVERED_TABLE)
    last = None
    while True:
        budget.check(force=True)
        where = "WHERE t.rowid>?" if last is not None else ""
        bindings = (last, CHUNK_ROWS) if last is not None else (CHUNK_ROWS,)
        rows = connection.execute(
            f"SELECT t.rowid, ({predicate}) FROM lost_and_found t {where} ORDER BY t.rowid LIMIT ?",
            bindings,
        ).fetchall()
        if not rows:
            return
        last = rows[-1][0]
        targets = [rowid for rowid, matched in rows if matched or rowid in selected]
        if targets:
            yield targets


def apply_plan(
    path: Path,
    plan: dict,
    *,
    expected_plan_sha256: str,
    backup: dict,
    retirement: dict,
    budget: Budget | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict:
    """Apply only after a caller has hash-verified both external evidence documents."""
    budget = budget or Budget()
    body = {key: value for key, value in plan.items() if key not in {"plan_sha256", "observed_at"}}
    require(plan.get("plan_sha256") == expected_plan_sha256 == digest(body), "plan_hash_mismatch")
    verify_evidence(plan, backup, retirement, now())
    require(file_identity(path) == plan["database"], "database_identity_changed")
    connection = connect(path, write=True, budget=budget)
    try:
        pages = connection.execute("PRAGMA page_count").fetchone()[0]
        page_size = connection.execute("PRAGMA page_size").fetchone()[0]
        require(
            connection.execute("PRAGMA journal_mode").fetchone()[0] in {"wal", "delete"},
            "unsafe_journal_mode",
        )
        budget.path, budget.journal_limit = path, pages * page_size * 2 + WORKING_BYTES
        budget.initial_journal = journal_bytes(path)
        require(
            shutil.disk_usage(path.parent).free
            >= (RESERVE_BYTES + WORKING_BYTES + budget.journal_limit),
            "insufficient_transaction_disk_budget",
        )
        connection.execute("BEGIN IMMEDIATE")
        require(plan_body(connection, path, budget) == body, "database_changed_since_plan")
        changed = {}
        for table in (
            RECOVERED_TABLE,
            "trades",
            "ai_analyses",
            "scan_history",
            "bot_stats",
            "signals",
        ):
            if table not in plan["targets"]:
                continue
            changed[table] = 0
            for ids in chunks(connection, table, budget):
                placeholders = ",".join("?" for _ in ids)
                action = (
                    "UPDATE trades SET signal_id=NULL"
                    if table == "trades"
                    else ("DELETE FROM " + identifier(table))
                )
                key = "rowid" if table == RECOVERED_TABLE else "id"
                result = connection.execute(f"{action} WHERE {key} IN ({placeholders})", ids)
                require(result.rowcount == len(ids), "batch_change_count_mismatch")
                changed[table] += result.rowcount
            require(changed[table] == plan["targets"][table]["count"], "target_count_mismatch")
        require(connection.total_changes == sum(changed.values()), "unexpected_change_count")
        after = measure(connection, budget)
        require(after["before"] == plan["expected_after"], "protected_data_changed")
        require(
            all(value["count"] == 0 for value in after["targets"].values()), "target_rows_remain"
        )
        require(file_identity(path) == plan["database"], "database_identity_changed")
        # The backup must still be fresh at commit; all writes remain uncommitted until here.
        recent(backup["snapshot_at"], now(), BACKUP_MAX_AGE)
        budget.check(force=True)
        connection.commit()
        return {
            "schema": "rapot-legacy-history-cleanup-v1",
            "status": "committed",
            "plan_sha256": expected_plan_sha256,
            "changed": changed,
            "after": after["before"],
            "completed_at": now().isoformat(),
            "financial_rows_deleted": 0,
            "schema_changed": False,
            "vacuum_performed": False,
        }
    except BaseException:
        # Cancellation/disk guard must not interrupt the rollback itself.
        connection.set_progress_handler(None, 0)
        connection.rollback()
        raise
    finally:
        connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--database", type=Path)
    parser.add_argument("--plan-file", type=Path)
    parser.add_argument("--expected-plan-sha256")
    parser.add_argument("--backup-proof", type=Path)
    parser.add_argument("--expected-backup-sha256")
    parser.add_argument("--retirement-proof", type=Path)
    parser.add_argument("--expected-retirement-sha256")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=float, default=1800)
    args = parser.parse_args(argv)
    if not args.plan and not args.apply:
        print(json.dumps({"status": "no_io", "plan_or_apply_required": True}))
        return 0
    budget = Budget(args.timeout)
    try:
        require(
            args.database is not None and args.output is not None, "database_and_output_required"
        )
        # Reserve an exclusive private receipt before any possible mutation.
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            if args.plan:
                result = create_plan(args.database, budget=budget)
            else:
                require(
                    all(
                        (
                            args.plan_file,
                            args.expected_plan_sha256,
                            args.backup_proof,
                            args.expected_backup_sha256,
                            args.retirement_proof,
                            args.expected_retirement_sha256,
                        )
                    ),
                    "apply_evidence_required",
                )
                require(args.plan_file.stat().st_size <= MAX_PROOF_BYTES, "plan_budget_exceeded")
                plan = json.loads(args.plan_file.read_text(encoding="utf-8"))
                result = apply_plan(
                    args.database,
                    plan,
                    expected_plan_sha256=args.expected_plan_sha256,
                    backup=read_proof(args.backup_proof, args.expected_backup_sha256),
                    retirement=read_proof(args.retirement_proof, args.expected_retirement_sha256),
                    budget=budget,
                )
            output.write(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n")
            output.flush()
            os.fsync(output.fileno())
        print(
            json.dumps(
                {
                    "status": result.get("status", "planned"),
                    "plan_sha256": result.get("plan_sha256"),
                }
            )
        )
        return 0
    except Exception as exc:
        code = str(exc) if isinstance(exc, CleanupError) else (budget.failure or type(exc).__name__)
        print(json.dumps({"status": "failed", "reason": code}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
