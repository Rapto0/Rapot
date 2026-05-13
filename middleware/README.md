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
- `MW_TRADING_ENABLED`
- `MW_BROKER_NAME=BINANCE_SPOT`
- `MW_WEBHOOK_AUTH_TOKEN`
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

## Live Gate

Live Binance execution requires:

```bash
MW_EXECUTION_MODE=LIVE
MW_TRADING_ENABLED=true
MW_BINANCE_LIVE_ENABLED=true
MW_BINANCE_BASE_URL=https://api.binance.com
MW_BINANCE_API_KEY=...
MW_BINANCE_SECRET_KEY=...
```

Start live with a small quote budget and a narrow `MW_ALLOWED_SYMBOLS_CSV`.
