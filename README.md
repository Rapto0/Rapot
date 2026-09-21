# Rapot

Rapot scans BIST and crypto markets, records COMBO/HUNTER signals, and presents them
in a Next.js dashboard through a Python/FastAPI backend. Gemini analysis and Telegram
notifications are configurable integrations. A separate Binance Spot middleware
process handles TradingView webhooks and order accounting.

Current priorities, production evidence and deferred acceptance:
[Rapot continuation plan](docs/RAPOT_DEVAM_PLANI.md). Documentation was compared with
the source on **21 September 2026 (repository cleanup)**. Old backlog IDs and unchecked boxes are
historical planning information; use the continuation plan for current work.
The [documentation index](docs/README.md) groups the current technical guides and acceptance records.

## Architecture

| Component | Entry points and data |
|---|---|
| Scanner bot | `main.py` → `scheduler.py` → `market_scanner.py` / `async_scanner.py` |
| Signal engine | `signals.py`, `strategy_inspector.py`, `data_loader.py` |
| Shared scanner handlers | `application/scanner/`, `domain/events/`, `infrastructure/persistence/` |
| Main API | `api/main.py`, `api/routes/` → `application/services/` → `infrastructure/repositories/` |
| Main storage | SQLite via `models.py` / `db_session.py`; legacy `database.py` access remains; separate price cache |
| Signal delivery | API `api/runtime/signal_feed.py` reads committed SQLite rows and broadcasts WS/SSE; clients refresh REST on reconnect |
| Dashboard | `frontend/src/app/`, `frontend/src/lib/api/client.ts`, hooks and components |
| Order middleware | `middleware/api/main.py` → `middleware/services/trading_service.py`; separate PostgreSQL/Alembic schema |

Main dashboard trades/stats and middleware orders/positions are separate datasets.
Browser alarms run while the alarms page is open; they do not provide server-side
24/7 monitoring. The settings page explains configuration scope; browser preferences
are edited in their respective screens. Signal CSV exports include the
currently loaded, filtered rows. See the [frontend guide](docs/FRONTEND.md).

Canonical imports and compatibility decisions are in the
[packaging map](docs/PACKAGING_REFACTOR_MAP.md) and
[wrapper removal policy](docs/WRAPPER_DEPRECATION_SCHEDULE.md). Technical flows and
known limits are described in [the architecture context](docs/ARCHITECTURE.md).

## Signal Scores

- COMBO counts four conditions: MACD, RSI, Williams %R and CCI. `+4/-0` means four
  buy points and zero sell points. Daily/weekly thresholds are BUY 4 / SELL 3;
  the other configured periods use 3 / 3. Unknown-period fallback is 4 / 4.
- HUNTER counts **15 indicator conditions**, not days in a pattern. `DipScore=7/7`
  means seven dip points against a required seven; `ActiveIndicators=X/15` reports
  available indicators separately. Dip thresholds are 7 for daily/weekly/biweekly,
  5 for three-week/monthly, and the top threshold is 10. Missing indicators do not
  lower the threshold; RSI is one of the points, not a separate mandatory gate.
- `signals.py` contains the actual scoring constants; it imports only `MIN_PERIODS`
  from `config.py`. Python, frontend and Pine implementations are not assumed to be
  fully equivalent; the remaining boundary cases are tracked in P3-1.

## Dependencies

Python 3.12 is selected by `.python-version`; `requirements-dev.lock` is the exact
development/CI resolution, while `requirements.txt` contains runtime version ranges
and includes `requirements-security.txt` for reviewed transitive constraints.
JWT authentication uses PyJWT with HS256. Streamlit is no longer a dependency;
the supported dashboard is Next.js. Tests additionally use httpx2 for Starlette's
TestClient; application SDKs still use httpx. Both transports are blocked from
external I/O in the isolated test harness.
The stack includes FastAPI, SQLAlchemy, pandas/NumPy/ta, python-binance,
isyatirimhisse/yfinance, google-genai, python-telegram-bot, Flask, Alembic and psycopg.
Gemini uses `google.genai` first; the old SDK is an optional code fallback.
The locked environment uses the `ta` compatibility accessor in `signals.py`;
installing optional `pandas_ta` can change the calculation path.

Frontend versions come from `frontend/package.json` and its lock: Node 20.20.2,
npm 10.9.9, Next.js 16.3.5, React 19.2.3, TypeScript 5.9.3, Tailwind 4.1.18,
Lightweight Charts 5.1.0, Zustand 5.0.10 and React Query 5.90.19.

## Quick Start

