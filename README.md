# Rapot

Rapot provides BIST and crypto charts, on-demand Borsapy screening, COMBO/HUNTER
indicators, manual Gemini analysis and persistent server alarms through a Next.js
dashboard and Python/FastAPI API. Telegram is optional for alarms explicitly created
on the site. A separate Binance Spot middleware handles TradingView webhooks and
order accounting.

Current priorities, production evidence and deferred acceptance:
[Rapot continuation plan](docs/RAPOT_DEVAM_PLANI.md). Documentation was compared with
the source on **13 October 2026 (indicator and watchlist alarm transition)**. Old backlog
IDs and unchecked boxes are historical planning information; use the continuation plan for current work.
The [documentation index](docs/README.md) groups the current technical guides and acceptance records.

The old scheduled COMBO/HUNTER scanner, Telegram commands and scanner-triggered
news/Gemini messages have been removed from the source. Website indicators,
backtests, `/ai` and opt-in alarm delivery remain supported. The subsequent
[history retirement](docs/INDICATOR_ALARM_TRANSITION_2026-10-12.md) removes the old
scanner archive and its UI/API consumers while preserving indicator calculations.
Source **`8b4e1bab` was deployed at 14:46:08 UTC on 13 October**. The separately
authorized history cleanup committed at **15:01:12 UTC**, and independent acceptance
passed at **15:11:48 UTC**. It removed 2,017,235 old signals, 184 scans and their
automatic analysis/counter remnants. Watchlists, alarm records, financial records
and account connections were preserved against a freshly restored backup. All four
persistent services are healthy. The [history retirement record](docs/INDICATOR_ALARM_TRANSITION_2026-10-12.md)
separates this acceptance from live-market and full-session capacity claims; the
[earlier bot migration](docs/SERVER_ONLY_MIGRATION_2026-10-12.md) is historical.

## Architecture

| Component | Entry points and data |
|---|---|
| On-demand screening | `/scanner` and `/research` → Borsapy research API; no scheduled Telegram scanner |
| Signal engine | `signals.py`, `strategy_inspector.py`, `data_loader.py` |
| Historical signal compatibility | `application/scanner/`, `domain/events/`, `infrastructure/persistence/`; preserved without an automatic bot entry point |
| Main API | `api/main.py`, `api/routes/` → `application/services/` → `infrastructure/repositories/` |
| Main storage | SQLite via `models.py` / `db_session.py`; legacy `database.py` access remains; separate price cache |
| Market delivery | Provider lifecycle in `api/runtime/realtime_bootstrap.py` and authenticated market WS/SSE in `api/realtime.py`; no legacy SQLite signal polling |
| Dashboard | `frontend/src/app/`, `frontend/src/lib/api/client.ts`, hooks and components |
| Order middleware | `middleware/api/main.py` → `middleware/services/trading_service.py`; separate PostgreSQL/Alembic schema |

Main dashboard trades/stats and middleware orders/positions are separate datasets.
The dashboard prioritizes server watchlists and alarms. `/signals` redirects to
`/alarms`; legacy signal/scan REST endpoints return authenticated `410` and are
excluded from OpenAPI. Trades remain readable; `/stats` contains trade metrics.
Interactive Borsapy screening and user-created COMBO/HUNTER alarms remain available.
The `/alarms` page manages 1,000 each of price, technical and watchlist alarms,
including compound conditions and intrabar or confirmed-candle triggers. The API
owns bounded market tracking and evaluation even when the browser is closed;
one-second cycles do not guarantee full-universe latency. Previous daily server
rules remain at `/alarms/legacy`. Legacy `/alarms/local` rules still
run only while that page is open. See the [alarm contract](docs/SERVER_ALARMS.md)
for supported indicators, timeframes and delivery limits. The settings page explains configuration scope; browser preferences
are edited in their respective screens. See the [frontend guide](docs/FRONTEND.md).

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
isyatirimhisse/yfinance, Borsapy, google-genai, cryptography, Alembic and psycopg.
Gemini uses `google.genai` first; the old SDK is an optional code fallback.
The locked environment uses the `ta` compatibility accessor in `signals.py`;
installing optional `pandas_ta` can change the calculation path.

Frontend versions come from `frontend/package.json` and its lock: Node 20.20.2,
npm 10.9.9, Next.js 16.3.8, React 19.2.3, TypeScript 5.9.3, Tailwind 4.1.18,
Lightweight Charts 5.1.0, Zustand 5.0.10 and React Query 5.90.19.

## Quick Start

