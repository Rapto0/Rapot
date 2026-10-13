"""Real SQLite transactions and fail-closed evidence gates; no production data."""

import hashlib
import json
import sqlite3
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from scripts import retire_legacy_history as cleanup

NOW = datetime(2026, 10, 12, 16, 0, tzinfo=UTC)
SECRET = "synthetic-private-content-must-not-be-reported"


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "fixture.sqlite3"
    with sqlite3.connect(path) as db:
        db.executescript("""
            PRAGMA foreign_keys=ON;
            CREATE TABLE signals(id INTEGER PRIMARY KEY, strategy TEXT, details BLOB,
                                 symbol TEXT, created_at TEXT);
            CREATE TABLE scan_history(id INTEGER PRIMARY KEY, mode TEXT);
            CREATE TABLE ai_analyses(id INTEGER PRIMARY KEY, signal_id INTEGER REFERENCES signals(id),
                                    scenario_name TEXT, analysis_text TEXT);
            CREATE TABLE trades(id INTEGER PRIMARY KEY, signal_id INTEGER REFERENCES signals(id),
                                price REAL, quantity REAL, pnl REAL, status TEXT);
            CREATE TABLE bot_stats(id INTEGER PRIMARY KEY, stat_name TEXT UNIQUE, stat_value TEXT);
            CREATE TABLE lost_and_found(rootpgno INTEGER, pgno INTEGER, nfield INTEGER,
                                        id INTEGER, c0, c1, c2, c3, c4, c5, c6, c7, c8, c9);
        """)
        for table in sorted(cleanup.ALARM_TABLES | {"orders", "research_workspaces"}):
            db.execute(f'CREATE TABLE "{table}" (id TEXT PRIMARY KEY, payload BLOB)')
            db.execute(f'INSERT INTO "{table}" VALUES (?, ?)', ("keep", b"\x00\xff"))
        db.executemany(
            "INSERT INTO signals(id,strategy,details) VALUES (?,?,?)",
            [
                (1, "COMBO", SECRET),
                (2, "HUNTER", b"\x01"),
                (3, "OTHER", "keep"),
                (4, "combo", "case-sensitive"),
                (5, "COMBO-extra", "keep"),
            ],
        )
        db.executemany("INSERT INTO scan_history VALUES (?,?)", [(1, "sync"), (2, "async")])
        db.executemany(
            "INSERT INTO trades VALUES (?,?,?,?,?,?)",
            [
                (1, 1, 123.25, 7.0, -2.4, "OPEN"),
                (2, 3, 12.0, 3.0, 4.0, "CLOSED"),
            ],
        )
        db.executemany(
            "INSERT INTO ai_analyses VALUES (?,?,?,?)",
            [
                (1, 1, "arbitrary linked", SECRET),
                (2, None, "MANUAL", SECRET),
                (3, 3, cleanup.LEGACY_AI_SCENARIOS[0], SECRET),
                (4, None, cleanup.LEGACY_AI_SCENARIOS[0] + " extra", SECRET),
                (5, None, "COMBO AL", SECRET),
                *[
                    (10 + i, None, name, SECRET)
                    for i, name in enumerate(cleanup.LEGACY_AI_SCENARIOS)
                ],
            ],
        )
        db.executemany(
            "INSERT INTO bot_stats VALUES (?,?,?)",
            [(i + 1, name, SECRET) for i, name in enumerate(cleanup.LEGACY_STATS)]
            + [
                (100, "advanced_alarm_delivery_pause", SECRET),
                (101, "server_alarm_cursor", SECRET),
                (102, "custom_key", SECRET),
            ],
        )
        db.execute("UPDATE signals SET symbol='AAA',created_at='2026-01-01' WHERE id=1")
        db.execute(
            "INSERT INTO lost_and_found(rootpgno,pgno,nfield,id,c0,c1,c2) VALUES (1,2,3,4,?,?,?)",
            (SECRET, "COMBO", None),
        )
    return path


