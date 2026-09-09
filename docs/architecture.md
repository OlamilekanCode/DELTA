# Synthetic Exposure — Architecture

## Repository structure

```
synthetic-exposure/
├── web/              Next.js 16 App Router frontend
├── api/              Python 3.12+ FastAPI backend
├── cloudflare/       Cron dispatcher Worker
├── docs/             Architecture, methodology, API reference
├── .env.example      Template for all environment variables
└── README.md
```

---

## Infrastructure layout

```
Vercel (Next.js)  →  Render API (FastAPI)  →  Render PostgreSQL
                             ↑
                   Cloudflare Worker (cron dispatcher)
```

Production database is Render PostgreSQL — not Neon or Railway. Local development and the test suite use SQLite.

---

## Frontend

**Framework**: Next.js 16, App Router, TypeScript strict mode
**Styling**: Tailwind CSS
**Animation**: Framer Motion, honoring `prefers-reduced-motion`
**Graph**: `@xyflow/react` — loaded only on `/graph/[symbol]`, `ssr: false`
**Charts**: lightweight-charts v5 — dynamic import, only on `/asset/[symbol]`, `ssr: false`
**Wallet**: Reown AppKit + Wagmi + Viem, backed by server-side SIWE authentication (see "Authentication" below) — the wallet SDK itself never makes an access decision

### BFF (Backend-for-Frontend) pattern

Browser → same-origin Next.js route handlers (`web/app/api/**/route.ts`) → Render API, with the session forwarded as an `Authorization: Bearer` header. The session token lives only in an `HttpOnly`, `Secure` cookie set by the Next.js route handlers — it is never readable from client-side JavaScript and never stored in `localStorage`.

Server Components (asset/explore/graph pages) call the backend through `web/lib/server-api.ts`, which forwards the session cookie (if present) directly to `BACKEND_API_URL` with `cache: "no-store"` — this is what lets a verified holder's server-rendered page actually see holder-only data. Without a session, requests fall back to the public `NEXT_PUBLIC_API_BASE_URL` with normal ISR revalidation, identical to guest behavior. Client Components needing protected data (portfolio, entitlements, chart-range switching) go through the route handlers in `web/app/api/**`, never the public backend origin directly.

### Bundle strategy

- Landing page: statically rendered at build time; no heavy dependencies.
- Wallet SDK: initialized once at module scope so `useAppKit`/`useAccount` resolve regardless of render order; the connect modal itself loads on demand.

---

## Backend

**Framework**: FastAPI + Pydantic v2
**Database**: PostgreSQL (production) / SQLite (development and tests)
**ORM**: SQLAlchemy 2 async — `asyncpg` for PostgreSQL, `aiosqlite` for SQLite
**Migrations**: Alembic, `render_as_batch=True` for SQLite compatibility
**HTTP client**: httpx with tenacity retry/backoff
**Analytics**: NumPy — Pearson correlation on aligned log returns
**Providers**: Marketstack (stock EOD + intraday), CoinGecko (crypto OHLCV + batch quotes)

### Data pipeline

Three independently runnable phases, matching `api/app/ingestion/commands.py`:

1. **Ingestion** — scheduled jobs or CLI commands fetch provider data and upsert `daily_prices`, `asset_quotes`, `crypto_quote_observations`, `intraday_prices`.
2. **Computation** — `recompute-scores` and the intraday scheduler read aligned prices and write `stored_exposure_scores` / `intraday_exposure_scores`.
3. **Query** — API endpoints read pre-computed scores only; no Exposure Score is ever calculated inside a request handler.

### Schema management

SQLite (dev/test) creates tables directly at startup since there's no separate migration deploy step. PostgreSQL (production) relies exclusively on `alembic upgrade head` — the backend never runs `Base.metadata.create_all()` against Postgres.

---

## Database schema (selected tables)

| Table | Purpose |
|-------|---------|
| `assets` | Asset catalogue — 20 stocks + 100 crypto, each with an `access: "free" \| "holder"` field |
| `daily_prices` | Historical daily close prices per asset, 90-day depth |
| `asset_quotes` | Latest crypto price snapshot, one row per crypto asset |
| `crypto_quote_observations` | Timestamped 5-minute crypto price samples used to build 30-min candles (7-day retention) |
| `intraday_prices` | 30-minute OHLC candles per asset (~90-day retention) |
| `stored_exposure_scores` | Pre-computed 90-day Pearson scores per stock × crypto pair |
| `intraday_exposure_scores` | Latest 30-minute Pearson score per stock × crypto pair |
| `wallet_users`, `auth_nonces`, `sessions` | SIWE authentication |
| `cached_wallet_balances` | Server-cached `$SynthEx` holder balance per wallet |
| `cached_wallet_positions` | Server-cached on-chain portfolio asset positions per wallet |
| `wallet_entitlements` | Verified cumulative purchase tier per wallet |
| `claimed_purchase_transactions` | Immutable record of each verified `$SynthEx`/ETH purchase |

