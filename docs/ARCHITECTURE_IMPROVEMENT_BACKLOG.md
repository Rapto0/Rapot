# Architecture Improvement Backlog (ARC-001..ARC-010)

This document tracks the architecture hardening tasks implemented in this repository.

## Implementation Order

1. ARC-001
2. ARC-002
3. ARC-003
4. ARC-004
5. ARC-005
6. ARC-006
7. ARC-007
8. ARC-008
9. ARC-009
10. ARC-010

## Completed Tasks

- [x] ARC-001: Split realtime consumption into dedicated ticker and signal channels in frontend hook.
  - Files: `frontend/src/lib/hooks/use-realtime.ts`, `tests/test_frontend_contracts.py`
- [x] ARC-002: Remove direct frontend vendor dependency to Binance `exchangeInfo`; use backend contract.
  - Files: `frontend/src/components/charts/advanced-chart.tsx`
- [x] ARC-003: Centralize shared runtime/stat key names into a single module.
  - Files: `state_keys.py`, `ops_repository.py`, `market_scanner.py`, `async_scanner.py`, `scheduler.py`, `health_api.py`, `api/main.py`
- [x] ARC-004: Add OpenAPI contract snapshot generation and verification gate.
  - Files: `scripts/generate_openapi_snapshot.py`, `docs/contracts/openapi.snapshot.json`, `tests/test_openapi_snapshot.py`
- [x] ARC-005: Extract calendar API endpoints from monolithic API module into route module.
  - Files: `api/routes/calendar_routes.py`, `api/main.py`
- [x] ARC-006: Introduce transport adapter between domain scanners and realtime API publisher.
  - Files: `signal_dispatcher.py`, `market_scanner.py`, `async_scanner.py`, `api/main.py`
- [x] ARC-007: Standardize health payload contract across FastAPI and Flask health surfaces.
  - Files: `api/contracts/health_contract.py`, `api/main.py`, `health_api.py`
- [x] ARC-008: Add frontend-backend HTTP contract sync tests against OpenAPI paths.
  - Files: `tests/test_frontend_backend_contract_sync.py`
- [x] ARC-009: Add architecture boundary checks for coupling regressions.
  - Files: `tests/test_architecture_boundaries.py`
- [x] ARC-010: Persist architecture backlog and implementation traceability document.
  - Files: `docs/ARCHITECTURE_IMPROVEMENT_BACKLOG.md`
