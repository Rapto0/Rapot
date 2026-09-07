# Rapot Trading Middleware

TradingView webhook sinyallerini Binance Spot emirlerine çeviren kripto odaklı FastAPI middleware.

## Scope

- Market: Binance Spot crypto only.
- Quote asset: default `USDT`.
- Buy signals: `H_BLS`, `H_UCZ`, `C_BLS`, `C_UCZ`.
- Sell signals: `H_PAH`, `C_PAH`.
- Buy sizing: signal-based USDT quote budget, default `10 USDT`.
- Sell sizing: FIFO, oldest open tranche `remaining_quantity`.
- Position stacking: every distinct BUY signal opens a new tranche while Binance balance allows.
- Default mode: `DRY_RUN` + `BINANCE_SPOT`.

## Flow

1. TradingView sends normalized JSON to `POST /webhooks/tradingview`.
2. Middleware validates schema, token, signal/side mapping, idempotency, temporal guards.
3. Binance `exchangeInfo` filters are loaded for the symbol.
4. BUY quantity is floored to `LOT_SIZE.stepSize`.
5. Limit price is rounded to `PRICE_FILTER.tickSize`.
6. Risk checks run before submit.
7. Binance adapter submits `LIMIT IOC` orders in live mode.
8. Filled BUY opens a tranche; filled SELL closes the oldest tranche FIFO.
9. Inventory, risk totals, and FIFO are restricted to the active execution/account scope.
10. Admin reconciliation compares only that scope with its Binance account balance.

## TradingView Contract

```json
{
  "schemaVersion": 1,
  "source": "Combo+Hunter",
  "symbol": "BTCUSDT",
  "ticker": "BTCUSDT",
  "signalCode": "H_BLS",
  "signalText": "Hunter Beles",
  "side": "BUY",
  "price": 78241.2,
  "timeframe": "1H",
  "barTime": 1713772800000,
  "barIndex": 12345,
  "isRealtime": true
}
```

Rules:
- Extra fields are rejected.
- `symbol` and `ticker` must match.
- `source` must be `Combo+Hunter`.
- `signalCode` must match canonical side.
- TradingView auth uses `?token=<MW_WEBHOOK_AUTH_TOKEN>`.

## Sizing

BUY:
- `quoteBudget = MW_BINANCE_BUY_QUOTE_AMOUNT_USDT * multiplier(signalCode)`
- Default `MW_BINANCE_BUY_QUOTE_AMOUNT_USDT=10`; default multipliers are `1.00`.
- `buyLimitPrice = round_up_to_tick(price * (1 + MW_BUY_BPS / 10000))`
- `quantity = floor_to_step(quoteBudget / buyLimitPrice)`

SELL:
- Select oldest open tranche for symbol.
- `sellLimitPrice = round_down_to_tick(price * (1 - MW_SELL_BPS / 10000))`
- `quantity = floor_to_step(tranche.remaining_quantity)`
- Each SELL closes one oldest tranche; repeated SELL signals continue through FIFO stack.

Binance filters enforced:
- `PRICE_FILTER`
- `LOT_SIZE`
- `MIN_NOTIONAL`
- `NOTIONAL`

## Environment

See `middleware/.env.example`.

Important variables:
- `MW_DATABASE_URL`
- `MW_EXECUTION_MODE` (`DRY_RUN` or `LIVE`)
- `MW_INVENTORY_ACCOUNT_ID` (non-secret stable account label; required in `LIVE`)
- `MW_TRADING_ENABLED`
- `MW_BROKER_NAME=BINANCE_SPOT`
- `MW_WEBHOOK_AUTH_TOKEN`
- `MW_ADMIN_AUTH_TOKEN` (separate management secret, required for private reads/admin operations)
- `MW_ALLOW_ADMIN_ENDPOINTS` (enables replay/reconciliation, not authentication)
- `MW_BINANCE_BASE_URL`
- `MW_BINANCE_API_KEY`
- `MW_BINANCE_SECRET_KEY`
- `MW_BINANCE_BUY_QUOTE_AMOUNT_USDT`
- `MW_ALLOWED_SYMBOLS_CSV`
- Optional guards: `MW_MAX_SYMBOL_EXPOSURE_USDT`, `MW_MAX_DAILY_LOSS_USDT`,
  `MW_MAX_ORDERS_PER_DAY`, `MW_MAX_OPEN_TRANCHES_PER_SYMBOL`

