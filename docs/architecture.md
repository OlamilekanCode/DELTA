# Synthetic Exposure Architecture

## Repository structure

```
delta/
├── web/              Next.js 16 App Router frontend
├── api/              Python 3.12+ FastAPI backend
├── docs/             Architecture, methodology, API reference
├── .env.example      Template for all environment variables
└── README.md
```

---

## Frontend

**Framework**: Next.js 16, App Router, TypeScript strict mode
**Styling**: Tailwind CSS with Synthetic Exposure design tokens
**Animation**: Framer Motion (`prefers-reduced-motion` respected)
**Graph**: `@xyflow/react` — loaded only on `/graph/[symbol]`
**Charts**: lightweight-charts v5 — dynamic import, only on `/asset/[symbol]`
**Wallet**: Reown AppKit + Wagmi + Viem — client-side balance read, no transaction signing

### Bundle strategy

- Landing page: statically rendered at build time; no heavy dependencies
- Price chart: `AssetHistoryChartClient` wraps `AssetHistoryChart` with `ssr: false`
- Exposure graph: `ExposureGraphCanvasClient` wraps `ExposureGraphCanvas` with `ssr: false`
- Wallet SDK: dynamic import; loads when wallet modal opens

---

## Backend

**Framework**: FastAPI + Pydantic v2
**Database**: PostgreSQL (production) / SQLite (development and tests)
**ORM**: SQLAlchemy 2 async — `asyncpg` driver for PostgreSQL, `aiosqlite` for SQLite
**Migrations**: Alembic
**HTTP client**: httpx with tenacity retry/backoff
**Analytics**: NumPy — Pearson correlation on aligned daily log returns
**Providers**: Marketstack (stock EOD), CoinGecko (crypto OHLCV + batch quotes)

---

## Database schema

| Table | Purpose |
|-------|---------|
| `assets` | Asset catalogue (38 rows: 8 stocks + 30 crypto) |
| `daily_prices` | Historical daily close prices, 90-day depth per asset |
| `asset_quotes` | Current price snapshot, one row per crypto asset (unique on `asset_id`) |
| `stored_exposure_scores` | Pre-computed Pearson scores for all stock × crypto pairs |

---

## Data refresh schedule

| Command | Recommended schedule | Notes |
|---------|---------------------|-------|
| `refresh-crypto-quotes` | Every 5 minutes | CoinGecko `/coins/markets` — 1 request for all 30 crypto |
| `refresh-stock-eod` | Tuesday and Friday | Marketstack EOD — skips weekends automatically |
| `recompute-scores` | Tuesday and Friday (after EOD) | Pearson scores for all 8 × 30 = 240 pairs |
| `backfill` | Once on first deploy | 90-day historical backfill for all 38 assets |

All commands are idempotent. On provider failure, existing stored data is preserved and the error is logged. A PID-file lock prevents overlapping runs of the same command.

---

## Wallet gating

`$DELTA` token balance is read client-side by Reown AppKit / Wagmi using the connected wallet. No backend RPC call is made for balance reads. The backend has no session layer and does not verify holdings.

Portfolio analysis (which would require backend verification) is not yet implemented.

---

## Security

- Provider API keys: backend environment variables only, never in `NEXT_PUBLIC_*` variables
- Wallet: read-only connection, no transaction signing
- Session: not implemented
- CORS: allow-listed origins configured via `CORS_ORIGINS` environment variable

---

## Deployment

| Service | Platform | Notes |
|---------|----------|-------|
| Frontend (`web/`) | Vercel | Static + server-rendered; no secrets at runtime |
| Backend API (`api/`) | Railway | Managed; `$PORT` set by Railway |
| Database | Railway managed PostgreSQL | |
| Cron jobs | Railway cron | Three schedules matching the refresh table above |

### Deployment order

1. Provision Railway project + managed PostgreSQL
2. Set all environment variables in Railway (never commit secrets)
3. Deploy backend, run `alembic upgrade head`, verify `/api/v1/health`
4. Run `python -m app.ingestion.commands backfill`
5. Run `python -m app.ingestion.commands recompute-scores`
6. Deploy frontend with correct `NEXT_PUBLIC_API_BASE_URL`
