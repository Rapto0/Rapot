# Rapot

Python trading bot + FastAPI backend + Next.js dashboard.

## Quick Start

Install the selected Python 3.12 / Node 20.20.2 / npm 10.9.9 development environment first:
[installation and offline test commands](docs/RAPOT_DEVAM_PLANI.md#geliştirme-ortamı-ve-komutlar).

1. Copy environment template:
   - `cp .env.example .env`
2. Set required secrets in `.env`:
   - `JWT_SECRET_KEY`
   - `ADMIN_PASSWORD`
   - `USER_PASSWORD`
   - `FINNHUB_API_KEY` (for economic calendar)
3. Run services:
   - API: `uvicorn api.main:app --reload --port 8000`
   - Bot: `python main.py`
   - Frontend: `cd frontend && npm run dev`

## Docker

Run all services:

```bash
docker compose up --build
```

Frontend uses `/api` as public base path, and Next.js rewrites proxy requests to `API_PROXY_TARGET`.

## Tests

- Python tests:
  - `.venv/Scripts/python.exe -m pytest` (Windows)
  - `.venv/bin/python -m pytest` (Linux/macOS)
- The default command includes `tests/` and `middleware/tests/` with temporary databases,
  synthetic settings and external network access blocked. It does not need a `.env` file.
- Frontend contract checks are included in the Python test suite.
- See the [continuation plan](docs/RAPOT_DEVAM_PLANI.md) for known failures and frontend checks.

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

- Existing dashboard reads and stored analyses remain public. This change does not make
  the entire dashboard private. Server exposure and proxy configuration still need verification.
- The dashboard stores tokens only in tab memory. Reload, expiry, or logout ends the session;
  account changes clear query caches and private component state. No middleware admin key
  belongs in a frontend environment variable.
- Middleware management uses a separate `MW_ADMIN_AUTH_TOKEN` through `X-Admin-Token`;
  see its [access policy](middleware/README.md#management-authentication).
- `JWT_SECRET_KEY` is required by default.
- Only for local development, insecure fallback can be enabled with:
  - `ALLOW_INSECURE_JWT_SECRET=1`
- CORS origins are controlled by:
  - `CORS_ALLOW_ORIGINS`
  - `CORS_ALLOW_CREDENTIALS`
