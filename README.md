# Rapot

Python trading bot + FastAPI backend + Next.js dashboard.

## Quick Start

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
  - `pytest tests/ -v`
- Frontend contract checks are included in the Python test suite.

## Security Notes

- `JWT_SECRET_KEY` is required by default.
- Only for local development, insecure fallback can be enabled with:
  - `ALLOW_INSECURE_JWT_SECRET=1`
- CORS origins are controlled by:
  - `CORS_ALLOW_ORIGINS`
  - `CORS_ALLOW_CREDENTIALS`
