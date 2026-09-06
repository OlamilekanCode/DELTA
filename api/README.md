# DELTA — Synthetic Exposure API

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

# Downgrade one step (for testing)
alembic downgrade -1

# Create a new migration after model changes
alembic revision --autogenerate -m "description"
```

## Data ingestion commands

```bash
# Initial 90-day backfill for all 38 assets
python -m app.ingestion.commands backfill

# Refresh current crypto prices via CoinGecko /coins/markets (1 request, all 30 crypto)
python -m app.ingestion.commands refresh-crypto-quotes

# Refresh 90-day OHLCV history for all 30 crypto assets
python -m app.ingestion.commands refresh-crypto-history

# Refresh stock EOD prices via Marketstack (weekdays only)
python -m app.ingestion.commands refresh-stock-eod

# Recompute and store Exposure Scores for all stock × crypto pairs
python -m app.ingestion.commands recompute-scores

# Combined: stock EOD + crypto history + score recomputation
python -m app.ingestion.commands refresh-all
```

With `USE_DEMO_DATA=false`, both `MARKETSTACK_API_KEY` and `COINGECKO_API_KEY` must be set. Commands exit with a clear error if either key is missing.

All commands are idempotent. On provider failure, existing stored data is preserved and the error is logged.

## Protected cron endpoints

Two HTTP endpoints are used by the Cloudflare Cron scheduler. Every request must include the header `X-Cron-Secret: <CRON_SECRET>`.

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/cron/refresh-crypto-quotes` | Current crypto prices — every 5 minutes |
| `POST` | `/api/v1/cron/refresh-history-and-scores` | OHLCV history + score recompute — Tuesday and Friday |

Responses:
```json
{ "ok": true, "command": "refresh-crypto-quotes" }
{ "ok": false, "skipped": true, "message": "Job is already running on another instance" }
```

Returns `401 Unauthorized` if the secret is missing or incorrect.

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

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Service health |
| `GET` | `/api/v1/assets` | All assets, optional `?type=stock\|crypto` |
| `GET` | `/api/v1/assets/search` | Search by `?q=` and optional `?type=` |
| `GET` | `/api/v1/assets/{symbol}` | Single asset with latest price |
| `GET` | `/api/v1/assets/{symbol}/history` | Daily price history, `?days=7–365` |
| `GET` | `/api/v1/correlation/{symbol}` | Pearson scores for a stock vs all crypto |
| `GET` | `/api/v1/exposures/{symbol}` | Stored Exposure Scores for a stock |
| `GET` | `/api/v1/graphs/{symbol}` | Graph nodes and edges for the Exposure Graph |
| `POST` | `/api/v1/cron/refresh-crypto-quotes` | Trigger crypto quote refresh (requires `X-Cron-Secret`) |
| `POST` | `/api/v1/cron/refresh-history-and-scores` | Trigger history + score refresh (requires `X-Cron-Secret`) |

## Deployment (Render)

```bash
# Build command
pip install -r requirements.txt

# Pre-deploy / start command (run migrate before starting)
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set all secrets in Render's environment panel. Never commit `.env` files with real values.

### Scheduler — Cloudflare Cron

Configure two HTTP triggers pointing at the Render URL:

| Schedule | Endpoint | Header |
|----------|----------|--------|
| Every 5 minutes | `POST /api/v1/cron/refresh-crypto-quotes` | `X-Cron-Secret: <value>` |
| Tuesday + Friday | `POST /api/v1/cron/refresh-history-and-scores` | `X-Cron-Secret: <value>` |

Set the same `CRON_SECRET` value in both the Render environment and the Cloudflare Cron HTTP trigger header.