Install the selected Python 3.12 / Node 20.20.2 / npm 10.9.9 development environment first:
[installation and offline test commands](docs/RAPOT_DEVAM_PLANI.md#geliştirme-ortamı-ve-komutlar).

1. Copy environment template:
   - `cp .env.example .env`
2. Set a strong `JWT_SECRET_KEY`. Configure `ADMIN_PASSWORD` / `USER_PASSWORD` or their hash
   alternatives for the accounts you want to enable. Use an isolated development
   database path. `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` may remain empty; set both
   only if you want Telegram delivery for explicitly enabled website alarms.
   Tests below need none of these real credentials.
3. Optional AI uses `GEMINI_API_KEY` with `AI_ENABLED`. BIST charts and the default
   BIST history/daily-alarm source use the server-side Borsapy/TradingView connection
   configured by an admin in `/research`. `BORSAPY_USE_FOR_BIST` defaults to true;
   false explicitly selects legacy history/daily-alarm providers. Provider or account
   failure never silently selects a different BIST source. The economic calendar
   uses public Borsapy/Doviz.com data without Finnhub or TradingView credentials.
   Binance market data preserves its exchange identity and does not require enabling
   the middleware's order execution.
4. Run services with the selected virtual environment activated:
   - API: `python -m uvicorn api.main:app --reload --port 8000`
   - Frontend, in `frontend/`: `npm ci`, then `npm run dev`

These startup commands use application settings, databases and external providers.
They are not the isolated test harness. The API owns server alarm evaluation and
delivery; no separate or embedded bot process is required.

## Docker

The supported production topology uses **Compose 2.24+**, `main-init`, `api`
and `frontend`. With the middleware profile, the four persistent services are
API, frontend, middleware and PostgreSQL. `main-init` and `middleware-migrate`
are one-shot jobs. Middleware uses its own database, with DRY_RUN and trading/live
disabled in Compose.

Prepare the data directory and configuration using [the deployment guide](docs/DEPLOY.md)
before starting Compose. Main SQLite uses `db_session.init_db()` and compatible
schema additions; middleware uses Alembic migrations and a production revision
check. The legacy `migrate_db.py` script is not a general deployment command.
See [the two database migration policies](docs/DB_MIGRATION_POLICY.md).

Browser HTTP/WebSockets use `/api`; health uses `/api/health` and authenticated
alarm runtime status. Next.js rewrites target `API_PROXY_TARGET`; container builds
use `http://api:8000`. The former Flask port 5000 and `/health-api` proxy are removed.
Host Nginx uses explicit `127.0.0.1` upstreams and HTTPS.
`deploy.yml` publishes images; it does not deploy them to the server. A documentation
commit does not change the running application images.
This architecture/dependency change requires normal clean backend and frontend
builds. The historical additive/source-only image paths do not satisfy its build
input guards; those guards must not be bypassed.

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
  | `GET /ops/strategy-inspector` | Admin JWT | 30/minute |
  | `GET /market/analysis`, `GET /api/market/analysis` | Admin JWT | Shared 2/minute |
  | `/borsapy/*` research, saved inputs and provider connections | Admin JWT; private, no-store | Query 20/minute; candles 30/minute; stream 120/minute |
  | Other personal dashboard HTTP reads and actions | Admin JWT; private, no-store | Route-specific |
  | Backend WebSocket / SSE data | Admin JWT; rechecked during delivery | WS auth within 5 seconds |

- The private `/research` workspace exposes the reviewed borsapy feature catalog;
  `/chart`, dashboard quotes and watchlists use authenticated BIST TradingView data
  through Borsapy. Provider credentials
  are encrypted on the server and are never returned to the browser. See the
  [integration contract](docs/BORSAPY_INTEGRATION.md) for feature coverage and pending
  live-market acceptance.

- Main API HTTP access defaults to admin-only, including stored analyses and market
  data. Only `/`, `/health`, `/auth/token`, `/auth/me`, `/docs`, `/redoc` and
  `/openapi.json` bypass that global boundary; `/auth/me` still validates its JWT.
  CORS preflight is allowed without exposing data. Private responses, including
  errors, use `Cache-Control: private, no-store`.
- WebSockets require the first message `{ "type": "auth", "token": "<JWT>" }`;
  clients wait for `authenticated` before subscribing. SSE uses the Bearer header.
  Tokens never belong in URLs. Expiry or revoked access stops private delivery;
  WebSocket close codes 4401/4403 stop automatic reconnects and clear private data.
- The old Flask bot surface and Telegram-only `POST /analyze/{symbol}` endpoint
  are removed. Manual site AI continues through `/market/analysis`; alarm status
  and delivery remain behind the API's admin boundary.
- Dated HTTP/Flask and bot rollout records describe earlier deployments. See the
  continuation plan for current component identities and acceptance limits.
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