All ingestion is idempotent (upsert on the natural key). Provider failures preserve existing data — a job never deletes valid rows before a full replacement set is ready.

---

## Access control

Two catalogue tiers: guests/non-holders see 8 free stocks + 30 free crypto; verified `$SynthEx` holders see the full 20 stocks + 100 crypto. Enforcement lives in `api/app/services/access.py` and is applied at the database-query level (a `WHERE access = 'free'` clause, not a post-hoc filter) on every endpoint that serves asset data: `/assets`, `/assets/search`, `/assets/{symbol}`, `/assets/{symbol}/history`, `/exposures/{symbol}`, `/graphs/{symbol}`, `/correlation/{symbol}`, `/intraday/{symbol}`. Requesting a holder-only stock returns `401` with no session and `403` for an authenticated non-holder. The frontend never relies solely on hiding links.

---

## Authentication (SIWE / ERC-4361)

1. Wallet connects via Reown AppKit; the app compares the connected chain ID against `NEXT_PUBLIC_SYNTHEX_CHAIN_ID` and shows a "wrong chain" state until the wallet is on the configured chain — Base is only ever the SDK's bootstrap placeholder network, never treated as correct.
2. Backend issues a short-lived, single-use nonce (`POST /auth/nonce`).
3. Wallet signs a human-readable SIWE message — no gas, no approval, no transaction.
4. Backend validates the full EIP-4361 structure (domain, URI scheme/host, `Version: 1`, chain ID, no duplicate fields, address format, issued-at/expiry, message/signature length limits) against dedicated `SIWE_ALLOWED_DOMAINS`/`SIWE_ALLOWED_URIS` settings — not CORS — verifies the signature, then atomically consumes the nonce via a conditional `UPDATE ... WHERE used = false` (not a read-then-write race).
5. Backend creates an opaque session; only its HMAC-SHA256 hash (keyed by `SESSION_SECRET`) is stored.
6. The Next.js BFF sets the session in an `HttpOnly`, `Secure`, `SameSite=Strict` cookie.

Sessions last 30 days. Switching the connected wallet address ends the active session (each address is a separate account); the frontend detects the address change and logs out before any re-authentication.

---

## Holder verification and purchases

`api/app/services/blockchain.py` defines a minimal JSON-RPC client (`JsonRpcProvider`) and a mock (`MockRpcProvider`) behind a common `RpcProvider` interface, used by:

- `services/holder.py` — reads the `$SynthEx` ERC-20 balance, compares it (as integers, never floats) against `SYNTHEX_HOLDER_MIN_BALANCE_RAW`, and upserts `cached_wallet_balances`. Called after login, on explicit refresh, after purchase verification, and at a 5-minute cache interval — never on an ordinary asset-page request.
- `services/purchase_verification.py` — verifies a submitted `$SynthEx`/ETH transaction hash: receipt success, chain ID, confirmations, sender, approved router/pool destination, an ERC-20 `Transfer` log moving `$SynthEx` to the wallet, ETH/WETH spent, and the nearest stored ETH/USD price at the block timestamp. Verified purchases update the wallet's cumulative tier atomically and can never be claimed twice.
- `services/portfolio.py` — reads configured portfolio asset contracts (`services/portfolio_assets.py`, a version-controlled list — never a database-configurable or invented address) and upserts `cached_wallet_positions`; `compute_portfolio_exposure` then reads only stored positions, stored quotes and stored Exposure Scores, never a live provider call.

All three fail closed — they return an honest `not_configured`/empty state until `ROBINHOOD_RPC_URL`, `SYNTHEX_TOKEN_ADDRESS`, router/pool addresses, and (for portfolio) a populated contract list are supplied. The private `ROBINHOOD_RPC_URL` never reaches the frontend.

**Currently unconfigured — not yet live:**

- `services/portfolio_assets.py`'s `PORTFOLIO_ASSET_CONTRACTS` list is empty. No Robinhood Chain (or Ethereum/Base) token contract address has been confirmed yet, so `refresh_wallet_positions()` has nothing to read — this is expected, not a bug, and portfolio refresh reports `not_configured` accordingly rather than a misleading zero.
- `ETHEREUM_RPC_URL` and `BASE_RPC_URL` are unset, so portfolio reads on those chains stay disabled even once `PORTFOLIO_CHAIN_IDS` includes them.
- `SYNTHEX_DEX_ROUTER_ADDRESSES`, `SYNTHEX_DEX_POOL_ADDRESSES`, `SYNTHEX_WETH_ADDRESS` and `SYNTHEX_TOKEN_START_BLOCK` are all unset in this environment — purchase verification fails closed until every one of them is supplied, and native-ETH purchases additionally require a confirmed router method registered in `purchase_verification.ROUTER_ADAPTERS` (also empty today) before raw `tx.value` can ever be trusted.

---

## Cron scheduling

Three distinct Cloudflare Cron Trigger schedules dispatch to protected `/api/v1/cron/*` endpoints (see `cloudflare/src/worker.js`), authenticated with `X-Cron-Secret`:

