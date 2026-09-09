from datetime import datetime

import pytest
from httpx import AsyncClient

from app.services.market_calendar import get_market_status


@pytest.mark.asyncio
async def test_market_status_endpoint_schema(client: AsyncClient) -> None:
    r = await client.get("/api/v1/market-status")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["is_open"], bool)
    assert body["timezone"] == "America/New_York"
    assert body["last_close"]
    assert body["next_open"]
    assert "status_reason" in body
    if body["is_open"]:
        assert body["current_bucket"] is not None
    else:
        assert body["current_bucket"] is None


def test_market_open_during_regular_hours() -> None:
    # Wednesday 2026-09-09 15:00 UTC = 11:00 ET, well within 9:30-16:00 ET.
    status = get_market_status(datetime.fromisoformat("2026-09-09T15:00:00+00:00"))
    assert status.is_open is True
    assert status.status_reason == "regular trading hours"
    assert status.current_bucket is not None
    assert status.current_bucket.minute in (0, 30)


def test_market_closed_on_weekend() -> None:
    # Saturday 2026-09-12.
    status = get_market_status(datetime.fromisoformat("2026-09-12T15:00:00+00:00"))
    assert status.is_open is False
    assert status.current_bucket is None
    assert status.status_reason == "market holiday or weekend"


def test_market_closed_on_holiday() -> None:
    # Christmas Day 2026 (Friday) is a full NYSE holiday.
    status = get_market_status(datetime.fromisoformat("2026-12-25T16:00:00+00:00"))
    assert status.is_open is False
    assert status.status_reason == "market holiday or weekend"


def test_market_closed_after_hours() -> None:
    # Wednesday 2026-09-09 22:00 UTC = 18:00 ET, after the 16:00 ET close.
    status = get_market_status(datetime.fromisoformat("2026-09-09T22:00:00+00:00"))
    assert status.is_open is False
    assert status.status_reason == "outside regular trading hours"