def evidence(plan):
    fingerprint_hash = hashlib.sha256(
        json.dumps(plan["before"], sort_keys=True).encode()
    ).hexdigest()
    snapshot_hash = "a" * 64
    artifact = {"snapshot_sha256": snapshot_hash, "snapshot_bytes": 32768}
    snapshot_receipt = {
        "stage": "binary_snapshot_completed",
        "run_id": "synthetic",
        "snapshot_bytes": artifact["snapshot_bytes"],
        "source_path": plan["database"]["path"],
    }
    receipt_hash = hashlib.sha256(
        json.dumps(snapshot_receipt, separators=(",", ":")).encode()
    ).hexdigest()
    backup = {
        "schema": "rapot-sqlite-binary-backup-v1",
        "stage": "binary_snapshot_independent_restore_verified",
        "verified": True,
        "source_read_only": True,
        "production_restore_performed": False,
        "integrity_snapshot": "ok",
        "integrity_restored": "ok",
        "verification_method": "local_sql_dump_restore_and_typed_fingerprint",
        "snapshot_at": (NOW - timedelta(hours=2)).isoformat(),
        "fingerprint": deepcopy(plan["before"]),
        "snapshot_fingerprint_sha256": fingerprint_hash,
        "restored_fingerprint_sha256": fingerprint_hash,
        "local_artifact_sha256": snapshot_hash,
        "api_source_sha": "1" * 40,
        "source_image": "sha256:" + "2" * 64,
        "remote_snapshot_receipt": snapshot_receipt,
        "remote_transfer_receipt": {
            **artifact,
            "stage": "binary_transfer_completed",
            "run_id": "synthetic",
            "snapshot_receipt_sha256": receipt_hash,
        },
        "remote_receipt_sha256": receipt_hash,
        **artifact,
    }
    retirement = {
        "schema": "rapot-legacy-history-retirement-v1",
        "database": plan["database"],
        "observed_at": NOW.isoformat(),
        "source_sha": "3" * 40,
        "api_image": "sha256:" + "4" * 64,
        "legacy_bot_absent": True,
        "api_stopped": True,
        "other_writers_stopped": True,
        "observer_units_inactive": True,
        "retired_runtime_verified": True,
    }
    return backup, retirement


def apply(database, plan, **kwargs):
    backup, retirement = evidence(plan)
    return cleanup.apply_plan(
        database,
        plan,
        expected_plan_sha256=plan["plan_sha256"],
        backup=backup,
        retirement=retirement,
        now=lambda: NOW,
        **kwargs,
    )


def test_plan_is_read_only_and_secret_free(database):
    raw = database.read_bytes()
    plan = cleanup.create_plan(database)
    assert database.read_bytes() == raw
    assert SECRET not in json.dumps(plan)
    assert plan["targets"]["signals"]["count"] == 2
    assert plan["targets"]["scan_history"]["count"] == 2
    assert plan["targets"]["ai_analyses"]["count"] == 9
    assert plan["targets"]["trades"]["count"] == 1
    assert plan["targets"]["bot_stats"]["count"] == 12
    assert len(plan["before"]["tables"]) == 15
    assert cleanup.create_plan(database)["plan_sha256"] == plan["plan_sha256"]


@pytest.mark.parametrize("field", ["source_path", "snapshot_bytes", "run_id"])
def test_transfer_receipt_binds_unhashed_snapshot_stage(database, field):
    plan = cleanup.create_plan(database)
    backup, retirement = evidence(plan)
    assert "snapshot_sha256" not in backup["remote_snapshot_receipt"]
    cleanup.verify_evidence(plan, backup, retirement, NOW)
    backup["remote_snapshot_receipt"][field] = "changed"
    with pytest.raises(cleanup.CleanupError, match="backup_artifact_binding_failed"):
        cleanup.apply_plan(
            database,
            plan,
            expected_plan_sha256=plan["plan_sha256"],
            backup=backup,
            retirement=retirement,
            now=lambda: NOW,
        )
    assert cleanup.create_plan(database)["before"] == plan["before"]


