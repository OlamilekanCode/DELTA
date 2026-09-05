# DELTA

**Map the Market.** See how stocks and crypto move together.

DELTA bridges the stock market and crypto by mapping historical correlations through an interactive Exposure Graph and a 0–1 Exposure Score. The `$DELTA` utility token unlocks advanced graph depth, portfolio exposure, and detailed score breakdowns.

---

## Status

| Milestone | Status |
|-----------|--------|
| 0 — Repository foundation | ✅ Complete |
| 1 — Polished landing page | ✅ Complete |
| 2 — Real data backend | 🔄 In progress |
| 3 — Exposure Score engine | ⏳ Planned |
| 4 — Wallet and token gating | ⏳ Planned |
| 5 — Portfolio exposure | ⏳ Planned |
| 6 — Production readiness | ⏳ Planned |

---

## Local development

### Prerequisites

- Node.js 20+ and npm
- Python 3.12+ (for api/ — required from Milestone 2)

### Frontend (web/)

```bash
# 1. Install dependencies
cd web
npm install

# 2. Copy and configure environment variables
cp ../.env.example .env.local
# Edit .env.local — NEXT_PUBLIC_API_BASE_URL defaults to http://localhost:8000

# 3. Start the development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

#### Other frontend commands

```bash
npm run build         # Production build
npm start             # Serve the production build
npm run lint          # Run ESLint (note: not next lint — removed in Next.js 16)
npx tsc --noEmit      # TypeScript type-check
```

### Backend API (api/) — Milestone 2+

```bash
# 1. Create and activate a virtual environment
cd api
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and configure environment variables
cp ../.env.example .env
# Edit .env with real DATABASE_URL, API keys, etc.

# 4. Start the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## Project structure

```
delta/
├── web/              Next.js App Router frontend
├── api/              FastAPI backend (active from Milestone 2)
├── docs/
│   ├── architecture.md
│   ├── methodology.md
│   └── api.md
├── .env.example      Copy to web/.env.local and api/.env
└── README.md
```

---

## Railway deployment (Milestone 6)

> Do not deploy to production until the owner supplies: final domain, `$DELTA` token contract address, minimum balance, DEX pool URL, and all required secrets.

### Services

| Service | Root | Build | Start |
|---------|------|-------|-------|
| `delta-web` | `web/` | `npm run build` | `npm start` |
| `delta-api` | `api/` | `pip install -r requirements.txt` | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| `delta-postgres` | Railway managed | — | — |
| `delta-refresh` | `api/` | — | `python -m app.ingestion.runner` (cron) |

### Deployment order

1. Create Railway project and attach managed PostgreSQL
2. Set all environment variables in Railway (not in git)
3. Deploy `delta-api`, run Alembic migrations (`alembic upgrade head`), verify `/api/v1/health`
4. Run first data ingestion: `python -m app.ingestion.runner`
5. Deploy `delta-web` with `NEXT_PUBLIC_API_BASE_URL` pointing to the live API
6. Configure Cloudflare DNS and enforce HTTPS
7. Verify public, connected, locked, and unlocked states

### Environment variables

All required environment variables are documented in `.env.example`. Set them in Railway's environment variable panel — never commit `.env` files with real values.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js (App Router), TypeScript, Tailwind CSS |
| Animation | Framer Motion |
| Graph | @xyflow/react (graph routes only) |
| Charts | TradingView Lightweight Charts (dynamic import) |
| Wallet | Reown AppKit, Wagmi, Viem (Milestone 4) |
| Backend | Python FastAPI, Pydantic v2 |
| Database | PostgreSQL, SQLAlchemy 2, Alembic |
| Hosting | Railway (web + api + db + cron) |
| DNS/SSL | Cloudflare |

---

## Disclaimer

DELTA Exposure Scores are for informational purposes only and do not constitute investment advice. See `/methodology` for the complete explanation. DELTA does not custody assets, operate an exchange, or guarantee equivalent asset performance.
