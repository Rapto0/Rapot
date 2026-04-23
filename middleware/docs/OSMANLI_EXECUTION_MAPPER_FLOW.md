# Osmanli Execution Mapper Flow (Broker-Agnostic Boundary)

This document defines the current mapper boundary between domain intent and broker-specific request/response handling.

## 1. Domain Intent In
- Input type: `BrokerOrderRequestPayload`
- Fields consumed:
  - `symbol`
  - `side`
  - `lots`
  - `limit_price`
  - `tif`
  - `signal_code`
  - `idempotency_key`

## 2. Mapper Output
- Mapper: `middleware/broker_adapters/osmanli_mapper.py`
- Output type: `OsmanliSubmitOrderEnvelope`
- Envelope content:
  - `endpoint_hint` (placeholder until official endpoint is confirmed)
  - `method`
  - `headers`
  - `body`

Notes:
- Current mapper uses placeholder transport keys.
- No undocumented Osmanli payload contract is assumed.
- Envelope is audit/debug-friendly and stored in execution reports on failures.

## 3. Adapter Behavior (Current)
- Adapter: `middleware/broker_adapters/osmanli.py`
- Current mode:
  - Builds mapped envelope.
  - Returns deterministic `failed` result with TODO payload.
  - Prevents accidental live usage unless explicit runtime gates are enabled.

## 4. Required Live Completion Steps
1. Replace `endpoint_hint` and body keys with official Osmanli API schema.
2. Implement official auth/token bootstrap and secure token refresh.
3. Implement HTTP transport with timeout/retry/backoff rules.
4. Map official broker statuses to internal `OrderStatus`.
5. Implement cancel/status reconciliation flow (polling or callback based on docs).
6. Add integration tests against Osmanli sandbox/UAT.
7. Enable `MW_OSMANLI_LIVE_ENABLED=true` only after UAT sign-off.
