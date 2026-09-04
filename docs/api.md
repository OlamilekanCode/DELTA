# DELTA API Reference

> Base URL: `/api/v1` | Updated: Milestone 0 — Placeholder. Expand in Milestone 2.

All endpoints are versioned under `/api/v1`. Responses use ISO 8601 UTC timestamps. Every response includes `is_demo: boolean` to indicate whether fixture data is being returned.

## Health

### `GET /api/v1/health`

Returns service status. Used as the Railway health-check endpoint.

```json
{
  "status": "ok",
  "milestone": "placeholder",
  "timestamp": "2026-09-04T00:00:00Z"
}
```

---

## Public endpoints (Milestone 2+)

### `GET /api/v1/assets/search?q={query}`

Search supported stocks and crypto assets.

### `GET /api/v1/assets/{symbol}`

Asset identity, current price, data source, and freshness.

### `GET /api/v1/assets/{symbol}/history?range=90d`

Historical daily price data for the specified range.

### `GET /api/v1/exposures/{symbol}?window=90&limit=20`

Exposure Scores for the top related crypto assets. Returns pre-computed results; never recalculates on request.

### `GET /api/v1/graphs/{symbol}?window=90&depth=1`

Graph data (nodes + edges) for the specified stock. Depth 1 is public; depth 2+ requires a token-gated session.

### `GET /api/v1/methodology`

Returns the current model version, description, and data source metadata.

---

## Authentication (Milestone 4+)

### `POST /api/v1/auth/nonce`

Issue a backend-signed SIWE nonce for the provided wallet address.

### `POST /api/v1/auth/verify`

Verify a signed SIWE message and create an authenticated session.

### `POST /api/v1/auth/logout`

Invalidate the current session.

### `GET /api/v1/access`

Return the current session's access level and `$DELTA` balance.

### `POST /api/v1/access/refresh`

Re-check the on-chain balance and update the access level.

---

## Token-gated endpoints (Milestone 4+)

### `GET /api/v1/graphs/{symbol}?depth=2`

Full graph data including depth-2 nodes. Requires authenticated session with sufficient `$DELTA` balance.

### `POST /api/v1/portfolio/analyze`

Analyze the connected wallet's read-only on-chain holdings and return category + stock exposure summary.

---

## Response conventions

```typescript
// Success
{
  "data": { ... },
  "is_demo": false,
  "data_source": "marketstack",
  "freshness": "2026-09-04T20:15:00Z"
}

// Error
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Asset UNKNOWN not found in supported list"
  }
}
```

## Rate limits

Applied per IP (public) and per wallet address (authenticated). Exact limits are configured at the API gateway layer and documented in `docs/architecture.md` after Milestone 6.