## Local Commands

```bash
pip install -r requirements.txt
alembic -c middleware/infra/alembic.ini upgrade head
uvicorn middleware.api.main:app --reload --port 8010
```

## Endpoints

- `POST /webhooks/tradingview`
- `GET /health`
- `GET /positions`
- `GET /positions/{symbol}`
- `GET /orders`
- `GET /signals`
- `POST /admin/replay-signal`
- `GET /admin/reconcile/{symbol}`

## Management Authentication

Send `X-Admin-Token: <MW_ADMIN_AUTH_TOKEN>` on `/orders`, `/positions`,
`/positions/{symbol}`, `/signals`, and every `/admin/*` request. Query-string tokens
and `X-Webhook-Token` do not grant management access. Configure a strong independent
secret on the server; never put it in Pine alerts or dashboard public variables.

Missing/incorrect request credentials return `401`. An unset admin secret, or one
equal to `MW_WEBHOOK_AUTH_TOKEN`, returns `503` and prevents service/broker creation.
`MW_ALLOW_ADMIN_ENDPOINTS=false` returns `403` on replay/reconciliation even with a
valid key. Private reads require the key regardless of that feature flag.
Disabling webhook authentication does not disable management authentication.

Replay requires both the enabled flag and the admin key. Its default
`bypass_idempotency=false` preserves duplicate suppression. An authenticated admin
can explicitly set `bypass_idempotency=true` to process the payload again; this can
create another order under the configured execution mode and trading gates.

`GET /health` remains public. TradingView keeps its separate webhook credential
(`X-Webhook-Token` or the existing `?token=` fallback).

## Reconciliation

`GET /admin/reconcile/BTCUSDT` checks whether middleware open tranche quantity
matches the Binance account balance for the base asset.

The response includes:
- Middleware open tranche quantity.
- Binance `free`, `locked`, and total base asset balance.
- `total_delta_quantity` and `free_delta_quantity`.
- `status`: `OK`, `MISMATCH`, or `LOCKED_BALANCE`.

`OK` means Binance total base balance is within the symbol step-size tolerance
and free balance is enough to sell the tracked open tranches.

## Inventory Scope and Migration

Every order and tranche carries an `inventory_scope` built from execution mode,
broker, environment/venue, and a stable account label:

- DRY run: `DRY_RUN|BINANCE_SPOT|<MW_APP_ENV>|<account-or-simulation-default>`
- Live: `LIVE|BINANCE_SPOT|<MW_BINANCE_BASE_URL-host>|<MW_INVENTORY_ACCOUNT_ID>`

`MW_INVENTORY_ACCOUNT_ID` is a label such as `testnet-primary` or `prod-primary`,
not an API key or Binance secret. It must remain stable for one account and differ
between accounts. Testnet and production also remain separate because their API hosts
are part of the scope. Changing any scope component intentionally presents an empty,
independent inventory until returning to the original values.

FIFO selection, open-position/exposure limits, daily order/loss totals, order and
position listings, and reconciliation all use the same scope. Signal history remains
a global webhook audit; signal idempotency is evaluated independently per scope.

Before running code with this schema against an existing middleware database:

```bash
alembic -c middleware/infra/alembic.ini upgrade head
```

Migration `20260907_0004` cannot prove the account and venue of historical rows, so it
marks them `LEGACY_UNCLASSIFIED`. These rows remain stored but are excluded from every
active scope. Classify them only after matching orders and tranches to verified broker
history; update both tables to the exact scope shown by the management responses.
The downgrade removes the new columns and indexes while retaining the historical rows.
The migration has not been applied to the real database in this local change.

## Live Gate

Live Binance execution requires:

```bash
MW_EXECUTION_MODE=LIVE
MW_TRADING_ENABLED=true
MW_BINANCE_LIVE_ENABLED=true
MW_INVENTORY_ACCOUNT_ID=prod-primary
MW_BINANCE_BASE_URL=https://api.binance.com
MW_BINANCE_API_KEY=...
MW_BINANCE_SECRET_KEY=...
```

Start live with a small quote budget and a narrow `MW_ALLOWED_SYMBOLS_CSV`.
