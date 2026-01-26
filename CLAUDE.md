# CLAUDE.md - Rapot Codebase Guide

This document provides comprehensive guidance for AI assistants working with the Rapot codebase.

## Project Overview

**Rapot** is an autonomous financial analysis and trading bot platform that operates 24/7. It combines:
- Real-time market scanning for BIST (Istanbul Stock Exchange) and cryptocurrency markets
- AI-powered technical analysis using Google Gemini
- Professional web dashboard with TradingView-quality charts
- Telegram bot notifications for trading signals

**Primary Language:** Turkish (bilingual UI)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    RAPOT PLATFORM                       │
├─────────────────────────────────────────────────────────┤
│  FRONTEND (Next.js 14)          BACKEND (Python)       │
│  ├─ Dashboard UI                ├─ FastAPI REST API    │
│  ├─ TradingView Charts          ├─ Market Scanner      │
│  ├─ Signal Management           ├─ Signal Calculator   │
│  └─ WebSocket Client            ├─ AI Analyst (Gemini) │
│                                 ├─ Telegram Bot        │
│                                 └─ Health Monitoring   │
│                                                         │
│  DATABASE: SQLite (trading_bot.db)                     │
│  DEPLOYMENT: Docker + docker-compose                   │
└─────────────────────────────────────────────────────────┘
```

## Directory Structure

```
/Rapot
├── frontend/                   # Next.js 14 Dashboard
│   ├── src/
│   │   ├── app/               # App Router pages
│   │   │   ├── dashboard/     # Main analytics dashboard
│   │   │   ├── signals/       # Signal management
│   │   │   ├── trades/        # Trade history
│   │   │   ├── scanner/       # Market scanner status
│   │   │   ├── health/        # Bot health monitoring
│   │   │   ├── settings/      # Configuration
│   │   │   └── chart/         # TradingView charts
│   │   ├── components/        # React components
│   │   │   ├── dashboard/     # Dashboard widgets
│   │   │   ├── charts/        # Chart components
│   │   │   ├── layout/        # Header, Sidebar, Nav
│   │   │   └── ui/            # Base Shadcn/UI components
│   │   ├── lib/
│   │   │   ├── api/           # API client functions
│   │   │   ├── hooks/         # Custom React hooks
│   │   │   └── stores/        # Zustand state stores
│   │   └── types/             # TypeScript definitions
│   └── package.json
│
├── api/                        # FastAPI Backend
│   ├── main.py                # REST endpoints
│   ├── auth.py                # JWT authentication
│   └── calendar_service.py    # Economic calendar
│
├── # Python Backend Modules (root level)
│   ├── main.py                # Bot entry point
│   ├── scheduler.py           # Task scheduling
│   ├── market_scanner.py      # Market scanning engine
│   ├── signals.py             # Signal calculation (COMBO/HUNTER)
│   ├── data_loader.py         # Historical data fetching
│   ├── ai_analyst.py          # Gemini AI integration
│   ├── database.py            # Database operations
│   ├── models.py              # SQLAlchemy ORM models
│   ├── config.py              # Trading configuration
│   ├── settings.py            # Environment settings (Pydantic)
│   ├── telegram_notify.py     # Telegram notifications
│   └── backtesting_system.py  # Backtest engine
│
├── tests/                      # Test suite
│   ├── conftest.py            # pytest configuration
│   ├── test_config.py
│   ├── test_market_scanner.py
│   └── test_signals.py
│
├── data/                       # Data files
│   └── bist_symbols.json      # BIST market symbols
│
├── docker-compose.yml          # Container orchestration
├── Dockerfile                  # Python container
├── requirements.txt            # Python dependencies
└── pyproject.toml              # Python project config
```

## Tech Stack

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| Next.js | 16.1.4 | React framework (App Router) |
| React | 19.2.3 | UI library |
| TypeScript | 5 | Type safety |
| Tailwind CSS | v4 | Styling |
| TradingView Charts | 5.1.0 | Professional candlestick charts |
| Recharts | 3.7.0 | Secondary analytics |
| Zustand | 5.0.10 | State management |
| React Query | 5.90.19 | Server state |
| Shadcn/UI | - | Component library |

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.10+ | Language |
| FastAPI | 0.109.0 | REST API framework |
| SQLAlchemy | 2.0.0 | ORM |
| Pydantic | 2.5.0+ | Validation & settings |
| google-generativeai | 0.3.0+ | AI analysis |
| python-telegram-bot | 20.0+ | Notifications |
| python-binance | 1.0.0 | Crypto data |
| isyatirimhisse | 1.2.0+ | BIST data |
| ta | 0.10.0+ | Technical analysis |
| pandas | 2.0.0+ | Data processing |

## Development Commands

### Frontend
```bash
cd frontend
npm run dev          # Development server on :3000
npm run build        # Production build
npm run start        # Production server
npm run lint         # ESLint check
```

### Backend
```bash
# Run the trading bot
python main.py              # Sync mode
python main.py --async      # Async mode

# Run API server
uvicorn api.main:app --reload --port 8000