Install the selected Python 3.12 / Node 20.20.2 / npm 10.9.9 development environment first:
[installation and offline test commands](docs/RAPOT_DEVAM_PLANI.md#geliştirme-ortamı-ve-komutlar).

1. Copy environment template:
   - `cp .env.example .env`
2. Set `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` (required settings fields), and a
   `JWT_SECRET_KEY`. Configure `ADMIN_PASSWORD` / `USER_PASSWORD` or their hash
   alternatives for the accounts you want to enable. Use an isolated development
   database path. Tests below need none of these real credentials.
3. Optional integrations: `GEMINI_API_KEY` with `AI_ENABLED`, and `FINNHUB_API_KEY`
   for the economic calendar. Without Finnhub configuration the calendar returns an
   empty result with a warning. Binance public market data does not require enabling
   the middleware's order execution.
4. Run services with the selected virtual environment activated:
   - API: `python -m uvicorn api.main:app --reload --port 8000`
   - Bot: `python main.py` (or `python main.py --async`)
   - Frontend, in `frontend/`: `npm ci`, then `npm run dev`

These startup commands use application settings, databases and external providers.
They are not the isolated test harness. Keep `RUN_EMBEDDED_BOT=0` when the bot runs
as a separate process.

## Docker

The supported production topology uses **Compose 2.24+**, `main-init`, `api`, `bot`
and `frontend`. The optional `middleware` profile adds `postgres`,
`middleware-migrate` and `middleware`. Init/migrate are one-shot jobs; middleware
uses its own database, with DRY_RUN and trading/live disabled in Compose.

Prepare the data directory and configuration using [the deployment guide](docs/DEPLOY.md)
before starting Compose. Main SQLite uses `db_session.init_db()` and compatible
schema additions; middleware uses Alembic migrations and a production revision
check. The legacy `migrate_db.py` script is not a general deployment command.
See [the two database migration policies](docs/DB_MIGRATION_POLICY.md).

Browser HTTP/WebSockets use `/api`, health uses `/health-api`. Next.js rewrites
target `API_PROXY_TARGET` and `HEALTH_PROXY_TARGET`; container builds use `api:8000`
and `bot:5000`. Host Nginx uses explicit `127.0.0.1` upstreams and HTTPS.
`deploy.yml` publishes images; it does not deploy them to the server. A documentation
commit does not change the running application images.

## Tests

- Python tests:
  - `.venv/Scripts/python.exe -m pytest` (Windows)
  - `.venv/bin/python -m pytest` (Linux/macOS)
- The default command includes `tests/` and `middleware/tests/` with temporary databases,
  synthetic settings and external network access blocked. It does not need a `.env` file.
- Some frontend contract checks are included in Python; the Node suite is separate.
  In `frontend/`, after selecting Node/npm and installing the lock, run:

  ```powershell
  npm test
  npm run lint -- --no-cache
  npm run typecheck -- --incremental false
  $env:NEXT_TELEMETRY_DISABLED = '1'
  npm run build
  npm run test:standalone
  ```

- Standalone checks require the build output and use local HTTP/WebSocket mocks.
- `python -m scripts.ci_quality lint` checks all Git-tracked Python files, including
  middleware and tests, with the workspace exclusions in `pyproject.toml`.
- Python security checks use pinned CI-only Bandit/pip-audit tools and publish JSON reports,
  scope manifests and summaries. Findings are explicitly report-only; tool errors,
  invalid reports or incomplete source/package coverage fail CI. This does not scan
  container OS packages or runtime configuration, and green CI is not proof of
  zero security findings. See the [continuation plan](docs/RAPOT_DEVAM_PLANI.md) for
  dated results and follow-up decisions.
- `npm run audit:dependencies` in `frontend` audits all locked production, development,
  optional and peer dependencies. Any finding, tool error, invalid report or lock
  coverage mismatch fails the check. CI preserves the raw npm report, lock hash,
  scope manifest and summary under `security-reports/npm/`. This check contacts the
  public npm registry; `npm test` tests the guard without network access. See the
  [frontend dependency review](docs/FRONTEND_DEPENDENCY_SECURITY.md) for the advisory
  decisions and the two documented npm 10 optional-platform `npm ls` warnings.

## Security Notes

- Dashboard sign-in is available at `/login`. The `admin` and `user` accounts use the
  configured `ADMIN_PASSWORD` / `USER_PASSWORD` (or their `_HASH` equivalents).
  An account without a configured password is unavailable.
- Main API clients obtain a token from `POST /auth/token` and send
  `Authorization: Bearer <token>`. Tokens must have an expiry; disabled users are rejected.
- Access policy (limits are per client IP in the current process):

  | Operation | Access | Limit |
  |---|---|---|
  | `POST /auth/token` | Login credentials | 5/minute |
  | `GET /logs` | Admin JWT; 1–500 rows | 30/minute |
  | `POST /analyze/{symbol}` | Admin JWT | 2/minute |
  | `GET /ops/strategy-inspector` | User/admin JWT | 30/minute |
  | `GET /market/analysis`, `GET /api/market/analysis` | User/admin JWT | Shared 2/minute |

- Existing dashboard reads and stored analyses remain public; the dashboard is not
  entirely private. Production HTTPS/auth/proxy acceptance is recorded in P1-2/P1-6
  of the continuation plan; verify these boundaries again when changing exposure.
- The dashboard stores tokens only in tab memory. Reload, expiry, or logout ends the session;
  account changes clear query caches and private component state. No middleware admin key
  belongs in a frontend environment variable.
- Middleware management uses a separate `MW_ADMIN_AUTH_TOKEN` through `X-Admin-Token`;
  see its [access policy](docs/MIDDLEWARE.md#management-authentication).
- `JWT_SECRET_KEY` is required by default.
- Only for isolated local development, insecure fallback requires all three:
  an empty `JWT_SECRET_KEY`, `APP_ENV=development`, and
  `ALLOW_INSECURE_JWT_SECRET=1`. A nonempty placeholder key is rejected even with
  that flag. Use a strong configured key for normal operation.
- CORS origins are controlled by:
  - `CORS_ALLOW_ORIGINS`
  - `CORS_ALLOW_CREDENTIALS`
