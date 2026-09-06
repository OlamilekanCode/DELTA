# DELTA — Synthetic Exposure API Reference

**Base URL**: `/api/v1`

All endpoints are versioned under `/api/v1`. Field names use `snake_case`. The `is_demo` or `demo` field in every response indicates whether fixture data was returned (`USE_DEMO_DATA=true`).

---

## Health

### `GET /api/v1/health`

Returns service status. Used as the Railway health-check endpoint.

```json
{ "status": "ok", "timestamp": "2026-09-06T12:00:00Z" }
```

---

## Assets

### `GET /api/v1/assets`

Returns all 38 assets (8 stocks + 30 crypto) with latest price data.

Query params:
- `type=stock|crypto` — filter by asset type

### `GET /api/v1/assets/search`

Search assets by symbol, name, or category.

Query params:
- `q=string` — search query (matches symbol, name, category)
- `type=stock|crypto` — optional type filter

### `GET /api/v1/assets/{symbol}`

Single asset with latest price and quote data.

**Crypto assets** — current price comes from `asset_quotes` (populated by `refresh-crypto-quotes`). Includes `change_24h_pct`, `market_cap_usd`, `volume_24h_usd`, `quote_ts`, `quote_provider`. Falls back to `DailyPrice` if no quote row exists.

**Stock assets** — price comes from `DailyPrice` (Marketstack EOD). Quote fields are `null`.

### `GET /api/v1/assets/{symbol}/history`

Daily price history for the given asset.

Query params:
- `days=7–365` (default: 90)

Response includes `prices: [{date, close}]`, `is_demo`, `provider`.

### Asset schema

```typescript
interface AssetOut {
  symbol: string;
  name: string;
  category: string;
  asset_type: "stock" | "crypto";
  coingecko_id: string | null;
  last_price: number | null;
  last_price_date: string | null;   // ISO date
  is_demo: boolean | null;
  // Populated for crypto only:
  change_24h_pct: number | null;
  market_cap_usd: number | null;
  volume_24h_usd: number | null;
  quote_ts: string | null;          // ISO 8601 UTC timestamp of quote
  quote_provider: string | null;   // "coingecko" | "fixture"
}
```

---

## Correlation

### `GET /api/v1/correlation/{symbol}`

Pearson correlation scores computed on request from stored `DailyPrice` rows.

Query params:
- `days=60–90` (default: 90)

Response: `CorrelationResult` with `scores: [ExposureScoreOut]`, `demo`, `computed_at`.

---

## Exposures

### `GET /api/v1/exposures/{symbol}`

Pre-computed stored Exposure Scores for the given stock.

On first request with no stored scores, scores are computed and written to `stored_exposure_scores`. Subsequent calls read from the table directly. Scores older than 25 hours are flagged `stale: true`.

Response: `ExposuresResult` with `stock`, `scores`, `computed_at`, `stale`, `demo`.

---

## Graphs

### `GET /api/v1/graphs/{symbol}`

Graph nodes and edges for the Exposure Graph. Returns up to 12 crypto nodes plus edges connecting them to the stock node.

Response: `GraphResult` with `nodes: [GraphNode]`, `edges: [GraphEdge]`, `demo`, `computed_at`.

---

## Errors

FastAPI returns standard HTTP error responses:

```json
{ "detail": "Asset 'FAKEX' not found" }
```

| Code | Meaning |
|------|---------|
| `404` | Asset not found |
| `422` | Invalid query parameter (Pydantic validation failure) |
| `500` | Unexpected server error |

---

## Cron endpoints

Protected endpoints called by the Cloudflare Cron scheduler. Every request must include `X-Cron-Secret: <CRON_SECRET>`.

### `POST /api/v1/cron/refresh-crypto-quotes`

Refreshes current crypto prices for all 30 assets from CoinGecko `/coins/markets`. Runs every 5 minutes in production.

With `USE_DEMO_DATA=true`, the command logs a skip message and returns immediately.

```json
{ "ok": true, "command": "refresh-crypto-quotes" }
```

If another instance of the same job is already running (PostgreSQL advisory lock held):

```json
{ "ok": false, "skipped": true, "message": "Job 'refresh-crypto-quotes' is already running on another instance" }
```

Returns `401 Unauthorized` if `X-Cron-Secret` is missing, empty, or incorrect.

### `POST /api/v1/cron/refresh-history-and-scores`

Runs stock EOD refresh, then 90-day crypto OHLCV history refresh, then recomputes all Exposure Scores. Intended to run Tuesday and Friday.

```json
{ "ok": true, "command": "refresh-history-and-scores" }
```

Same `401` / advisory-lock skip behaviour as above.

---

## Not implemented

The following are not implemented and have no planned delivery date:

- `/api/v1/auth/*` — SIWE wallet authentication
- `/api/v1/access` — session-based access level
- `/api/v1/portfolio/*` — portfolio exposure analysis

Portfolio analysis requires backend session verification and is planned for a future release.
