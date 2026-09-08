import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.purchase_verification import verify_purchase


@pytest.mark.asyncio
async def test_verify_purchase_fails_closed_when_unconfigured(db: AsyncSession) -> None:
    """Default test settings have no chain/RPC/token configured."""
    result = await verify_purchase(db, "0x" + "1" * 40, "0x" + "a" * 64)
    assert result["status"] == "not_configured"
    assert result["message"] == "Purchase verification is not configured yet"


@pytest.mark.asyncio
async def test_verify_purchase_never_returns_verified_without_config(db: AsyncSession) -> None:
    result = await verify_purchase(db, "0x" + "2" * 40, "0x" + "b" * 64)
    assert result["status"] != "verified"
