# Binance Spot Execution Plan

Middleware bundan sonra sadece Binance Spot kripto akışına odaklanır.

## Current State

- Broker: `BINANCE_SPOT`
- Default execution: `DRY_RUN`
- Live gate: `MW_TRADING_ENABLED=true` + `MW_BINANCE_LIVE_ENABLED=true`
- Sizing: fixed quote budget in USDT
- State: Decimal base quantity, FIFO tranches
- Inventory scope: execution mode + broker + venue/environment + stable account label
- Filters: Binance `exchangeInfo` rules before submit
- Recovery: deterministic client order ID + cumulative fill snapshots

## Order Rules

BUY:
- Quote budget: `MW_BINANCE_BUY_QUOTE_AMOUNT_USDT * signalMultiplier`
- Default quote budget is `10 USDT`; default signal multipliers are `1.00`
- Limit price: signal price plus `MW_BUY_BPS`, rounded up to tick size
- Quantity: quote budget divided by limit price, floored to step size
- Every distinct BUY alert opens a new tranche for the same symbol

SELL:
- Select oldest open tranche for the symbol
- Limit price: signal price minus `MW_SELL_BPS`, rounded down to tick size
- Quantity: tranche remaining quantity, floored to step size
- Every SELL alert closes one oldest tranche, then the next SELL closes the next tranche

BROKER RESULT:
- Store the deterministic client order ID before submitting the order
- Treat `executedQty` as cumulative and apply only the quantity above the stored total
- Apply partial fills even when the final status is `CANCELED` or `EXPIRED`
- On an ambiguous submit result, query by client order ID and keep unresolved orders `unknown`
- Repeat recovery through authenticated `POST /admin/recover-order/{order_id}`

## Guard Rails

- `MW_ALLOWED_SYMBOLS_CSV` for live allowlist
- `MW_MAX_OPEN_TRANCHES_PER_SYMBOL` optional; unset means no tranche count cap
- `MW_MAX_SYMBOL_EXPOSURE_USDT` optional; unset means balance/filter checks decide
- `MW_MAX_DAILY_LOSS_USDT` optional
- `MW_MAX_ORDERS_PER_DAY` optional
- `MW_REQUIRE_REALTIME_SIGNALS`
- `MW_MAX_SIGNAL_AGE_SECONDS`

## Live Readiness Checklist

1. Database migration head, currently `20260907_0005`, is applied before the new application starts.
2. A stable, non-secret `MW_INVENTORY_ACCOUNT_ID` identifies this exact account.
3. Testnet API key passes signed account check.
4. Testnet BUY with marketable limit fills.
5. Testnet FIFO SELL fills and closes the tranche.
6. A deliberately ambiguous testnet response is found by client order ID without resubmitting.
7. `GET /admin/reconcile/{symbol}` reports the expected testnet scope and `OK`.
8. Production uses a different account label and production API host.
9. Webhook token is rotated after test sharing.
10. Production key has Spot trading only, no withdrawal permission.
11. Production key is IP-whitelisted to the server where possible.
12. First production run uses small quote budget and narrow symbol allowlist.

## Known Follow-Up Work

- Commission-aware automatic state repair.
- Automated polling for orders that remain `unknown` or non-terminal.
- Optional status endpoint that separates live Binance orders from dry-run history.
