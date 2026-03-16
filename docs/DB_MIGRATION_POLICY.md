# Database Migration Policy

## Scope
This project uses SQLite and SQLAlchemy for schema and data lifecycle.

## Official Policy
- Alembic is not used in this repository.
- Schema evolution is handled in `db_session.py`:
  - `init_db()` creates missing tables.
  - `ensure_sqlite_columns(...)` applies backward-compatible column/index updates.
- Data migrations and one-off backfills are handled in `migrate_db.py`.

## When To Change `db_session.py`
- New table/model: update `models.py`, then rely on `init_db()` + `create_all`.
- New backward-compatible column/index: extend `ensure_sqlite_columns(...)` calls in `init_db()`.
- Never add destructive schema changes here (drop/rename) without a dedicated migration plan.

## When To Change `migrate_db.py`
- Existing records must be transformed or copied.
- Legacy database data must be migrated into current SQLAlchemy models.
- Run with `--dry-run` first, then run with backup enabled.

## Standard Workflow
1. Update `models.py` and/or `db_session.py`.
2. Run tests.
3. If data movement is needed, update `migrate_db.py`.
4. Execute:
   - `python migrate_db.py --dry-run`
   - `python migrate_db.py --backup`

## Notes
- Startup path: API calls `init_db()` during application startup.
- This policy keeps schema changes deterministic without Alembic revision chains.
