# Backend Reliability Backlog

This backlog is prioritized for production hardening and ordered by implementation sequence.

## P0

1. [x] P0-1: Health/readiness must fail when DB or realtime services are unhealthy.
2. [x] P0-2: Realtime startup must fail-fast instead of silent startup degradation.
3. [x] P0-3: Async scanner must report failed status and avoid false success summaries.
4. [x] P0-4: Remove critical-path `print()` logging from startup/auth/system paths.
5. [x] P0-5: Disallow insecure JWT fallback secret in non-local environments.

## P1

1. [ ] P1-1: Replace remaining backend `print()` calls with structured logger usage.
2. [ ] P1-2: Normalize error handling with `logger.exception(...)` at boundary catches.
3. [ ] P1-3: Add retry/backoff and explicit error logging for upstream HTTP non-200 responses.
4. [ ] P1-4: Add per-message parse guards in websocket ingest path to prevent stream resets.
5. [ ] P1-5: Add degraded response metadata (`degraded`, `error_code`, `source_status`) to fallback endpoints.
6. [ ] P1-6: Mask secret-bearing values in logs (DATABASE_URL, tokens, auth headers).
7. [ ] P1-7: Consolidate env/config loading to `settings.py` as single source of truth.
8. [ ] P1-8: Persist scan/signal counters to DB (`bot_stats`) and restore at startup.
9. [ ] P1-9: Add distributed lock for scheduler overlap safety in multi-process deployments.

## P2

1. [ ] P2-1: Add `orders` lifecycle model + startup reconciliation for active orders.
2. [ ] P2-2: Add centralized secret redaction filter in logger and Telegram handler.
3. [ ] P2-3: Improve system log endpoint error semantics (distinguish missing file vs unexpected failures).
4. [ ] P2-4: Replace in-memory-only health state with repository-backed health signals.
5. [ ] P2-5: Move to structured JSON logging schema with correlation fields.
