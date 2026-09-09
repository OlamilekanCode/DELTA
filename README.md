# Synthetic Exposure

Maps stock ↔ crypto correlation through an interactive Exposure Graph, historical (90-day) and live (30-minute) signed Exposure Scores (`−1.00` to `+1.00`), and portfolio exposure analysis. The `$SynthEx` utility token gates an expanded asset universe and portfolio features.

---

## Project structure

```
synthetic-exposure/
├── web/              Next.js 16 App Router frontend
├── api/              FastAPI backend (Python 3.12+)
├── cloudflare/       Cron dispatcher Worker
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
python -m app.ingestion.commands backfill              # seed/backfill 90 days of history
python -m app.ingestion.commands refresh-crypto-quotes  # 1 batch CoinGecko request, all crypto
python -m app.ingestion.commands refresh-crypto-history
python -m app.ingestion.commands refresh-stock-eod       # weekdays only
python -m app.ingestion.commands refresh-intraday        # batched Marketstack + stored crypto observations
python -m app.ingestion.commands recompute-scores
python -m app.ingestion.commands refresh-all             # stock EOD + crypto history + scores + cleanup
python -m app.ingestion.commands cleanup-old-data
```

---

## Environment variables

Full reference in `.env.example`. Highlights:

| Variable | Required for |
|----------|-------------|
| `DATABASE_URL` | Backend (PostgreSQL in production, SQLite by default) |
| `MARKETSTACK_API_KEY` / `COINGECKO_API_KEY` | Live price data (`USE_DEMO_DATA=false`) |
| `SESSION_SECRET` | HMAC-signs stored session-token hashes — required strong (32+ chars) in production |
| `SIWE_ALLOWED_DOMAINS` / `SIWE_ALLOWED_URIS` | SIWE identity policy — defaults to `CORS_ORIGINS` if unset |
| `SYNTHEX_CHAIN_ID`, `SYNTHEX_TOKEN_ADDRESS`, `ROBINHOOD_RPC_URL` | On-chain holder verification (fails closed until all are set) |
| `SYNTHEX_DEX_ROUTER_ADDRESSES`, `SYNTHEX_DEX_POOL_ADDRESSES`, `SYNTHEX_WETH_ADDRESS` | `$SynthEx`/ETH purchase verification (fails closed until all are set) |
| `CRON_SECRET` | Authenticate scheduled job endpoints |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend → backend URL for public data (browser-fetched) |
| `BACKEND_API_URL` | Server-only Vercel var → FastAPI origin (BFF pattern, never `NEXT_PUBLIC_`) |
| `NEXT_PUBLIC_REOWN_PROJECT_ID` | Wallet connection (AppKit) |
| `NEXT_PUBLIC_SYNTHEX_CHAIN_ID` / `NEXT_PUBLIC_SYNTHEX_RPC_URL` | Wallet-facing chain prompts (display only — never authoritative for access) |
| `NEXT_PUBLIC_SYNTHEX_TOKEN_ADDRESS` / `NEXT_PUBLIC_SYNTHEX_BUY_URL` | `$SynthEx` display + buy link |

---

## Deployment

### Frontend — Vercel

Set all `NEXT_PUBLIC_*` variables and `BACKEND_API_URL` (server-only) in the Vercel project settings. Default `npm run build`.

### Backend — Render

```bash
pip install -r requirements.txt                                    # build
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT   # start
```

Database is Render PostgreSQL. Schema changes are Alembic-only in production — the app never runs `create_all()` against Postgres. Never run `alembic downgrade` or migration testing against the production database — verify migrations against a disposable local/staging database only.

### Scheduler — Cloudflare Worker + Cron

```bash
cd cloudflare
npx wrangler secret put API_BASE_URL
npx wrangler secret put CRON_SECRET
npx wrangler deploy
```

| Schedule | Forwarded to | Purpose |
|----------|--------------|---------|
| `*/5 * * * *` | `POST /api/v1/cron/refresh-crypto-quotes` | Current crypto prices + 5-min observations |
| `2,32 * * * *` | `POST /api/v1/cron/refresh-intraday` | 30-min candles + live Exposure Scores |
| `0 23 * * 2,5` | `POST /api/v1/cron/refresh-history-and-scores` | History + historical scores + retention cleanup |

---

## Asset universe

**Guest / non-holder — 8 stocks, 30 crypto:** NVDA, TSLA, COIN, MSTR, AMD, MSFT, META, PLTR, plus 30 crypto across Layer 1/2, DeFi, Oracle/Data, AI/Compute, Storage and Memecoin categories.

**Verified `$SynthEx` holder — 20 stocks, 100 crypto.** See `docs/methodology.md` for the full catalogue and `docs/architecture.md` for how access is enforced.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS |
| Animation | Framer Motion |
| Graph | @xyflow/react |
| Charts | lightweight-charts v5 |
| Wallet | Reown AppKit, Wagmi, Viem — backed by server-side SIWE |
| Backend | Python FastAPI, Pydantic v2 |
| Database | Render PostgreSQL, SQLAlchemy 2 async, Alembic |
| Providers | CoinGecko (crypto), Marketstack (stocks) |
| Hosting | Render (API), Vercel (frontend), Cloudflare Worker (scheduler) |

---

## Disclaimer

Synthetic Exposure Scores are for informational purposes only and do not constitute investment advice. See [docs/methodology.md](docs/methodology.md) for the full methodology. Synthetic Exposure does not custody assets, operate an exchange, or guarantee equivalent asset performance.
