# Synthetic Exposure — API Reference

**Base URL**: `/api/v1`

All endpoints are versioned under `/api/v1`. Field names use `snake_case`. The `is_demo`/`demo` field in every response indicates whether fixture data was returned (`USE_DEMO_DATA=true`).

Authenticated requests send `Authorization: Bearer <session_token>`. The token is issued by `POST /auth/verify` and never exposed to browser JavaScript — see the BFF pattern in `docs/architecture.md`.

---

## Access model

Two catalogue tiers:

- **Guest / non-holder**: 8 free stocks + 30 free crypto assets.
- **Verified `$SynthEx` holder**: 20 stocks + 100 crypto assets.

Every endpoint that serves asset rows filters by access level at the database-query level. Requesting a holder-only stock (`{symbol}` path parameter) returns:

- `401` with `{"detail": "authentication_required"}` when there is no session at all.
- `403` with `{"detail": "holder_required"}` when the session is authenticated but not a verified holder.

List/search/exposure/graph/correlation/intraday endpoints instead silently restrict which rows are returned — a guest never sees holder-only symbols in a list, and never sees a holder-only crypto asset inside a free stock's exposure/graph/intraday results.

---

## Health

### `GET /health`

```json
{ "status": "ok", "timestamp": "2026-09-08T12:00:00Z" }
```

---

## Assets

### `GET /assets`

Returns the caller's accessible assets (38 for a guest, 120 for a verified holder) with latest price data. Query: `type=stock|crypto`.

### `GET /assets/search`

Search by symbol, name or category, filtered to the caller's access tier. Query: `q=string`, `type=stock|crypto`.

### `GET /assets/{symbol}`

Single asset with latest price and quote data. `401`/`403` per the access model above for a holder-only symbol.

**Crypto** — price comes from `asset_quotes`. Includes `change_24h_pct`, `market_cap_usd`, `volume_24h_usd`, `quote_ts`, `quote_provider`.
**Stock** — price comes from `daily_prices` (Marketstack EOD). Quote fields are `null`.

### `GET /assets/{symbol}/history`

Price history. Query: `days=7–365` (default 90), or `range=4H|1D|1W|1M|3M|1Y` (4H/1D/1W/1M read stored 30-minute candles; 3M/1Y read stored daily prices). Returns `collecting_data: true` when a selected intraday range hasn't accumulated enough observations yet — never a partial/misleading result.

### Asset schema

```typescript
interface AssetOut {
  symbol: string;
  name: string;
  category: string;
  asset_type: "stock" | "crypto";
  access: "free" | "holder";
  coingecko_id: string | null;
  last_price: number | null;
  last_price_date: string | null;
  is_demo: boolean | null;
  change_24h_pct: number | null;    // crypto only
  market_cap_usd: number | null;    // crypto only
  volume_24h_usd: number | null;    // crypto only
  quote_ts: string | null;          // crypto only
  quote_provider: string | null;    // crypto only
}
```

---

## Exposures (historical, 90-day)

### `GET /exposures/{symbol}`

Pre-computed, stored signed Exposure Scores (`[-1.00, +1.00]`) for a stock. Never computed inside the request — reads `stored_exposure_scores` only.

```typescript
interface ExposuresResult {
  stock: { symbol: string; name: string };
  scores: {
    symbol: string; name: string; category: string;
    score: number; raw_correlation: number; observations: number;
    data_quality: string | null; data_ts: string | null;
  }[];
  computed_at: string | null;
  stale: boolean;   // market-aware: compares against the last Tue/Fri recalculation deadline
  demo: boolean;
  model_version: string;
  window_days: number;
}
```

### `GET /correlation/{symbol}` — deprecated alias

Kept for backward compatibility. Reads the same stored data as `/exposures` (plus normalized price series for charting) rather than recomputing anything on request.

---

## Live Exposure (intraday, 30-minute)

### `GET /intraday/{symbol}`

Reads the latest stored 30-minute Exposure Scores only — never computes a score inside the request. While the market is open, scores refresh after each completed bucket; while closed, the last valid score is preserved and `freshness: "market_closed"` is returned instead of stale.

```typescript
interface IntradayResult {
  stock: { symbol: string; name: string };
  status: "ready" | "collecting_data";
  scores: { symbol: string; name: string; category: string; score: number; observations: number }[];
  interval: "30m";
  sessions_used: number;
  demo: boolean;
  current_count: number | null;
  required_count: number | null;
  estimated_ready: string | null;
  data_ts: string | null;            // the real stored score timestamp, not the theoretical close
  freshness: "fresh" | "stale" | "collecting_data" | "market_closed" | null;
  market_is_open: boolean | null;
  next_market_open: string | null;
}
```

