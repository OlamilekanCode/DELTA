# DELTA API

> **Milestone 0 placeholder.** Real FastAPI implementation begins in Milestone 2.

## Current state

The `api/` directory holds a minimal FastAPI application with a single `/api/v1/health` endpoint. This exists to:
- Confirm the service structure before the frontend needs it
- Provide a deployable Railway service configuration
- Keep the repository runnable from day one

## Setup (for development)

```bash
# Requires Python 3.12+
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: http://localhost:8000/api/v1/health

## What's coming in Milestone 2

- PostgreSQL database (SQLAlchemy 2 async + Alembic migrations)
- Marketstack provider integration (stock historical data)
- CoinGecko provider integration (crypto historical data)
- Asset seeding and price ingestion jobs
- Real `/assets/*` and `/exposures/*` endpoints
- Structured logging and error handling

## Dependencies

Milestone 0–1: `fastapi` and `uvicorn` only.

Milestone 2+ will add: `sqlalchemy`, `alembic`, `asyncpg`, `httpx`, `pydantic`, `polars`, `numpy`, `scipy`, and others. Do not add these until Milestone 2.

## Deployment (Railway)

See `docs/architecture.md` and the root `README.md` for the full Railway deployment configuration.

Build command: `pip install -r requirements.txt`
Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
