# DELTA API

FastAPI backend providing asset data, price history, and stock↔crypto Exposure Scores.

## Stack

- **FastAPI** with async lifespan, CORS middleware
- **SQLAlchemy 2** async engine (`asyncpg` for PostgreSQL, `aiosqlite` for tests)
- **Alembic** migrations
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
# Edit .env — set DATABASE_URL, API keys, etc.

# Apply database migrations
alembic upgrade head

# Start the dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: http://localhost:8000/api/v1/health

With `USE_DEMO_DATA=true` (default), the server seeds deterministic fixture data on startup. No API keys or database needed beyond the default SQLite file.

## Database migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "description"
```

## Data ingestion

```bash
# Initial 90-day backfill for all 38 assets
python -m app.ingestion.commands backfill

# Refresh current crypto prices via CoinGecko /coins/markets (1 request, all assets)
python -m app.ingestion.commands refresh-crypto-quotes

# Refresh stock EOD prices via Marketstack (weekdays only)
python -m app.ingestion.commands refresh-stock-eod

# Recompute and store Exposure Scores for all stock × crypto pairs
python -m app.ingestion.commands recompute-scores
```

With `USE_DEMO_DATA=false`, both `MARKETSTACK_API_KEY` and `COINGECKO_API_KEY` must be set. The commands exit with a clear error if either key is missing.

## Running tests

```bash
pytest tests/ -v
```

Tests use SQLite in-memory and `pytest-httpx` to mock all external HTTP calls. No API keys or network access required.

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

### Notes

- `/assets/search` must be registered before `/assets/{symbol}` in FastAPI to prevent "search" being matched as a symbol.
- `/exposures/{symbol}` populates stored scores on first request if none exist, then serves from cache. Scores are flagged stale after 25 hours.
- The `demo` field in all responses reflects `is_demo` on the actual stored price rows, not just the `USE_DEMO_DATA` env var.
- Correlation `days` is capped at 90 to match ingestion depth.

## Deployment (Railway)

```bash
# Build
pip install -r requirements.txt

# Migrate (run once after each deploy)
alembic upgrade head

# Start
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Scheduled cron jobs (Railway):

```bash
python -m app.ingestion.commands refresh-crypto-quotes   # hourly
python -m app.ingestion.commands refresh-stock-eod       # daily, weekdays
python -m app.ingestion.commands recompute-scores        # daily
```

Set all secrets in Railway's environment panel. Never commit `.env` files with real values.
