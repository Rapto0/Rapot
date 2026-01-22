# Rapot

Rapot is a Python-based algorithmic trading bot with a Next.js (App Router) admin dashboard in the `frontend/` directory.

## Quick start

### Backend

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python main.py
```

### Frontend

The Next.js app lives in `frontend/`. Run all Node/NPM commands from that folder.

```bash
cd frontend
npm install
npm run dev
```

Then open `http://localhost:3000`.

## Common troubleshooting

- **`npm ERR! ENOENT ... package.json`**
  - You are running `npm install` from the repo root. Run it inside `frontend/` instead.
- **`403` or registry errors**
  - Ensure `npm config get registry` returns `https://registry.npmjs.org/` and retry.

## Repo layout

- `frontend/` — Next.js dashboard UI (dark TradingView-style admin panel)
- `api/`, `main.py`, `scheduler.py`, etc. — Python services for data collection, trading, and APIs