| Schedule | Endpoint | Purpose |
|----------|----------|---------|
| `*/5 * * * *` | `refresh-crypto-quotes` | One CoinGecko batch call for every crypto asset; also persists 5-min observations |
| `2,32 * * * *` | `refresh-intraday` | One batched Marketstack call for every stock; crypto candles built from stored observations (zero CoinGecko calls); recomputes live scores |
| `0 23 * * 2,5` | `refresh-history-and-scores` | Stock EOD, crypto history, historical score recompute, and retention/auth cleanup |

The quote and history jobs share a PostgreSQL advisory lock (no-op on SQLite); intraday uses its own lock so it never queues behind the others. A job that fails entirely (every provider call failed) returns a non-2xx status — the worker never treats that as a silent success.

---

## Provider call budget

One HTTP request is not the same thing as one unit of provider billing —
both CoinGecko and Marketstack bill per symbol/asset requested within a
batch call, not per HTTP round trip. The figures below keep those two
numbers separate, and keep the CoinGecko monthly running rate separate
from the Marketstack five-day prelaunch figure — they are not the same
budget and must not be added or substituted for one another.

**CoinGecko** (monthly running rate, current 100-asset holder catalogue):

| Job | Calculation | Approx. monthly calls |
|---|---|---|
| Quote batch (`refresh-crypto-quotes`, every 5 min, 24/7) | `288 calls/day × 30 days` | ≈ 8,640 |
| Historical backfill (100 assets, Tue/Fri) | 2 refreshes/week × ~4.3 weeks | ≈ 800–1,000 |

Each call above is one batch HTTP request covering up to 100 assets — not
100 separate credits per call, but check the active plan's per-asset
billing multiplier before treating "calls" and "credits" as interchangeable.
Retries and any ad-hoc/manual backfills are additional and must be added
to the risk estimate before committing to a plan tier.

**Marketstack** (five-day prelaunch window, 20-stock holder catalogue):

```
20 symbols × ~13 completed 30-minute buckets/day × 5 trading days
  ≈ 1,300 symbol credits
```

This is a single batched HTTP request per 30-minute run (one call covering
all 20 symbols), but Marketstack bills per symbol within that batch — so
"1,300" is symbol-credits, not HTTP calls. It also does not include EOD
history refresh, backfill, or retry attempts, which consume additional
credits on top of this figure. **The five-day prelaunch plan is not
"within a 1,300-credit budget"** — that figure covers Marketstack intraday
only; CoinGecko's usage above is a separate, larger, ongoing monthly
number that must be budgeted independently.

**Guardrails:**

- The free (8 stocks / 30 crypto) and holder (20 stocks / 100 crypto)
  catalogues are fixed by product agreement — do not shrink either to fit
  a provider budget without separate approval.
- A configurable intraday ingestion scope/budget guard (e.g. capping
  symbols refreshed per run) is a reasonable future addition, but it must
  never silently change which assets a tier can see, and a
  scope-skipped symbol must report `collecting_data` honestly rather than
  serving a stale score as current.

---

## Security

- Provider and RPC secrets live only in backend environment variables, never in `NEXT_PUBLIC_*` variables.
- Session tokens are stored server-side only as an HMAC-SHA256 hash; the raw token lives only in an `HttpOnly` cookie.
- CORS is allow-listed via `CORS_ORIGINS`; SIWE's domain/URI allowlist is a separate, dedicated setting.
- Auth endpoints are rate-limited per IP; nonce/session cleanup runs as part of the historical maintenance job.
- `X-Cron-Secret` gates every scheduled job endpoint.

---

## Deployment

| Service | Platform | Notes |
|---------|----------|-------|
| Frontend (`web/`) | Vercel | `NEXT_PUBLIC_*` vars in project settings; `BACKEND_API_URL` server-only |
| Backend API (`api/`) | Render | Web service; `$PORT` set by Render |
| Database | Render PostgreSQL | `alembic upgrade head` runs schema changes — never `create_all()` |
| Cron scheduler | Cloudflare Worker + Cron Triggers | `synthetic-exposure-cron`, forwards to `/api/v1/cron/*` |

### Deployment order

1. Provision Render PostgreSQL; set `DATABASE_URL` on the API service.
2. Deploy the Render web service with all backend environment variables set. Start command: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
3. Verify `GET /api/v1/health` returns `{"status": "ok"}` and `alembic heads` shows exactly one head.
4. Run `python -m app.ingestion.commands backfill` once to seed history (skip if `USE_DEMO_DATA=true`).
5. Deploy `cloudflare/` with `wrangler secret put API_BASE_URL` / `CRON_SECRET` matching the Render service, then `npx wrangler deploy`.
6. Deploy the frontend to Vercel with `NEXT_PUBLIC_API_BASE_URL` and `BACKEND_API_URL` pointing at the Render origin.

Never run migration downgrade testing against the production database.
