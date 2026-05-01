# Binance Spot execution plan

Goal: use the same TradingView + middleware model for Binance Spot while keeping
Osmanli support intact.

## Scope

- Spot only.
- No futures, margin, leverage, short selling, or cross/isolated margin.
- TradingView emits only signal intent.
- Middleware owns sizing, risk checks, exchange filters, idempotency, order
  journal, and FIFO position state.

## TradingView payload

Use `middleware/pine/combo_hunter_middleware_normalized.pine` for Binance.

The Pine script sends:

```json
{
  "schemaVersion": 1,
  "source": "Combo+Hunter",
  "symbol": "BTCUSDT",
  "ticker": "BTCUSDT",
  "signalCode": "H_BLS",
  "signalText": "Hunter Ucuz",
  "side": "BUY",
  "price": 65000.0,
  "timeframe": "1D",
  "barTime": 1713772800000,
  "barIndex": 12345,
  "isRealtime": true
}
```

Do not include Binance API keys, quantities, or account data in the TradingView
message.

## Runtime topology

Preferred first implementation:

```text
TradingView
-> Binance middleware URL
-> MW_BROKER_NAME=BINANCE_SPOT
-> Binance Spot adapter
```

If Osmanli and Binance must run at the same time, run two middleware instances
with different environment variables and different webhook URLs.

Later alternative: add explicit broker routing inside middleware. Do this only
after the single-broker instance model is stable.

## Fixed USDT buy

For Binance LIMIT buys, fixed USDT budget is converted to base quantity before
submission:

```text
quote_budget = MW_BINANCE_BUY_QUOTE_AMOUNT_USDT * signal_multiplier
limit_price = round_up_to_tick(signal_price * (1 + buy_bps / 10000))
raw_qty = quote_budget / limit_price
quantity = floor_to_step(raw_qty, LOT_SIZE.stepSize)
notional = quantity * limit_price
```

Reject before sending to Binance if:

- `quantity < LOT_SIZE.minQty`
- `quantity > LOT_SIZE.maxQty`
- `notional < MIN_NOTIONAL.minNotional` or `NOTIONAL.minNotional`
- `notional > NOTIONAL.maxNotional`, when present
- quote asset free balance is insufficient
- symbol is not `TRADING`
- symbol is not allowed by middleware allowlist

For MARKET buys, Binance supports `quoteOrderQty`, but the initial middleware
flow should keep LIMIT behavior for parity with the current BIST execution
model.

## FIFO sell

On accepted BUY fills, create or update an open tranche:

```text
symbol=BTCUSDT
entry_price=avg_fill_price
filled_quantity=executedQty
remaining_quantity=executedQty
entry_time=fill_time
open_order_id=<local order id>
```

On SELL signal:

```text
target = oldest open tranche for symbol
limit_price = round_down_to_tick(signal_price * (1 - sell_bps / 10000))
quantity = floor_to_step(target.remaining_quantity, LOT_SIZE.stepSize)
```

Reject if there is no open tranche or if rounded quantity falls below exchange
minimums. Apply fills back to the target tranche until its remaining quantity is
zero, then close it. This preserves first-in-first-out accounting.

## Persistence changes needed

The current BIST middleware stores integer lots. Binance requires decimal base
asset quantities.

Required model change:

- Add decimal order quantity fields, or migrate `requested_lots`, `filled_lots`,
  and tranche quantities to decimal-safe names.
- Keep API compatibility for BIST responses where possible.
- Store quote asset, base asset, exchange order id, client order id, and raw
  Binance status payloads.

## Binance adapter requirements

Minimum adapter methods:

- `get_exchange_info(symbol)`
- `get_account_balances()`
- `submit_limit_order(...)`
- `get_order(symbol, order_id/client_order_id)`
- `cancel_order(...)`

Required Binance endpoints:

- `GET /api/v3/exchangeInfo`
- `GET /api/v3/account`
- `POST /api/v3/order/test`
- `POST /api/v3/order`
- `GET /api/v3/order`

Use Testnet first:

```text
MW_BINANCE_BASE_URL=https://testnet.binance.vision
MW_EXECUTION_MODE=DRY_RUN
MW_TRADING_ENABLED=false
```

Enable live only after Testnet UAT:

```text
MW_BINANCE_BASE_URL=https://api.binance.com
MW_EXECUTION_MODE=LIVE
MW_TRADING_ENABLED=true
MW_BINANCE_LIVE_ENABLED=true
```

## Safety gates

- API key must have trade permission only.
- Withdrawal permission must be disabled.
- Use IP allowlist where possible.
- Keep keys only in environment variables or secret store.
- Start with a small canary USDT amount.
- Keep duplicate signal rate at zero.
- Reconcile order status after timeouts because Binance can return an unknown
  execution state.
