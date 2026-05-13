# Binance Spot Execution Plan

Middleware bundan sonra sadece Binance Spot kripto akışına odaklanır.

## Current State

- Broker: `BINANCE_SPOT`
- Default execution: `DRY_RUN`
- Live gate: `MW_TRADING_ENABLED=true` + `MW_BINANCE_LIVE_ENABLED=true`
- Sizing: fixed quote budget in USDT
- State: Decimal base quantity, FIFO tranches
- Filters: Binance `exchangeInfo` rules before submit

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

## Guard Rails

- `MW_ALLOWED_SYMBOLS_CSV` for live allowlist
- `MW_MAX_OPEN_TRANCHES_PER_SYMBOL` optional; unset means no tranche count cap
- `MW_MAX_SYMBOL_EXPOSURE_USDT` optional; unset means balance/filter checks decide
- `MW_MAX_DAILY_LOSS_USDT` optional
- `MW_MAX_ORDERS_PER_DAY` optional
- `MW_REQUIRE_REALTIME_SIGNALS`
- `MW_MAX_SIGNAL_AGE_SECONDS`

## Live Readiness Checklist

1. Testnet API key passes signed account check.
2. Testnet BUY with marketable limit fills.
3. Testnet FIFO SELL fills and closes the tranche.
4. Webhook token rotated after test sharing.
5. Production key has Spot trading only, no withdrawal permission.
6. Production key is IP-whitelisted to the server where possible.
7. First production run uses small quote budget and narrow symbol allowlist.

## Known Follow-Up Work

- Commission-aware remaining quantity reconciliation.
- Partial-fill polling/reconciliation for IOC expirations.
- Optional status endpoint that separates live Binance orders from dry-run history.
