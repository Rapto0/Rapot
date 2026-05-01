# Pine scripts for TradingView middleware alerts

This folder keeps the TradingView-side scripts that emit webhook payloads for the
middleware execution flow.

## Files

- `combo_hunter_middleware_normalized.pine`
  - Broker-neutral script for middleware.
  - Sends the strict `/webhooks/tradingview` payload:
    `schemaVersion`, `source`, `symbol`, `ticker`, `signalCode`, `signalText`,
    `side`, `price`, `timeframe`, `barTime`, `barIndex`, `isRealtime`.
  - Use this for Binance Spot and for any future official Osmanli adapter flow.
  - It does not send `quantity`, `apiKey`, `token`, or broker secrets.

- `combo_hunter_osmanli_wizard_legacy.pine`
  - Copy of the current Osmanli Wizard-style payload.
  - Sends fields such as `orderSide`, `orderType`, `quantity`, `apiKey`, and
    `token`.
  - Keep this only for the existing `/webhooks/tradingview/osmanli-proxy` shadow
    or Wizard-forward flow. Do not use it for Binance.

## Recommended setup

For Binance Spot, use:

```text
TradingView alert
-> POST /webhooks/tradingview?token=<MW_WEBHOOK_AUTH_TOKEN>
-> middleware validation, idempotency, risk
-> Binance Spot adapter
```

For Osmanli Wizard proxy compatibility, use:

```text
TradingView alert
-> POST /webhooks/tradingview/osmanli-proxy?token=<MW_WEBHOOK_AUTH_TOKEN>
-> middleware shadow/risk checks
-> optional Osmanli Wizard forwarding
```

If both Osmanli and Binance run at the same time, prefer two middleware runtime
instances with different broker configuration and different webhook URLs. The
same normalized Pine can be used for both; routing should stay in middleware,
not in Pine.

## Binance fixed-USDT and FIFO rule

Binance fixed-USDT buying must be implemented in middleware settings and risk
logic, not in Pine. Pine only emits `BUY` or `SELL` intent.

Expected Binance behavior:

- `BUY`: middleware spends a fixed USDT budget per accepted signal.
- `SELL`: middleware sells from the oldest open tranche first.
- Binance symbol filters (`PRICE_FILTER`, `LOT_SIZE`, `MIN_NOTIONAL`/`NOTIONAL`)
  must be applied before order submission.
- API keys stay in environment variables or a secret store. Never paste Binance
  keys into TradingView alert messages.

Use Spot symbols on TradingView, for example `BINANCE:BTCUSDT`, not futures or
perpetual contracts.