@pytest.mark.parametrize("wal", [False, True])
def test_atomic_cleanup_preserves_financial_alarm_and_unproven_data(database, wal):
    if wal:
        with sqlite3.connect(database) as db:
            db.execute("PRAGMA journal_mode=WAL")
    plan = cleanup.create_plan(database)
    receipt = apply(database, plan)
    assert receipt["status"] == "committed"
    assert receipt["after"] == plan["expected_after"]
    assert receipt["financial_rows_deleted"] == 0
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT id FROM signals ORDER BY id").fetchall() == [(3,), (4,), (5,)]
        assert db.execute("SELECT * FROM trades ORDER BY id").fetchall() == [
            (1, None, 123.25, 7.0, -2.4, "OPEN"),
            (2, 3, 12.0, 3.0, 4.0, "CLOSED"),
        ]
        assert db.execute("SELECT id FROM ai_analyses ORDER BY id").fetchall() == [
            (2,),
            (3,),
            (4,),
            (5,),
        ]
        assert db.execute("SELECT stat_name FROM bot_stats ORDER BY id").fetchall() == [
            ("advanced_alarm_delivery_pause",),
            ("server_alarm_cursor",),
            ("custom_key",),
        ]
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    assert cleanup.create_plan(database)["before"] == plan["expected_after"]


@pytest.mark.parametrize(
    "table,sql",
    [
        ("signals", "UPDATE signals SET details='changed' WHERE id=1"),
        ("orders", "UPDATE orders SET payload='changed'"),
        ("advanced_alarm_events", "UPDATE advanced_alarm_events SET payload='changed'"),
        ("lost_and_found", "UPDATE lost_and_found SET c1='changed'"),
        ("ai_analyses", "UPDATE ai_analyses SET analysis_text='changed' WHERE id=2"),
    ],
)
def test_apply_rejects_any_postplan_data_change(database, table, sql):
    plan = cleanup.create_plan(database)
    with sqlite3.connect(database) as db:
        db.execute(sql)
    before = cleanup.create_plan(database)["before"]
    with pytest.raises(cleanup.CleanupError, match="database_changed_since_plan"):
        apply(database, plan)
    assert cleanup.create_plan(database)["before"] == before


@pytest.mark.parametrize(
    "side,key,value,reason",
    [
        ("backup", "verified", False, "backup_not_independently_verified"),
        ("backup", "integrity_restored", "failed", "backup_not_independently_verified"),
        ("backup", "snapshot_at", (NOW - timedelta(hours=7)).isoformat(), "proof_not_fresh"),
        ("backup", "snapshot_at", (NOW + timedelta(seconds=1)).isoformat(), "proof_not_fresh"),
        ("backup", "restored_fingerprint_sha256", "0" * 64, "backup_fingerprint_mismatch"),
        ("backup", "local_artifact_sha256", "0" * 64, "backup_artifact_binding_failed"),
        ("retirement", "api_stopped", False, "writers_not_proven_quiescent"),
        ("retirement", "legacy_bot_absent", False, "writers_not_proven_quiescent"),
        ("retirement", "other_writers_stopped", False, "writers_not_proven_quiescent"),
        ("retirement", "observer_units_inactive", False, "writers_not_proven_quiescent"),
        ("retirement", "observed_at", (NOW - timedelta(minutes=6)).isoformat(), "proof_not_fresh"),
    ],
)
def test_missing_or_stale_external_evidence_never_changes_database(
    database, side, key, value, reason
):
    plan = cleanup.create_plan(database)
    backup, retirement = evidence(plan)
    (backup if side == "backup" else retirement)[key] = value
    with pytest.raises(cleanup.CleanupError, match=reason):
        cleanup.apply_plan(
            database,
            plan,
            expected_plan_sha256=plan["plan_sha256"],
            backup=backup,
            retirement=retirement,
            now=lambda: NOW,
        )
    assert cleanup.create_plan(database)["before"] == plan["before"]


def test_forged_plan_or_backup_contents_rejected(database):
    plan = cleanup.create_plan(database)
    backup, retirement = evidence(plan)
    plan["targets"]["signals"]["count"] += 1
    with pytest.raises(cleanup.CleanupError, match="plan_hash_mismatch"):
        cleanup.apply_plan(
            database,
            plan,
            expected_plan_sha256=plan["plan_sha256"],
            backup=backup,
            retirement=retirement,
            now=lambda: NOW,
        )
    plan = cleanup.create_plan(database)
    backup["fingerprint"]["tables"]["signals"]["count"] += 1
    with pytest.raises(cleanup.CleanupError, match="backup_database_mismatch"):
        cleanup.apply_plan(
            database,
            plan,
            expected_plan_sha256=plan["plan_sha256"],
            backup=backup,
            retirement=retirement,
            now=lambda: NOW,
        )


