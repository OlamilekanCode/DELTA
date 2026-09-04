# DELTA Architecture

> Updated: Milestone 0 — Placeholder. Expand in Milestone 2.

## Repository structure

```
delta/
├── web/        Next.js 15+ App Router frontend
├── api/        Python FastAPI backend (Milestone 2+)
├── docs/       This directory
├── .env.example
├── README.md
└── AGENTS.md
```

## Services (Railway — Milestone 6 deployment)

| Service | Source root | Responsibility |
|---------|-------------|----------------|
| `delta-web` | `web/` | Build and serve Next.js |
| `delta-api` | `api/` | Run Alembic migrations, then serve FastAPI |
| `delta-postgres` | Railway managed | Store assets, prices, scores, sessions |
| `delta-refresh` | `api/` | Railway Cron — idempotent market data + score refresh |

## Frontend architecture

- **Framework**: Next.js App Router, TypeScript strict mode
- **Styling**: Tailwind CSS with DELTA design tokens
- **Animation**: Framer Motion (`prefers-reduced-motion` respected everywhere)
- **Graph**: `@xyflow/react` — only on `/graph/[symbol]`, never in the landing bundle
- **Charts**: TradingView Lightweight Charts — dynamically imported
- **Wallet**: Reown AppKit + Wagmi + Viem (Milestone 4)
- **State**: TanStack Query for server state
- **Validation**: Zod for API response shapes

### Bundle strategy

- Landing page: statically rendered, no wallet SDK, no @xyflow/react
- Hero graph: custom SVG/Canvas animation (~50 KB gzipped)
- Charts: dynamic import with Suspense skeleton
- Full graph: dynamic import, only loads on `/graph/*` routes
- Wallet: dynamic import, loads when user clicks "Connect wallet"

## Backend architecture (Milestone 2+)

- **Framework**: FastAPI + Pydantic v2
- **Database**: PostgreSQL via SQLAlchemy 2 async + Alembic migrations
- **HTTP client**: HTTPX for external provider calls
- **Analytics**: Polars or Pandas + NumPy/SciPy
- **Cron job**: `python -m app.jobs.refresh_market_data` — idempotent, Railway-invoked
- **Providers**: Marketstack (stocks), CoinGecko (crypto), DEX Screener (optional)

## Security model

- Provider API keys: backend environment variables only, never `NEXT_PUBLIC_*`
- Wallet connection: read-only (no transaction signing for auth)
- Session: backend-issued SIWE nonce, HTTP-only cookie
- RPC balance reads: trusted backend RPC call, never trust browser-supplied values

## Deployment order (Milestone 6)

1. Create Railway project + managed PostgreSQL
2. Set production environment variables in Railway (no secrets in git)
3. Deploy `delta-api`, run Alembic migrations, verify `/api/v1/health`
4. Run first data refresh job
5. Deploy `delta-web` with production `NEXT_PUBLIC_API_BASE_URL`
6. Configure Cloudflare DNS + HTTPS
7. Run smoke tests for public, connected, locked, and unlocked states

## CORS policy

Allow only:
- `http://localhost:3000` (development)
- Production apex domain
- Preview URLs (if Railway preview environments are enabled)
