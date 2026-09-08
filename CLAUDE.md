# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Product overview

**Synthetic Exposure** — a stock ↔ crypto correlation analytics platform. The backend computes signed Pearson correlation scores between stocks and crypto assets using 90-day aligned daily log returns. The frontend visualises them as exposure scores, charts and graphs.

- Frontend: Next.js 16.3.4 / React 19.2.8 on Vercel
- Backend: FastAPI (async) on Render
- Database: Render PostgreSQL (production), SQLite (local dev and tests)
- Cron dispatcher: Cloudflare Worker → Render API
- Token: `$SynthEx` on Robinhood Chain (EVM)

---

## Commands

### Frontend (`web/`)

```bash
npm run dev          # dev server on :3000
npm run build        # production build
npm run lint         # ESLint
npx tsc --noEmit    # type-check
```

### Backend (`api/`)

```bash
# Setup
python -m venv .venv
pip install -r requirements.txt

# Database
alembic upgrade head
alembic heads          # confirm exactly one head

# Dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Ingestion CLI
python -m app.ingestion.commands backfill
python -m app.ingestion.commands refresh-crypto-quotes
python -m app.ingestion.commands refresh-stock-eod
python -m app.ingestion.commands refresh-crypto-history
python -m app.ingestion.commands recompute-scores
python -m app.ingestion.commands refresh-all

# Tests
pytest tests/ -v
pytest tests/test_correlation.py -v   # single file
pytest tests/ -k "test_name" -v       # single test

# Linting
python -m ruff check .
python -m ruff check . --fix
```

### Quality gate (run before every commit)

```bash
(cd web && npx tsc --noEmit && npm run lint && npm run build)
(cd api && python -m ruff check . && pytest tests/ -v && alembic heads)
```

Never run migration downgrade testing against the production database.

---

## Architecture

### Infrastructure layout

```
Vercel (Next.js)  →  Render API (FastAPI)  →  Render PostgreSQL
                             ↑
                   Cloudflare Worker (cron dispatcher)
```

The Cloudflare Worker fires on schedule and calls protected Render endpoints. Provider APIs (CoinGecko, Marketstack) are called only by scheduled backend jobs, never per visitor.

### Data pipeline

Three independently runnable phases:

1. **Ingestion** — CLI or cron fetches provider data → upserts `daily_prices` + `asset_quotes`
2. **Computation** — `recompute-scores` reads aligned prices → calculates Pearson r → writes `stored_exposure_scores`
3. **Query** — API reads pre-computed scores; no computation happens per request

### Scoring (`api/app/services/correlation.py`) — current state

- **Inner-join** stock and crypto `daily_prices` by date before computing returns (critical: ensures the same calendar intervals before differencing)
- `log_returns()`: `ln(p_t / p_{t-1})` on consecutive aligned prices
- `pearson_r()` via NumPy — requires `MIN_OBSERVATIONS = 45` aligned dates; returns `0.0` for NaN or insufficient data
- **Current score**: `max(0.0, raw_correlation)` — **positive-only clamp, to be removed**

### Provider selection (`api/app/ingestion/runner.py`)

- `USE_DEMO_DATA=true` → `FixtureProvider` for every asset (deterministic, no external calls)
- `USE_DEMO_DATA=false` → `MarketstackProvider` (stocks) + `CoinGeckoProvider` (crypto); both keys required

All ingestion is idempotent: upsert on `(asset_id, date)`. Provider failures preserve existing data — ingestion is not all-or-nothing. An asset's prices are always either all-demo or all-real; mixed rows are purged on upsert.

### Demo data

Fixture assets seed on lifespan startup when `USE_DEMO_DATA=true` (`api/app/providers/fixtures.py`). Every fixture-derived row has `is_demo=True` in the database. API responses expose `demo: bool`. The frontend must show `DemoDataBadge` on all fixture-derived data. Never mix demo and real rows for the same asset.

