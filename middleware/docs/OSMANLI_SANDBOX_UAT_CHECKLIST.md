# Osmanli Adapter Sandbox/UAT Checklist

This checklist is required before enabling live execution for Osmanli adapter.

## 1. Environment and Access
- Confirm dedicated sandbox/UAT credentials are issued by Osmanli.
- Confirm API base URL, auth URL, and allowed IP list from official docs.
- Confirm account type is spot-equity (BIST) only.
- Confirm no margin/futures entitlement exists on UAT account.
- Confirm `MW_EXECUTION_MODE=DRY_RUN` in initial onboarding phase.

## 2. Security and Secrets
- Store all credentials in env/secret manager (no hardcoded keys).
- Enforce `MW_REQUIRE_WEBHOOK_AUTH=true`.
- Set strong `MW_WEBHOOK_AUTH_TOKEN` and verify rotation procedure.
- Verify token never appears in application logs.
- Verify TLS certificate chain and hostname validation.

## 3. Contract Validation
- Validate incoming TradingView payload rejects unknown/extra fields.
- Validate unsupported `signalCode` is rejected.
- Validate signal/side mismatch is rejected.
- Validate duplicate webhook payload does not create duplicate orders.

## 4. Order Intent and Sizing
- Verify buy sizing formula:
  - `signalBudgetTL = baseBudgetTL * multiplier(signalCode)`
  - `buyLimitPrice = round_up_to_tick(close * (1 + buyBps / 10000))`
  - `buyLots = floor(signalBudgetTL / buyLimitPrice)`
- Verify `buyLots < 1` results in rejection.
- Verify sell pricing formula:
  - `sellLimitPrice = round_down_to_tick(close * (1 - sellBps / 10000))`
- Verify symbol-specific tick override behavior.

## 5. Risk Controls
- Verify `MW_TRADING_ENABLED=false` blocks live submission in LIVE mode.
- Verify max 4 open tranche guard per symbol.
- Verify sell without open tranche is rejected.
- Verify optional guardrails:
  - max symbol exposure
  - daily max loss
  - max order count per day

## 6. FIFO Tranche Behavior
- Execute at least 2 buy signals for same symbol.
- Trigger a sell signal and confirm oldest tranche is selected first.
- Confirm tranche `remaining_lots` and status updates are correct.
- Confirm partial fills update remaining lots accurately.

## 7. Broker Adapter Protocol Mapping
- Map official Osmanli order request fields to `BrokerOrderRequestPayload`.
- Map official response codes to internal order statuses:
  - `submitted`
  - `acknowledged`
  - `partially_filled`
  - `filled`
  - `cancelled`
  - `failed`
- Verify retry/backoff policy for transient failures (timeouts, 5xx, rate limit).
- Verify idempotent behavior on network retry / duplicate callback.

## 8. Auditability and Persistence
- Confirm `mw_signal_events` records each accepted event.
- Confirm `mw_orders` lifecycle states are persisted.
- Confirm `mw_execution_reports` captures broker responses and errors.
- Confirm all timestamps are timezone-aware UTC.
- Confirm DB migrations are repeatable and deterministic.

## 9. Observability and Operations
- Verify `/health` reports correct mode/broker/trading flag.
- Verify PM2/systemd process restarts are stable.
- Verify structured logs include correlation identifiers.
- Verify alerting for repeated order failures / broker downtime.
- Verify runbook includes emergency stop:
  - set `MW_TRADING_ENABLED=false`
  - restart middleware

## 10. Live Go/No-Go Gate
- Dry-run test cases pass 100%.
- Sandbox/UAT scenarios pass end-to-end.
- No critical or high-severity open defects.
- Risk owner and operations owner sign-off.
- Explicit change window and rollback plan documented.

## 11. Post-Go-Live Safeguards
- Start with minimum budget/canary symbol set.
- Enable strict order caps for first live window.
- Monitor fills/rejects/latency in real time.
- Conduct first-day reconciliation and incident review.