def test_cancellation_after_a_real_write_rolls_back_every_table(database, monkeypatch):
    plan = cleanup.create_plan(database)
    original = cleanup.chunks

    def interrupted(connection, table, budget):
        for ids in original(connection, table, budget):
            yield ids
            raise KeyboardInterrupt()

    monkeypatch.setattr(cleanup, "chunks", interrupted)
    with pytest.raises(KeyboardInterrupt):
        apply(database, plan)
    assert cleanup.create_plan(database)["before"] == plan["before"]


def test_disk_guard_after_partial_deletion_rolls_back(database, monkeypatch):
    plan = cleanup.create_plan(database)
    original = cleanup.chunks

    def interrupted(connection, table, budget):
        for ids in original(connection, table, budget):
            yield ids
            if table == "ai_analyses":
                monkeypatch.setattr(cleanup.shutil, "disk_usage", lambda _: SimpleNamespace(free=0))
                budget.check(force=True)

    monkeypatch.setattr(cleanup, "chunks", interrupted)
    with pytest.raises(cleanup.CleanupError, match="disk_reserve_reached"):
        apply(database, plan)
    assert cleanup.create_plan(database)["before"] == plan["before"]


def test_low_disk_rejected_before_first_write(database, monkeypatch):
    plan = cleanup.create_plan(database)
    monkeypatch.setattr(
        cleanup.shutil, "disk_usage", lambda _: SimpleNamespace(free=600 * cleanup.MIB)
    )
    with pytest.raises(cleanup.CleanupError, match="insufficient_transaction_disk_budget"):
        apply(database, plan)
    assert cleanup.create_plan(database)["before"] == plan["before"]


def test_deadline_and_wal_growth_guards(database, monkeypatch):
    budget = cleanup.Budget(1)
    monkeypatch.setattr(cleanup.time, "monotonic", lambda: budget.deadline + 1)
    assert budget.progress() == 1
    assert budget.failure == "deadline_exceeded"
    monkeypatch.undo()
    budget = cleanup.Budget()
    budget.path, budget.journal_limit = database, 100
    database.with_name(database.name + "-wal").write_bytes(b"0" * 101)
    with pytest.raises(cleanup.CleanupError, match="journal_budget_exceeded"):
        budget.check(force=True)


def test_replay_of_consumed_plan_is_rejected(database):
    plan = cleanup.create_plan(database)
    apply(database, plan)
    with pytest.raises(cleanup.CleanupError, match="database_changed_since_plan"):
        apply(database, plan)


def test_chunks_cover_negative_keys_and_large_scope_without_id_materialization(database):
    with sqlite3.connect(database) as db:
        db.executemany(
            "INSERT INTO signals(id,strategy,details) VALUES (?,?,?)",
            [
                (-(1 << 63), "HUNTER", "minimum"),
                *[(i, "COMBO", "synthetic") for i in range(100, 1300)],
            ],
        )
    plan = cleanup.create_plan(database)
    with sqlite3.connect(database) as db:
        batches = cleanup.chunks(db, "signals", cleanup.Budget())
        count = 0
        for batch in batches:
            assert 1 <= len(batch) <= cleanup.CHUNK_ROWS
            count += len(batch)
        assert count == 1203
    assert apply(database, plan)["changed"]["signals"] == 1203


def test_unknown_trigger_or_foreign_key_fails_closed(database):
    with sqlite3.connect(database) as db:
        db.execute("CREATE TRIGGER danger AFTER DELETE ON signals BEGIN DELETE FROM orders; END")
    with pytest.raises(cleanup.CleanupError, match="triggers_not_supported"):
        cleanup.create_plan(database)
    with sqlite3.connect(database) as db:
        db.execute("DROP TRIGGER danger")
        db.execute("CREATE TABLE extra(signal_id INTEGER REFERENCES signals(id) ON DELETE CASCADE)")
    with pytest.raises(cleanup.CleanupError, match="unexpected_target_foreign_key"):
        cleanup.create_plan(database)


def test_preexisting_invalid_fk_is_not_hidden(database):
    with sqlite3.connect(database) as db:
        db.execute("UPDATE trades SET signal_id=999 WHERE id=1")
    with pytest.raises(cleanup.CleanupError, match="existing_foreign_key_violation"):
        cleanup.create_plan(database)


