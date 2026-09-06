# Synthetic Exposure

Synthetic Exposure maps historical correlations between stocks and crypto assets through an interactive Exposure Graph and a 0–1 Exposure Score. The `$DELTA` utility token gates advanced features: deeper graph analysis, portfolio exposure breakdown, and detailed score history.

---

## Project structure

```
delta/
├── web/              Next.js 16 App Router frontend
├── api/              FastAPI backend (Python 3.12+)
├── docs/             Architecture, methodology, API reference
├── .env.example      Template for web/.env.local and api/.env
└── README.md
```

---

## Local development

### Prerequisites

- Node.js 20+ and npm
- Python 3.12+

### Frontend

```bash
cd web
npm install
cp ../.env.example .env.local   # set NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

```bash
npm run build         # production build
npm run lint          # ESLint
npx tsc --noEmit      # type-check
```

### Backend

```bash
cd api
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env        # edit with DATABASE_URL and API keys
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

With `USE_DEMO_DATA=true` (the default), the API seeds deterministic fixture data on startup — no API keys or external network required.

### Data ingestion

```bash
# Seed or backfill 90 days of price history
python -m app.ingestion.commands backfill

# Refresh current crypto prices (CoinGecko /coins/markets — 1 request for all assets)
python -m app.ingestion.commands refresh-crypto-quotes

# Refresh stock EOD prices (weekdays only)
python -m app.ingestion.commands refresh-stock-eod

# Recompute and store all Exposure Scores
python -m app.ingestion.commands recompute-scores
```

---

## Environment variables

All variables are documented in `.env.example`. Key values:

| Variable | Required for |
|----------|-------------|
| `DATABASE_URL` | Backend (PostgreSQL in production, SQLite by default) |
| `MARKETSTACK_API_KEY` | Stock price data (`USE_DEMO_DATA=false`) |
| `COINGECKO_API_KEY` | Crypto price data (`USE_DEMO_DATA=false`) |
| `COINGECKO_API_TYPE` | `demo` (default) or `pro` |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend → backend URL |
| `NEXT_PUBLIC_REOWN_PROJECT_ID` | Wallet connection (AppKit) |
| `NEXT_PUBLIC_DELTA_TOKEN_ADDRESS` | `$DELTA` token contract address |
| `NEXT_PUBLIC_DELTA_MIN_BALANCE` | Minimum balance for portfolio access (raw units) |
| `NEXT_PUBLIC_DEX_BUY_URL` | Link to buy `$DELTA` |

---

## Deployment

### Frontend (Vercel)

Set `NEXT_PUBLIC_API_BASE_URL` to your backend URL in the Vercel project settings. All other `NEXT_PUBLIC_*` variables must also be set there.

```bash
# Build command
npm run build

# Output directory
.next
```

### Backend (Railway)

```bash
# Build
pip install -r requirements.txt

# Migrate (run once after each deploy)
alembic upgrade head

# Start
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Scheduled refresh via Railway cron:

```bash
# Every hour — crypto quotes
python -m app.ingestion.commands refresh-crypto-quotes

# Daily (weekdays) — stock EOD
python -m app.ingestion.commands refresh-stock-eod

# Daily — recompute scores
python -m app.ingestion.commands recompute-scores
```

Set all secrets in Railway's environment panel. Never commit `.env` files with real values.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS |
| Animation | Framer Motion |
| Graph | @xyflow/react |
| Charts | lightweight-charts v5 (dynamic import) |
| Wallet | Reown AppKit, Wagmi, Viem |
| Backend | Python FastAPI, Pydantic v2 |
| Database | PostgreSQL, SQLAlchemy 2 async, Alembic |
| Providers | CoinGecko (crypto), Marketstack (stocks) |
| Hosting | Railway (API + DB + cron), Vercel (frontend) |

---

## Upcoming features

- Portfolio exposure breakdown (requires `$DELTA` balance)
- Real-time score updates as intraday prices move
- Live price feeds across all 38 assets
- Expanded asset universe (additional chains and equity sectors)
- Real-time alerts on significant score changes

---

## Disclaimer

Synthetic Exposure Scores are for informational purposes only and do not constitute investment advice. See `/methodology` for the full methodology. Synthetic Exposure does not custody assets, operate an exchange, or guarantee equivalent asset performance.
