# Synthetic Exposure API

FastAPI backend providing asset data, price history, and stock↔crypto Exposure Scores.

## Stack

- **FastAPI** with async lifespan, CORS middleware
- **SQLAlchemy 2** async engine (`asyncpg` for PostgreSQL, `aiosqlite` for tests)
- **Alembic** migrations (`render_as_batch=True` for SQLite compatibility)
- **NumPy** — Pearson correlation on aligned daily log returns
- **httpx + tenacity** — CoinGecko and Marketstack HTTP clients with retry/backoff
- **pytest + pytest-httpx** — async test suite with mocked HTTP

## Local setup

```bash
cd api
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp ../.env.example .env
# Edit .env — set DATABASE_URL, API keys, CRON_SECRET, etc.

# Apply database migrations
alembic upgrade head

# Start the dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: http://localhost:8000/api/v1/health

With `USE_DEMO_DATA=true` (default), the server seeds deterministic fixture data on startup. No API keys or external network access required.

## Database migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Downgrade one step — local/disposable databases only, never production
alembic downgrade -1

# Create a new migration after model changes
alembic revision --autogenerate -m "description"
```

## Data ingestion commands

```bash
python -m app.ingestion.commands backfill              # initial 365-day backfill, all assets (recurring refreshes stay at 90 days)
python -m app.ingestion.commands refresh-crypto-quotes  # 1 CoinGecko batch request, all crypto
python -m app.ingestion.commands refresh-crypto-history  # no CoinGecko batch endpoint for history — one request per crypto asset, bounded concurrency
python -m app.ingestion.commands refresh-stock-eod       # weekdays only
python -m app.ingestion.commands refresh-intraday        # batched Marketstack + stored crypto observations
python -m app.ingestion.commands recompute-scores
python -m app.ingestion.commands refresh-all             # stock EOD + crypto history + scores + cleanup
python -m app.ingestion.commands cleanup-old-data
```

With `USE_DEMO_DATA=false`, both `MARKETSTACK_API_KEY` and `COINGECKO_API_KEY` must be set. Commands exit with a clear error if either key is missing.

All commands are idempotent. On provider failure, existing stored data is preserved and the error is logged.

## Protected cron endpoints

Three HTTP endpoints are used by the Cloudflare Cron scheduler (see `cloudflare/`). Every request must include `X-Cron-Secret: <CRON_SECRET>`.

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/cron/refresh-crypto-quotes` | Current crypto prices + observations — every 5 minutes |
| `POST` | `/api/v1/cron/refresh-intraday` | 30-min candles + live Exposure Scores — 2 and 32 minutes past each hour |
| `POST` | `/api/v1/cron/refresh-history-and-scores` | History + historical scores + retention cleanup — Tuesday and Friday |

Responses:
```json
{ "ok": true, "command": "refresh-crypto-quotes", "counts": { "requested": 30, "succeeded": 30, "skipped": 0, "failed": 0 } }
{ "ok": false, "skipped": true, "message": "Job is already running on another instance" }
```

Returns `401 Unauthorized` if the secret is missing or incorrect. A genuine failure (every provider call failed) returns a non-2xx status, never `200` with `ok: false`.

## Running tests

```bash
pytest tests/ -v
```

Tests use SQLite and `pytest-httpx` to mock all external HTTP calls. No API keys or network access required.

## Linting

```bash
ruff check .
ruff check . --fix   # auto-fix import ordering and unused imports
```

## API endpoints

See `docs/api.md` for full request/response shapes, the access model (guest vs. verified holder), and error codes. Summary:

| Method | Path | Access |
|--------|------|--------|
| `GET` | `/api/v1/assets`, `/assets/search`, `/assets/{symbol}`, `/assets/{symbol}/history` | Filtered to caller's tier; `401`/`403` for a holder-only symbol |
| `GET` | `/api/v1/exposures/{symbol}`, `/graphs/{symbol}`, `/correlation/{symbol}` (deprecated alias), `/intraday/{symbol}` | Stored scores only — never computed on request |
| `GET` | `/api/v1/market-status` | Public |
| `POST` | `/api/v1/auth/nonce`, `/auth/verify` · `GET /auth/session` · `POST /auth/logout` | SIWE authentication |
| `GET`/`POST` | `/api/v1/entitlements/*`, `/portfolio/*` | Requires an authenticated session |
| `POST` | `/api/v1/cron/*` | Requires `X-Cron-Secret` |

## Deployment (Render)

```bash
# Build command
pip install -r requirements.txt

# Pre-deploy / start command (run migrate before starting)
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set all secrets in Render's environment panel. Never commit `.env` files with real values.

### Scheduler — Cloudflare Cron

Deployed from `cloudflare/` (see its `wrangler.toml`) — three triggers pointing at the Render URL:

| Schedule | Endpoint |
|----------|----------|
| Every 5 minutes | `POST /api/v1/cron/refresh-crypto-quotes` |
| 2, 32 minutes past each hour | `POST /api/v1/cron/refresh-intraday` |
| Tuesday + Friday, 23:00 UTC | `POST /api/v1/cron/refresh-history-and-scores` |

Set the same `CRON_SECRET` value in both the Render environment and the Cloudflare Worker secret.
