# Pine scripts for Binance Spot middleware alerts

Bu klasörde yalnızca Binance Spot middleware webhook payload'u üreten TradingView
Pine scriptleri tutulur.

## Files

- `combo_hunter_binance.pine`
  - `POST /webhooks/tradingview` contract'ına uygun payload üretir.
  - `schemaVersion`, `source`, `symbol`, `ticker`, `signalCode`, `signalText`,
    `side`, `price`, `timeframe`, `barTime`, `barIndex`, `isRealtime` gönderir.
  - Quantity, API key, secret veya broker token göndermez.

## TradingView Setup

```text
TradingView alert
-> POST /webhooks/tradingview?token=<MW_WEBHOOK_AUTH_TOKEN>
-> middleware validation, idempotency, risk
-> Binance Spot adapter
```

Use Spot symbols on TradingView, for example `BINANCE:BTCUSDT`, not futures or
perpetual contracts.

## Binance Fixed-USDT And FIFO Rule

- `BUY`: middleware spends signal-based USDT budget from
  `MW_BINANCE_BUY_QUOTE_AMOUNT_USDT * multiplier(signalCode)`.
- Default buy budget is `10 USDT` because default multipliers are `1.00`.
- Every distinct `BUY` alert opens a new tranche for the same symbol.
- `SELL`: middleware sells the oldest open tranche first.
- Binance filters (`PRICE_FILTER`, `LOT_SIZE`, `MIN_NOTIONAL`/`NOTIONAL`) are
  applied in middleware before submit.
- API keys stay in environment variables or a secret store.
