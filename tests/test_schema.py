"""
tests/test_schema.py
Ensures Fly Postgres has every column the bot relies on.
Skips automatically when DATABASE_URL is not set (e.g. local dev box).
"""

import os, pytest, asyncpg

DATABASE_URL = os.getenv("DATABASE_URL")

# ── skip locally if env var absent ───────────────────────────
if not DATABASE_URL:
    pytest.skip(
        "DATABASE_URL not set; skipping schema test", allow_module_level=True
    )

# ── required columns per table ───────────────────────────────
_REQUIRED = {
    "users": {
        "id", "username", "xp", "streak",
        "is_premium", "last_seen", "last_scored",
    },
    "submissions": {
        "id", "user_id", "kind", "type",
        "band", "tips", "word_count",
        "seconds", "created_at",
    },
}

@pytest.mark.asyncio
async def test_required_columns_exist():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        for table, expected in _REQUIRED.items():
            rows = await conn.fetch(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = $1
                """,
                table,
            )
            present = {r["column_name"] for r in rows}
            missing = expected - present
            assert not missing, f"{table} missing columns: {', '.join(sorted(missing))}"
    finally:
        await conn.close()