def test_real_orm_schema_supported_and_never_migrated(tmp_path):
    from sqlalchemy import create_engine

    from models import Base

    path = tmp_path / "actual-schema.sqlite3"
    engine = create_engine("sqlite:///" + path.as_posix())
    Base.metadata.create_all(engine)
    engine.dispose()
    plan = cleanup.create_plan(path)
    assert len(plan["before"]["tables"]) == 14
    assert apply(path, plan)["after"] == plan["before"]


def test_typed_fingerprint_fixed_vectors_and_type_distinction():
    # Independent expected bytes, equivalent to the already reviewed backup codec.
    import struct

    values = (None, 7, 1.5, "Türkçe", b"\x00\xff")
    raw = b"rapot-sqlite-row-v1\0" + struct.pack(">I", 5)
    for tag, payload in [
        (b"N", b""),
        (b"I", struct.pack(">q", 7)),
        (b"F", struct.pack(">d", 1.5)),
        (b"T", "Türkçe".encode()),
        (b"B", b"\x00\xff"),
    ]:
        raw += tag + struct.pack(">Q", len(payload)) + payload
    assert cleanup.row_digest(values) == hashlib.sha256(raw).digest()
    assert len({cleanup.row_digest((value,)) for value in (None, 0, 0.0, "0", b"0")}) == 5