---

## Graphs

### `GET /graphs/{symbol}`

Graph nodes/edges for the Exposure Graph, filtered to the caller's access tier, up to 12 crypto nodes. Query: `min_score=0.0–1.0` (filters on `abs(score)`, so inverse relationships aren't dropped).

```typescript
interface GraphResult {
  stock: { symbol: string; name: string };
  nodes: { id: string; symbol: string; name: string; category: string; score: number | null; is_center: boolean }[];
  edges: { source: string; target: string; weight: number; score: number; direction: "positive" | "inverse" }[];
  demo: boolean;
  computed_at: string | null;
}
```

---

## Market status

### `GET /market-status`

```json
{
  "is_open": false,
  "timezone": "America/New_York",
  "last_close": "2026-09-08T20:00:00Z",
  "next_open": "2026-09-09T13:30:00Z",
  "current_bucket": null,
  "status_reason": "market holiday or weekend"
}
```

---

## Auth (SIWE)

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `/auth/nonce` | Issues a short-lived, single-use nonce. Rate-limited per IP. |
| `POST` | `/auth/verify` | Body `{message, signature}`. Validates the full SIWE structure, verifies the signature, atomically consumes the nonce, creates a session. `503 chain_not_configured` if `SYNTHEX_CHAIN_ID` is unset. Rate-limited per IP. |
| `GET` | `/auth/session` | `{wallet_address, authenticated}` for the caller's bearer token. |
| `POST` | `/auth/logout` | Revokes the session tied to the bearer token. |

---

## Entitlements

All require authentication (`401` without a session).

| Method | Path | Notes |
|--------|------|-------|
| `GET` | `/entitlements/status` | `{tier, cumulative_usd, is_holder, synthex_balance, synthex_balance_raw, synthex_balance_checked_at}`. Reads cache only. |
| `POST` | `/entitlements/refresh` | Triggers an on-chain balance read and cache update. `{"status": "not_configured", ...}` until Robinhood Chain is fully configured. |
| `POST` | `/entitlements/verify-purchase` | Body `{tx_hash}`. Verifies a `$SynthEx`/ETH purchase and updates the wallet's tier. `{"status": "not_configured", ...}` until router/pool/token/RPC config is supplied. |

---

## Portfolio

All require authentication.

| Method | Path | Notes |
|--------|------|-------|
| `GET` | `/portfolio/exposure` | Query `stock=SYMBOL` for a single stock, or omitted for a ranked summary across every stock with data. `status: "suspended"` when the verified tier is retained but the current `$SynthEx` balance has dropped below the holder threshold. Response separates `portfolio_exposure_score` (crypto correlation), `direct_exposure_usd`/`direct_holdings` (Robinhood Stock Token holdings — literal, not correlation-based) and `cash_usd`/`cash_holdings` (stablecoins — zero correlation, still counted in `total_usd_value`) — never blended into one figure. Rate-limited to 10 requests/minute per IP. |
| `POST` | `/portfolio/refresh` | Refreshes on-chain wallet positions from the verified contract catalogue (`portfolio_asset_contracts`), batched through Multicall3 where available. No-op (not an error) until at least one verified contract exists. Served from cache (no RPC call) when the wallet was refreshed within the last 30 seconds. Rate-limited to 10 requests/minute per IP. |

---

## Errors

```json
{ "detail": "Asset 'FAKEX' not found" }
```

| Code | Meaning |
|------|---------|
| `401` | No session (holder-only resource, or an entitlements/portfolio endpoint) |
| `403` | Authenticated but not a verified holder |
| `404` | Asset not found |
| `422` | Invalid query parameter |
| `429` | Rate limited (auth endpoints) |
| `503` | Chain/backend not configured |

---

## Cron endpoints

Protected endpoints called by the Cloudflare Worker. Every request must include `X-Cron-Secret: <CRON_SECRET>`. A genuine job failure (every provider call failed) returns a non-2xx status — never `200` with `ok: false`.

| Method | Path | Schedule |
|--------|------|----------|
| `POST` | `/cron/refresh-crypto-quotes` | Every 5 minutes |
| `POST` | `/cron/refresh-intraday` | 2 and 32 minutes past each hour |
| `POST` | `/cron/refresh-history-and-scores` | Tuesday and Friday, 23:00 UTC |

```json
{ "ok": true, "command": "refresh-crypto-quotes", "counts": { "requested": 30, "succeeded": 30, "skipped": 0, "failed": 0 } }
```