### Migrations

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic heads    # must show exactly one head
```

All migrations use `render_as_batch=True` (set in `api/alembic/env.py`) for SQLite compatibility. Never rewrite historical revision identifiers. The revision chain currently ends at `0005_fix_pol_coingecko_id`.

### Frontend route groups

```
app/
├── layout.tsx                # root — Web3Provider wrapper
├── (main)/
│   ├── layout.tsx            # Navigation + Footer
│   ├── page.tsx              # landing page
│   ├── explore/page.tsx
│   ├── asset/[symbol]/page.tsx
│   ├── portfolio/page.tsx
│   └── methodology/page.tsx
└── (graph)/
    ├── layout.tsx            # full-screen, no nav
    └── graph/[symbol]/page.tsx
```

### Heavy dependencies — always SSR-disabled

These cause hydration errors if rendered server-side; always use `dynamic(..., { ssr: false })`:

- `@xyflow/react` — graph canvas (`ExposureGraphCanvasClient`)
- `lightweight-charts` — price charts (`AssetHistoryChartClient`)
- `HeroGraph` in `components/hero/HeroGraph.tsx`

### Animation

- Framer Motion components: call `useReducedMotion()` and skip or minimise motion when it returns `true`
- CSS animations: honour `prefers-reduced-motion` media query

### Cron and locking

Cron endpoints (`POST /api/v1/cron/*`) require `X-Cron-Secret` header matching `CRON_SECRET`. PostgreSQL advisory locks (`api/app/ingestion/lock.py`) prevent overlapping runs. SQLite (dev/test) skips the advisory lock. The Cloudflare Worker name is currently `delta-cron` (to be renamed).

### CoinGecko Demo

The CoinGecko Demo API key is for testing and prelaunch use only. Commercial launch requires an appropriately licensed CoinGecko plan. Include CoinGecko attribution wherever Demo API data is displayed.

---

## Current asset catalogue

Defined in `api/app/providers/fixtures.py`.

**8 stocks (free / guest access):** NVDA, TSLA, COIN, MSTR, AMD, MSFT, META, PLTR

**30 crypto assets (free / guest access):** BTC, ETH, SOL, BNB, XRP, ADA, AVAX, DOT, NEAR, ICP, APT, SUI, HBAR (Layer 1), ARB, OP, POL (Layer 2), UNI, AAVE, INJ (DeFi), LINK, GRT (Oracle/Data), TAO, RENDER, FET, AKT, AIOZ (AI/Compute), FIL, AR (Storage), DOGE, PEPE (Memecoin)

The catalogue is version-controlled and is not replaced dynamically at startup.

---

## Environment variables — current

### Backend (`api/`)

| Variable | Notes |
|---|---|
| `DATABASE_URL` | PostgreSQL (prod) or SQLite path (dev) |
| `USE_DEMO_DATA` | `true` seeds fixtures; `false` requires API keys |
| `MARKETSTACK_API_KEY` | Required when `USE_DEMO_DATA=false` |
| `COINGECKO_API_KEY` | Required when `USE_DEMO_DATA=false` |
| `COINGECKO_API_TYPE` | `demo` or `pro` |
| `CRON_SECRET` | Authenticates `/api/v1/cron/*` |
| `SESSION_SECRET` | Present in config; not yet used |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `delta_chain_id` | Chain ID — to be renamed `synthex_chain_id` |
| `delta_token_address` | Token contract — to be renamed |
| `delta_min_balance` | Min raw balance — to be renamed |
| `base_rpc_url` | Optional; not currently used server-side |

### Frontend (`web/`)

| Variable | Notes |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Render API origin |
| `NEXT_PUBLIC_REOWN_PROJECT_ID` | Reown AppKit |
| `NEXT_PUBLIC_CHAIN_ID` | Currently 8453 (Base) — to be Robinhood Chain |
| `NEXT_PUBLIC_DELTA_TOKEN_ADDRESS` | ERC-20 balance reads — to be renamed |
| `NEXT_PUBLIC_DELTA_MIN_BALANCE` | Min raw units — to be renamed |
| `NEXT_PUBLIC_SITE_URL` | Canonical origin for wallet metadata |
| `NEXT_PUBLIC_DEX_BUY_URL` | DEX buy link |

### Cloudflare Worker

| Variable | Purpose |
|---|---|
| `API_BASE_URL` | Render API origin |
| `CRON_SECRET` | Must match backend `CRON_SECRET` |

---

## Known legacy identifiers to rename

The following identifiers still reference the retired `DELTA` branding. Rename them without breaking Alembic revision history:

- `api/app/config.py`: `delta_chain_id`, `delta_token_address`, `delta_min_balance` → `synthex_*`
- `web/lib/delta-gate.ts` → `web/lib/access-gate.ts`
- `web/hooks/useDeltaGate.ts` → `web/hooks/useAccessGate.ts`
- `web/components/shared/DeltaLogo.tsx` → `BrandLogo`
- `web/components/sections/DeltaUtilitySection.tsx` → `TokenUtilitySection`
- `NEXT_PUBLIC_DELTA_TOKEN_ADDRESS` / `NEXT_PUBLIC_DELTA_MIN_BALANCE` → `NEXT_PUBLIC_SYNTHEX_*`
- `cloudflare/wrangler.toml` worker name `delta-cron` → `synthetic-exposure-cron`

Do not rename applied Alembic revision files or their `revision` / `down_revision` identifiers.

---

---

# Target architecture

The following describes the required system. **None of the items below are implemented yet.** Do not claim they are complete until the code exists and the quality gate passes.

## Exposure scores — signed

Remove the `max(0.0, r)` clamp from `correlation.py`. The stored score must be the raw Pearson correlation in `[−1.00, +1.00]`.

Display rules:
- Always show the sign: `+0.78`, `−0.62`, `0.00`
- Never display as percentage or `/100`
- Edge thickness: `abs(score)`
- Colour: separate accessible colours for positive and inverse relationships
- Graph filters: `All`, `Positive`, `Inverse`
- Sort: separate strongest-positive and strongest-inverse lists

## Historical score — corrected methodology

Preserve: log returns, Pearson correlation, 90-day window, inner-join before returns, minimum observations, Tuesday/Friday recalculation.

Corrections required:
- **Stock closes**: prefer `adj_close` from Marketstack; fall back to `close` and record the fallback in data-quality metadata; reject missing, zero or negative prices
- **Crypto alignment**: obtain CoinGecko hourly historical prices; use a US exchange calendar to determine the actual closing time of each session (including holidays and shortened days); select the crypto price nearest the market close; store the session-aligned value; compute daily close-to-close log returns after alignment
- Store timestamps in UTC; apply `America/New_York` for market rules

API response must include: observation count, data window, data timestamp, calculation timestamp, provider, data quality, demo status, model version.

## Intraday (30-minute) scores

### New database tables required (via Alembic migration)

**`intraday_prices`**: asset_id, bucket_ts (UTC), interval, open, high, low, close, volume (optional), provider, sample_count, data_quality, is_demo, created_at, updated_at. Unique on `(asset_id, interval, bucket_ts)`. Repeated ingestion must upsert.

**`intraday_exposure_scores`**: stock_id, crypto_id, score, observations, interval, window_sessions, data_ts, computed_at, model_version, is_demo, data_quality. Unique on `(stock_id, crypto_id, interval)`. Store only the latest score per pair.

### Intraday calculation rules

- Use completed 30-minute stock and crypto candles
- Match on exact normalised UTC buckets within the same US market session
- Candle return: `log(close/open)` — no overnight or weekend return leakage
- Up to 20 US trading sessions; minimum 65 valid matched intervals
- Signed Pearson correlation stored as `[−1.00, +1.00]`
- Model version: `pearson_intraday_v1`
- Full result set calculated first, then bulk atomic upsert; partial failure must not delete last valid scores

If insufficient observations, return `collecting_data` status with current count, required count and estimated readiness.

### Crypto intraday collection

Use CoinGecko `/coins/markets` batch endpoint: all 100 crypto assets in one request.

Schedule:
- US market open: every 5 minutes
- US market closed: every 30 minutes
- Backend determines market state using exchange calendar; Cloudflare triggers every 5 minutes but backend decides whether a provider call is due

Every quote refresh: update `asset_quotes`, insert/upsert timestamped observation, preserve existing data on failure.

Create 30-minute crypto candles from timestamped samples (first=open, max=high, min=low, last=close). Require minimum sample count; mark reduced-quality candles; never calculate from an unfinished bucket. Do not backfill with CoinGecko Demo — collect prospectively.

### Stock intraday collection

Extend `MarketstackProvider` with a batch-capable 30-minute intraday method for all 20 stocks. Use exchange calendar for timestamps, daylight-saving changes and shortened sessions. Normalise provider timestamps carefully (confirm candle-start vs candle-end convention).

## Market status endpoint

Add `GET /api/v1/market-status` returning: `is_open`, market timezone, last market close, next market open, current or last completed bucket, status reason.

Do not recompute the intraday score while the US market is closed (except the final closing calculation). The frontend shows a blue status badge: `US market closed` with last calculation time below it. Crypto quotes continue updating on their own schedule while the score remains frozen.

## Chart ranges

Add controls: `4H`, `1D`, `1W`, `1M` (30-minute stored data), `3M`, `1Y` (daily stored data).

Chart range changes query the Synthetic Exposure database only — never trigger a direct provider request. Return a clear `collecting_data` state when a selected intraday range has not yet accumulated enough observations.

Standard asset charts remain public. Holder-only assets require authentication.

### Data retention (managed by idempotent cleanup command)

- Raw 5-minute crypto observations: 7 days
- 30-minute candles: ~90 days
- Daily session-aligned data: long-term
- Index all timestamp, asset and interval query paths

## Freshness rules (market-aware, replacing the single 25-hour threshold)

- **Crypto quotes**: stale after ~15 minutes during market hours; stale after ~45 minutes outside market hours
- **Intraday scores**: stale when the expected completed market bucket plus processing grace is missing; closed-market scores remain current through the latest completed session and show `US market closed`
- **Historical scores**: stale if older than the last Tuesday/Friday recalculation window

## Asset universe and access

Expand catalogue to 20 stocks and 100 crypto assets. Add an explicit `access` field per asset: `free` or `holder`. Do not use array position to determine access level.

**Guest / unauthenticated**: 8 stocks + 30 crypto assets (current catalogue)
**Verified `$SynthEx` holder**: 20 stocks + 100 crypto assets

Enforce on the backend:
- Free asset endpoints may be publicly cached
- Holder endpoints require a valid authenticated session and current holder verification
- Direct requests to holder-only assets return `403 holder_required`
- Apply protection to asset detail, history, exposure and graph endpoints
- Never rely solely on hidden frontend links
- Never CDN-cache a private or personalised response

## Wallet authentication (SIWE)

Replace client-only balance gating with server-side SIWE / ERC-4361 authentication.

**Flow:**
1. User connects a compatible EVM wallet via Reown AppKit (MetaMask, Rabby, Trust, Coinbase, Rainbow, Robinhood Wallet, other WalletConnect wallets; Phantom only when EVM mode is confirmed working)
2. User switches to or adds Robinhood Chain — never silently fall back to Base (8453)
3. Backend creates a high-entropy, short-lived, single-use nonce
4. Wallet signs a human-readable SIWE message (no gas, no token approval, no blockchain transaction)
5. Backend verifies: address, signature, domain, URI, chain ID, nonce, issued-at, expiry
6. Backend consumes the nonce (replay protection)
7. Backend creates an opaque server-side session; store only the session-token hash in PostgreSQL
8. Session stored in a Secure, HttpOnly cookie via same-origin Next.js route handlers (BFF pattern)

**Session lifetime:** 30 days. Require a new signature when session expires, user logs out, connected wallet changes, or session is revoked.

**BFF pattern:** browser → Next.js route handlers (same origin, HttpOnly cookie) → Render API (Authorization header). Never store session tokens in localStorage.

**Wallet switching:** each wallet address is a separate account. Switching the connected address ends the active session. The new wallet must authenticate separately; entitlements do not transfer.

**New database models:** `auth_nonces`, `sessions`, `wallet_users`

**New API endpoints:** `POST /api/v1/auth/nonce`, `POST /api/v1/auth/verify`, `GET /api/v1/auth/session`, `POST /api/v1/auth/logout`

## Header `$SynthEx` balance

After login, show balance beside the shortened address: `12,450 SynthEx · 0x82F…91C`

Refresh: after login, on wallet change, after purchase verification, every 5 minutes while the tab is visible. Do not query the RPC on every route change. Cache server-side balance result for ~5 minutes. If the token contract is unconfigured, show an unavailable state — never a false zero.

## Portfolio tiers

Server-side tier enforcement based on verified cumulative USD purchase value (stored in integer cents or PostgreSQL Decimal):

| Cumulative verified purchase | Access |
|---|---|
| Under $50 | Locked — show "Buy $SynthEx" button |
| $50–$249.99 | Portfolio exposure summary |
| $250–$999.99 | Detailed assets and sector exposure |
| $1,000+ | All detailed features; advanced graphs / history / alerts marked Coming Soon |

Tier boundary exactness: $49.99 → locked; $50.00 → summary; $250.00 → detailed; $1,000.00 → highest.

The `$1,000+` tier must deliver all working `$250+` features. Only unreleased capabilities (advanced graphs, longer portfolio history, alerts) show Coming Soon.

**New database models:** `wallet_entitlements`, `claimed_purchase_transactions`, `cached_wallet_balances`

Portfolio exposure formula: `Σ(asset portfolio weight × signed asset Exposure Score)`

Calculate historical and intraday portfolio exposure separately.

## `$SynthEx/ETH` purchase verification

Expected trading pair: `$SynthEx/ETH` (not USDC).

The user submits a transaction hash. Backend (server-only RPC, never exposed to frontend) verifies:
- Authenticated wallet initiated the transaction
- Occurred on configured Robinhood Chain
- Transaction succeeded with required confirmations
- Official router/pool and official `$SynthEx` contract were used
- Wallet received `$SynthEx`; net ETH/WETH spent determined (refunds excluded)
- Transaction not previously claimed

**ETH/USD valuation:** use ETH/USD price at the transaction block time — not today's price. Read block timestamp, look up nearest stored ETH/USD observation (with acceptable timestamp distance), fall back to CoinGecko historical range, cache result by time bucket.

**Store per claim:** tx hash, block number, block timestamp, ETH/WETH spent, ETH/USD price used, ETH/USD source timestamp, calculated USD value, `$SynthEx` received (raw units), router/pool address, verification timestamp.

**Tier stability:** passive price appreciation does not upgrade access. A price decrease does not downgrade access. Selling below the recorded required token quantity locks portfolio access; restoring it restores access. Another verified purchase is required to upgrade tier.

Until real contracts are deployed: keep all contract values configurable, implement mocked receipt tests, fail closed in production, show "Purchase verification is not configured yet". No production bypass.

**New API endpoints:** `POST /api/v1/entitlements/verify-purchase`, `GET /api/v1/entitlements/status`, `POST /api/v1/entitlements/refresh`

## Robinhood Chain configuration

All Robinhood Chain values must be supplied through environment variables. Do not hardcode the chain ID, RPC URL, router address, pool address, WETH address or token contract in source code. Until these are supplied, the system must fail closed with a clear unavailable state. Base (chain ID 8453) must never be silently used as a production fallback — it is only the current placeholder in the existing frontend `Web3Provider`.

## Cloudflare cron schedule (three job types)

Replace current two-trigger routing with three distinct job types:

1. **Quote scheduler** (`*/5 * * * *`): fetch CoinGecko every 5 min during market hours, every 30 min outside; upsert quotes and timestamped observations
2. **Intraday score scheduler** (after each completed 30-min market bucket): ingest Marketstack candles, close crypto candles, recompute intraday scores; skip when market is closed except for the final closing calculation
3. **Historical scheduler** (`0 23 * * 2,5` — Tuesday/Friday after market close): refresh aligned historical data and recompute historical scores

Preserve: `CRON_SECRET`, advisory locks, idempotency, provider retry handling, existing data on failure, structured job-result responses.

## Environment variables — target additions

### Backend

| Variable | Purpose |
|---|---|
| `SYNTHEX_CHAIN_ID` | Robinhood Chain ID (replaces `delta_chain_id`) |
| `SYNTHEX_TOKEN_ADDRESS` | `$SynthEx` ERC-20 contract |
| `SYNTHEX_TOKEN_DECIMALS` | Token decimal places |
| `SYNTHEX_HOLDER_MIN_BALANCE_RAW` | Minimum raw token units for holder access |
| `ROBINHOOD_RPC_URL` | Server-only RPC — never exposed to frontend |
| `SYNTHEX_DEX_ROUTER_ADDRESSES` | Comma-separated valid router addresses |
| `SYNTHEX_DEX_POOL_ADDRESSES` | Comma-separated valid pool addresses |
| `SYNTHEX_WETH_ADDRESS` | WETH contract on Robinhood Chain |
| `SYNTHEX_MIN_CONFIRMATIONS` | Required block confirmations for purchase verification |
| `CORS_ORIGINS` | Comma-separated allowed origins (unchanged) |
| `PORTFOLIO_CHAIN_IDS` | Chains enabled for portfolio reads |
| `ETHEREUM_RPC_URL` | Optional — only required if Ethereum portfolio enabled |
| `BASE_RPC_URL` | Optional — only required if Base portfolio enabled |

### Frontend

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_SYNTHEX_CHAIN_ID` | Chain for wallet prompts (replaces `NEXT_PUBLIC_CHAIN_ID`) |
| `NEXT_PUBLIC_SYNTHEX_TOKEN_ADDRESS` | ERC-20 for balance display (replaces `NEXT_PUBLIC_DELTA_TOKEN_ADDRESS`) |
| `NEXT_PUBLIC_SYNTHEX_BUY_URL` | DEX buy link (replaces `NEXT_PUBLIC_DEX_BUY_URL`) |
| `BACKEND_API_URL` | Server-only Vercel variable — public Render API origin used by Next.js route handlers (BFF). Vercel cannot reach a Render private/internal URL; this must be the public HTTPS origin. Not `NEXT_PUBLIC_` — never exposed to the browser. |