# Run tests
pytest                      # All tests
pytest -v                   # Verbose
pytest tests/test_signals.py  # Specific file
```

### Code Quality
```bash
ruff check .               # Lint check
ruff format .              # Auto-format
pre-commit run --all-files # All pre-commit hooks
```

### Docker
```bash
docker-compose up -d       # Start all services
docker-compose logs -f api # View API logs
docker-compose down        # Stop services
```

## Code Style Conventions

### Python
- **Line length:** 100 characters
- **Formatter/Linter:** Ruff
- **Quote style:** Double quotes
- **Import order:** Standard library, third-party, local (isort managed)
- **Type hints:** Required for function signatures
- **Docstrings:** Use triple double-quotes, describe in Turkish or English

### TypeScript/React
- **Components:** Functional components with hooks
- **State:** Zustand for client state, React Query for server state
- **Styling:** Tailwind utility classes
- **File naming:** kebab-case for files, PascalCase for components

## Database Models

The SQLite database (`trading_bot.db`) contains these tables:

### Signal
Trading signals generated by the bot
- `symbol`, `market_type` (BIST/Kripto), `strategy` (COMBO/HUNTER)
- `signal_type` (AL/SAT), `timeframe`, `score`, `price`, `details` (JSON)

### Trade
Executed trades
- `symbol`, `market_type`, `direction` (BUY/SELL)
- `price`, `quantity`, `pnl`, `status` (OPEN/CLOSED/CANCELLED)

### ScanHistory
Market scanning records
- `scan_type`, `mode`, `symbols_scanned`, `signals_found`, `duration_seconds`

### BotStat
Key-value configuration store
- `stat_name`, `stat_value`, `updated_at`

### AIAnalysis
AI-generated analysis records
- `signal_id`, `symbol`, `analysis_text`, `technical_data` (JSON)

## Trading Strategies

### COMBO Strategy
Multi-indicator momentum detection:
- **Buy conditions:** MACD < 0, RSI < 40, Williams %R < -80
- **Sell conditions:** MACD > 0, RSI > 80, Williams %R > -10
- Score format: "+4/-0" (4 buy indicators, 0 sell indicators)

### HUNTER Strategy
Peak/valley detection with RSI confirmation:
- Detects 7-day/10-day dip/top patterns
- RSI confirmation (DIP < 30, TOP > 70)
- Score format: "7/7" (days in pattern, days required)

## API Endpoints

**Base URL:** `http://localhost:8000`

Key endpoints:
```
GET  /signals              # List signals (filterable)
GET  /signals/{id}         # Signal details
GET  /trades               # Trade history
GET  /stats                # Portfolio statistics
GET  /symbols/bist         # BIST symbols
GET  /symbols/crypto       # Crypto symbols
GET  /candles/{symbol}     # OHLCV data
GET  /market/ticker        # Live ticker
GET  /market/analysis      # AI analysis
POST /analyze/{symbol}     # Trigger analysis
GET  /health               # Health check
```

## Environment Variables

Required in `.env`:
```bash
# Telegram (Required)
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Binance (Optional - for crypto)
BINANCE_API_KEY=your_key
BINANCE_SECRET_KEY=your_secret

# AI (Optional)
GEMINI_API_KEY=your_gemini_key

# Database
DATABASE_PATH=trading_bot.db
```

## Configuration

Central configuration is in `config.py` using frozen dataclasses:
- `RateLimits`: API rate limiting
- `ScanSettings`: Scanning intervals
- `ComboThresholds`: COMBO strategy parameters
- `HunterThresholds`: HUNTER strategy parameters
- `BacktestSettings`: Backtesting configuration

Runtime settings use Pydantic in `settings.py`.

## Testing

Tests are in the `tests/` directory:
- `conftest.py`: pytest fixtures
- `test_config.py`: Configuration tests
- `test_market_scanner.py`: Scanner tests
- `test_signals.py`: Signal calculation tests

Run with: `pytest -v`

## Docker Services

Three services in `docker-compose.yml`:
1. **api** (port 8000): FastAPI backend
2. **dashboard** (port 8501): Legacy Streamlit (being replaced by Next.js)
3. **bot**: Market scanner and signal generator

## Important Conventions

1. **Turkish terminology in code:**
   - AL = BUY, SAT = SELL
   - Günlük = Daily, Haftalık = Weekly
   - BIST = Istanbul Stock Exchange, Kripto = Cryptocurrency

2. **Signal scores:**
   - COMBO: "+X/-Y" format (X buy indicators, Y sell indicators)
   - HUNTER: "X/Y" format (X days in pattern, Y days required)

3. **Timeframes:**
   - `1D` = Daily
   - `W-FRI` = Weekly (Friday close)
   - `2W-FRI`, `3W-FRI` = Bi/tri-weekly
   - `ME` = Monthly

4. **Color scheme (dark theme):**
   - Background: `#0e1117`
   - Cards: `#161b22`
   - Bullish (Long): `#00c853`
   - Bearish (Short): `#ff3d00`

## Common Tasks

### Adding a new signal type
1. Add strategy logic in `signals.py`
2. Update `ComboThresholds` or `HunterThresholds` in `config.py`
3. Add corresponding UI in `frontend/src/components/dashboard/`

### Adding a new API endpoint
1. Add route in `api/main.py`
2. Add corresponding hook in `frontend/src/lib/hooks/`
3. Update types in `frontend/src/types/`

### Adding a new dashboard widget
1. Create component in `frontend/src/components/dashboard/`
2. Add data hook in `frontend/src/lib/hooks/`
3. Import and place in dashboard page

## Debugging

- API logs: `docker-compose logs -f api`
- Bot logs: `docker-compose logs -f bot`
- Frontend: Browser DevTools + React DevTools
- Health check: `http://localhost:5000/health`
