# DELTA API

FastAPI backend providing asset data and stock↔crypto correlation scores.

## Stack

- **FastAPI** with async lifespan, CORS middleware
- **SQLAlchemy 2** async engine (`asyncpg` for PostgreSQL, `aiosqlite` for tests)
- **Alembic** migrations (run `alembic upgrade head` before first start)
- **NumPy** — Pearson correlation on aligned daily log returns
- **httpx + tenacity** — CoinGecko and Marketstack providers with retry/backoff
- **pytest + pytest-httpx** — async test suite with mocked HTTP providers

## Local setup

```bash
# Requires Python 3.12+
cd api
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp ../.env.example .env
# Edit .env — set DATABASE_URL, API keys, etc.

# Apply database migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: http://localhost:8000/api/v1/health

## Running ingestion

Seeds the asset catalogue and fetches price history from providers:

```bash
python -m app.ingestion.runner
```

- `USE_DEMO_DATA=true` (default) — uses deterministic fixture data, no API keys required.
- `USE_DEMO_DATA=false` — requires both `MARKETSTACK_API_KEY` (stocks) and `COINGECKO_API_KEY` (crypto). Exits with a clear error if either key is absent. Never mixes fixture and real providers in one run.

## Running tests

```bash
pytest tests/ -v
```

Tests use SQLite and `pytest-httpx` to mock all external HTTP calls. No API keys or network access required.

## Linting

```bash
ruff check .
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Service health check |
| `GET` | `/api/v1/assets` | List all assets (optional `?type=stock\|crypto`) |
| `GET` | `/api/v1/correlation/{symbol}` | Correlation scores for a stock vs all crypto assets |

### Correlation query params

| Param | Default | Range | Description |
|-------|---------|-------|-------------|
| `days` | `90` | 60–90 | Lookback window in calendar days. Capped at 90 to match ingestion depth. |

The `demo` field in the response reflects `is_demo` on the actual stored price rows — not just the `USE_DEMO_DATA` env var.

## Deployment (Railway)

```bash
# Build
pip install -r requirements.txt

# Migrate (run once after deploy)
alembic upgrade head

# Start
uvicorn app.main:app --host 0.0.0.0 --port $PORT

# Scheduled ingestion (Railway cron job)
python -m app.ingestion.runner
```

Set all environment variables in Railway's environment panel — never commit `.env` files with real secrets.