def test_default_cli_does_no_io(monkeypatch, capsys):
    monkeypatch.setattr(
        cleanup.sqlite3, "connect", lambda *a, **k: pytest.fail("Unexpected database I/O")
    )
    assert cleanup.main([]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "no_io"


def test_cli_plan_exclusive_output_and_proof_hash(database, tmp_path, capsys):
    output = tmp_path / "plan.json"
    args = ["--plan", "--database", str(database), "--output", str(output)]
    assert cleanup.main(args) == 0
    original = output.read_bytes()
    assert cleanup.main(args) == 1
    assert output.read_bytes() == original
    checksum = hashlib.sha256(original).hexdigest()
    assert cleanup.read_proof(output, checksum)["schema"] == "rapot-legacy-history-plan-v1"
    with pytest.raises(cleanup.CleanupError, match="proof_hash_mismatch"):
        cleanup.read_proof(output, "0" * 64)
    assert SECRET not in capsys.readouterr().out


def recovered_body(signal_id=101, **changes):
    row = dict(
        zip(
            cleanup.RECOVERED_COLUMNS,
            [
                1,
                2,
                10,
                signal_id,
                None,
                "BBB",
                "BIST",
                "COMBO",
                "AL",
                "1D",
                "AL4",
                123.5,
                SECRET,
                "2025-01-01",
            ],
            strict=True,
        )
    )
    return {**row, **changes}


def add_recovered(db, *, nfield=2, original_id=55, **values):
    row = dict.fromkeys(cleanup.RECOVERED_COLUMNS)
    row.update(rootpgno=1, pgno=2, nfield=nfield, id=original_id, **values)
    placeholders = ",".join("?" for _ in row)
    return db.execute(
        f"INSERT INTO lost_and_found VALUES ({placeholders})", tuple(row.values())
    ).lastrowid


def test_recovered_exact_provenance_preserves_unmatched_and_duplicate_original_ids(database):
    with sqlite3.connect(database) as db:
        body = recovered_body()
        target_body = db.execute(
            "INSERT INTO lost_and_found VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", tuple(body.values())
        ).lastrowid
        targets = [target_body]
        targets.append(add_recovered(db, nfield=4, c0="BBB", c1="HUNTER", c2="W-FRI", c3=101))
        # Exact current signal symbol/date and recovered body symbol/date; all have the
        # same nonunique original id. Their physical rowid remains the deletion key.
        for text, original in [
            ("AAA", 1),
            ("2026-01-01", 1),
            ("BBB", 101),
            ("2025-01-01", 101),
            ("BBB", 101),
        ]:
            targets.append(add_recovered(db, c0=text, c1=original))
        kept = [
            add_recovered(db, c0="does-not-match", c1=1),
            add_recovered(db, c0="AAA", c1=3),
            add_recovered(db, c0="BBB", c1=999),
            add_recovered(db, c0="BBB", c1=101, c2="not-a-two-column-index"),
            add_recovered(db, nfield=4, c0="BBB", c1="OTHER", c2="1D", c3=101),
            add_recovered(db, nfield=4, c0="BBB", c1="COMBO", c2="unknown", c3=101),
            add_recovered(db, nfield=4, c0="BBB", c1="COMBO", c2="1D", c3=101, c4=0),
        ]
        keep_values = db.execute(
            "SELECT rowid,* FROM lost_and_found WHERE rowid NOT IN ("
            + ",".join("?" for _ in targets)
            + ") ORDER BY rowid",
            targets,
        ).fetchall()
    plan = cleanup.create_plan(database)
    assert plan["targets"]["lost_and_found"]["count"] == 7
    assert SECRET not in json.dumps(plan)
    receipt = apply(database, plan)
    assert receipt["changed"]["lost_and_found"] == 7
    with sqlite3.connect(database) as db:
        assert (
            db.execute("SELECT rowid,* FROM lost_and_found ORDER BY rowid").fetchall()
            == keep_values
        )
        assert {row[0] for row in keep_values} >= set(kept)


@pytest.mark.parametrize(
    "changes",
    [
        {"nfield": 9},
        {"c0": 0},
        {"c1": 123},
        {"c2": "US"},
        {"c3": "COMBO-extra"},
        {"c4": "BUY"},
        {"c5": None},
        {"c6": 4},
        {"c7": "123.5"},
        {"c8": None},
        {"c9": None},
    ],
)
def test_unproven_recovered_body_and_its_index_stay(database, changes):
    with sqlite3.connect(database) as db:
        row = recovered_body(**changes)
        db.execute(
            "INSERT INTO lost_and_found VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", tuple(row.values())
        )
        add_recovered(db, c0="BBB", c1=101)
    plan = cleanup.create_plan(database)
    assert plan["targets"]["lost_and_found"]["count"] == 0
    assert apply(database, plan)["changed"]["lost_and_found"] == 0


def test_recovered_candidate_budget_fails_closed(database, monkeypatch):
    with sqlite3.connect(database) as db:
        for i in range(4):
            add_recovered(db, c0="AAA", c1=i)
    raw = database.read_bytes()
    monkeypatch.setattr(cleanup, "MAX_RECOVERED_INDEX_ROWS", 3)
    with pytest.raises(cleanup.CleanupError, match="recovered_index_budget_exceeded"):
        cleanup.create_plan(database)
    assert database.read_bytes() == raw


def test_recovered_unknown_layout_refuses_interpretation(database):
    with sqlite3.connect(database) as db:
        db.execute("ALTER TABLE lost_and_found ADD COLUMN c10")
    with pytest.raises(cleanup.CleanupError, match="recovered_schema_changed"):
        cleanup.create_plan(database)


def test_recovered_late_index_survives_body_batch_deletion_as_target(database):
    with sqlite3.connect(database) as db:
        for i in range(400):
            row = recovered_body(signal_id=1000 + i)
            db.execute(
                "INSERT INTO lost_and_found VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                tuple(row.values()),
            )
        for i in range(400):
            add_recovered(db, c0="BBB", c1=1000 + i)
    plan = cleanup.create_plan(database)
    assert plan["targets"]["lost_and_found"]["count"] == 800
    assert apply(database, plan)["changed"]["lost_and_found"] == 800
    assert cleanup.create_plan(database)["before"]["tables"]["lost_and_found"]["count"] == 1


def test_recovered_repeated_original_id_proves_each_exact_body_version(database):
    with sqlite3.connect(database) as db:
        for symbol, date in [("OLD", "2024-01-01"), ("NEW", "2025-01-01")]:
            row = recovered_body(signal_id=101, c1=symbol, c9=date)
            db.execute(
                "INSERT INTO lost_and_found VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                tuple(row.values()),
            )
            add_recovered(db, c0=symbol, c1=101)
            add_recovered(db, c0=date, c1=101)
        add_recovered(db, c0="neither-version", c1=101)
    plan = cleanup.create_plan(database)
    assert plan["targets"]["lost_and_found"]["count"] == 6
    assert apply(database, plan)["changed"]["lost_and_found"] == 6
    assert cleanup.create_plan(database)["before"]["tables"]["lost_and_found"]["count"] == 2
