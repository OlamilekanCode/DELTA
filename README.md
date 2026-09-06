# DELTA — Synthetic Exposure

DELTA maps historical correlations between stocks and crypto assets through an interactive Exposure Graph and a 0–1 Exposure Score. The `$DELTA` utility token gates future advanced features.

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

# Refresh current crypto prices from CoinGecko (1 batch request)
python -m app.ingestion.commands refresh-crypto-quotes

# Refresh 90-day OHLCV history for all crypto assets
python -m app.ingestion.commands refresh-crypto-history

# Refresh stock EOD prices (weekdays only)
python -m app.ingestion.commands refresh-stock-eod

# Recompute and store all Exposure Scores
python -m app.ingestion.commands recompute-scores

# Combined: stock EOD + crypto history + score recomputation
python -m app.ingestion.commands refresh-all
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
| `CRON_SECRET` | Authenticate scheduled job endpoints |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend → backend URL |
| `NEXT_PUBLIC_REOWN_PROJECT_ID` | Wallet connection (AppKit) |
| `NEXT_PUBLIC_DELTA_TOKEN_ADDRESS` | `$DELTA` token contract address |
| `NEXT_PUBLIC_DELTA_MIN_BALANCE` | Minimum balance for portfolio access (raw units) |
| `NEXT_PUBLIC_DEX_BUY_URL` | Link to buy `$DELTA` |

---

## Deployment

### Frontend — Vercel

Set all `NEXT_PUBLIC_*` variables in the Vercel project settings. No build command override needed; the default `npm run build` works.

### Backend — Render

```bash
# Build command
pip install -r requirements.txt

# Pre-deploy / start command (run migrate before starting)
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set all backend secrets in Render's environment panel.

### Database — Neon (PostgreSQL)

Set `DATABASE_URL` to the Neon connection string (use the pooled URL for the API, the direct URL for `alembic upgrade head`).

### Scheduler — Cloudflare Worker + Cron

Cloudflare Cron Triggers cannot set custom HTTP headers directly, so a small Worker (`cloudflare/`) acts as the dispatcher. It receives the cron event and forwards it to the Render API with `X-Cron-Secret`.

```bash
cd cloudflare
npx wrangler secret put API_BASE_URL   # https://your-api.onrender.com
npx wrangler secret put CRON_SECRET    # must match CRON_SECRET on Render
npx wrangler deploy
```

| Schedule (wrangler.toml) | Forwarded to | Purpose |
|--------------------------|--------------|---------|
| `*/5 * * * *` | `POST /api/v1/cron/refresh-crypto-quotes` | Current crypto prices |
| `0 0 * * 2,5` | `POST /api/v1/cron/refresh-history-and-scores` | OHLCV history + score recompute |

Both endpoints share a single advisory lock — they cannot overlap even if both crons fire at the same time.

---

## Asset universe

**8 stocks**: NVDA, TSLA, COIN, MSTR, AMD, MSFT, META, PLTR

**30 crypto assets** across 7 categories: Layer 1, Layer 2, DeFi, Oracle/Data, AI/Compute, Storage, Memecoin. See [docs/methodology.md](docs/methodology.md) for the full list.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS |
| Animation | Framer Motion |
| Graph | @xyflow/react |
| Charts | lightweight-charts v5 |
| Wallet | Reown AppKit, Wagmi, Viem |
| Backend | Python FastAPI, Pydantic v2 |
| Database | PostgreSQL (Neon), SQLAlchemy 2 async, Alembic |
| Providers | CoinGecko (crypto), Marketstack (stocks) |
| Hosting | Render (API), Vercel (frontend), Cloudflare Cron (scheduler) |

---

## Disclaimer

DELTA Exposure Scores are for informational purposes only and do not constitute investment advice. See [/methodology](/methodology) for the full methodology. DELTA does not custody assets, operate an exchange, or guarantee equivalent asset performance.
