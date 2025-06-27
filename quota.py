# quota.py — Telegram Stars pay-wall middleware
#
# Keeps the first N scorings free, then offers a one-time ⭐ unlock.
# Requires *no* external payment provider: just pass provider_token="STARS".

import os
from aiogram import BaseMiddleware
from aiogram.types import Message

from db import get_pool                   # fresh pool every call

FREE_LIMIT  = int(os.getenv("PAYWALL_FREE_LIMIT", 5))   # first N scores are free
PRICE_STARS = int(os.getenv("PRICE_STARS", 300))        # set via Fly secret

# ── Friendly, on-brand upsell copy ─────────────────────────────
STOP_MSG = (
    "🔒 That was your {limit}<sup>th</sup> free score.\n"
    "Drop a ⭐ once to unlock <b>unlimited feedback</b> – "
    "<i>cheaper than a coffee!</i>"
)


class QuotaMiddleware(BaseMiddleware):
    """
    • Each user gets up to FREE_LIMIT auto-scorings.
    • Once exhausted, send a gentle upsell message plus a Telegram-Stars
      invoice and block further handling until payment succeeds.
    """

    async def __call__(self, handler, event: Message, data):
        # Ignore non-message updates or posts without a sender
        if not isinstance(event, Message) or not event.from_user:
            return await handler(event, data)

        user_id = event.from_user.id

        # ── 1 · Fetch usage & premium flag ──────────────────────
        async with get_pool() as pool:
            row = await pool.fetchrow(
                """
                SELECT is_premium,
                       (SELECT COUNT(*) FROM submissions WHERE user_id = $1) AS used
                  FROM users
                 WHERE id = $1
                """,
                user_id,
            )

        is_premium = row and row["is_premium"]
        used        = row["used"] if row else 0

        # ── 2 · Still within quota or already premium? → OK ────
        if is_premium or used < FREE_LIMIT:
            return await handler(event, data)

        # ── 3 · Quota exhausted → upsell & block ───────────────
        await event.answer(STOP_MSG.format(limit=FREE_LIMIT), parse_mode="HTML")

        payload = f"unlim:{user_id}:{PRICE_STARS}"
        await event.bot.send_invoice(
            chat_id         = event.chat.id,
            title           = "IELTS Bot · Unlimited scoring",
            description     = "One-time purchase — lifetime essay & speaking scores.",
            payload         = payload,
            provider_token  = "STARS",   # ← REQUIRED for Telegram Stars
            currency        = "XTR",     # fixed code for Stars
            prices          = [{"label": "Unlimited", "amount": PRICE_STARS}],
        )
        # Swallow the update so no scoring happens
        return
