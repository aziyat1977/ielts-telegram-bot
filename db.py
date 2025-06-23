# db.py
import os, asyncpg, datetime as dt
from contextlib import asynccontextmanager
from aiogram.types import User


# ── connection pool ──────────────────────────────────────────────
@asynccontextmanager
async def get_pool():
    pool = await asyncpg.create_pool(
        os.getenv("DATABASE_URL"),
        min_size=1,
        max_size=5,
        init=init_conn,
    )
    try:
        yield pool
    finally:
        await pool.close()


async def init_conn(conn):
    # make every timestamp zone-aware & get rows as dict-like objects
    await conn.set_type_codec(
        "jsonb", encoder=lambda v: v, decoder=lambda v: v, schema="pg_catalog"
    )


# ── helpers ──────────────────────────────────────────────────────
async def upsert_user(pool: asyncpg.Pool, tg: User):
    """Insert (or update username/last_seen) before every command."""
    await pool.execute(
        """
        INSERT INTO users (id, username)
        VALUES ($1, $2)
        ON CONFLICT (id) DO
          UPDATE SET username = EXCLUDED.username,
                     last_seen = now()
        """,
        tg.id,
        tg.username,
    )


async def save_submission(
    pool: asyncpg.Pool,
    tg: User,
    sub_type: str,
    band: float,
    tips: dict,
    *,
    word_count: int | None = None,
    seconds: int | None = None,
):
    xp_gain = int(band * 10)

    async with pool.acquire() as conn, conn.transaction():
        # 1) store the submission
        await conn.execute(
            """
            INSERT INTO submissions
                  (user_id, type, band, tips, word_count, seconds)
            VALUES ($1,      $2,   $3,   $4,  $5,        $6)
            """,
            tg.id,
            sub_type,
            band,
            tips,
            word_count,
            seconds,
        )

        # 2) update XP & streak atomically
        await conn.execute(
            """
            UPDATE users
               SET xp          = xp + $2,
                   streak      = CASE
                                   WHEN date_trunc('day', last_scored)
                                        = date_trunc('day', now()) - interval '1 day'
                                   THEN streak + 1
                                   ELSE 1
                                 END,
                   last_scored = now()
             WHERE id = $1
            """,
            tg.id,
            xp_gain,
        )
