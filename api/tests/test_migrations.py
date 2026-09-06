"""Tests that Alembic migrations run cleanly on a fresh SQLite database.

These are synchronous subprocess tests — they invoke `alembic` exactly as a
developer would from the command line, using a throwaway database file.
"""

import os
import subprocess
import tempfile
from pathlib import Path

_API_DIR = Path(__file__).parent.parent


def _alembic(args: list[str], db_url: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python", "-m", "alembic", *args],
        capture_output=True,
        text=True,
        cwd=str(_API_DIR),
        env={**os.environ, "DATABASE_URL": db_url},
    )


def test_migrate_round_trip() -> None:
    """Upgrade from empty DB to head, downgrade -1, then re-upgrade to head."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    db_url = f"sqlite+aiosqlite:///{db_path}"

    try:
        result = _alembic(["upgrade", "head"], db_url)
        assert result.returncode == 0, (
            f"alembic upgrade head failed:\n{result.stdout}\n{result.stderr}"
        )

        result = _alembic(["downgrade", "-1"], db_url)
        assert result.returncode == 0, (
            f"alembic downgrade -1 failed:\n{result.stdout}\n{result.stderr}"
        )

        result = _alembic(["upgrade", "head"], db_url)
        assert result.returncode == 0, (
            f"alembic re-upgrade to head failed:\n{result.stdout}\n{result.stderr}"
        )
    finally:
        db_path.unlink(missing_ok=True)


def test_migrate_from_base_to_head() -> None:
    """Verify all four migrations apply cleanly from an empty database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    db_url = f"sqlite+aiosqlite:///{db_path}"

    try:
        result = _alembic(["upgrade", "head"], db_url)
        assert result.returncode == 0, (
            f"upgrade from base to head failed:\n{result.stdout}\n{result.stderr}"
        )

        # Verify current revision matches head
        result = _alembic(["current"], db_url)
        assert result.returncode == 0
        assert "0004" in result.stdout, (
            f"Expected revision 0004 to be current, got:\n{result.stdout}"
        )
    finally:
        db_path.unlink(missing_ok=True)