`NEXT_PUBLIC_API_BASE_URL` remains for public endpoints fetched directly by the browser (asset lists, public chart data). Authenticated or entitlement-specific requests go through Next.js route handlers using `BACKEND_API_URL`.

Public `NEXT_PUBLIC_*` contract addresses are used for display and wallet prompts only. They are not authoritative — all access decisions are enforced server-side.

## Wallet states (frontend)

The UI must handle all of the following:

1. Disconnected → Connect Wallet
2. Connected, wrong chain → Switch to Robinhood Chain
3. Connected, correct chain, not authenticated → Sign In With Wallet
4. Authenticated, no `$SynthEx` → 8 stocks + 30 crypto; Buy `$SynthEx`
5. Authenticated holder, portfolio under $50 → 20 stocks + 100 crypto; portfolio locked
6. Verified $50 tier → portfolio exposure summary
7. Verified $250 tier → detailed analysis
8. Verified $1,000 tier → detailed analysis + Coming Soon labels on advanced features
9. Insufficient current token balance → access suspended; show required vs current balance
10. Missing production contract config → clear unavailable state; never show false zero or fake success

## Five-day prelaunch credit budget

| Provider | Expected five-day total |
|---|---|
| Marketstack intraday (20 stocks) | ~1,300 credits |
| Marketstack history/backfill | ~20–40 credits |
| CoinGecko batch quote requests | ~565 |
| CoinGecko history (100 assets) | ~100–200 |
| CoinGecko safety allowance | ~135 |
| **CoinGecko target total** | **< 1,000** |

Add structured provider-usage logging to compare actual vs estimated usage. Do not log API keys.
