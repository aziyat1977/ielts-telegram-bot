# quota.py — Telegram Stars pay-wall middleware
#
# The first N scorings are free, afterwards the bot offers a one-time ⭐ unlock.
# No external PSP required – Telegram handles the payment when
# provider_token="STARS".

import os
from aiogram import BaseMiddleware
from aiogram.types import Message

from db import get_pool                    # new pool on every call

FREE_LIMIT   = int(os.getenv("PAYWALL_FREE_LIMIT", 5))     # free scores
PRICE_STARS  = int(os.getenv("PRICE_STARS", 300))          # set as Fly secret

# ── Friendly, on-brand upsell copy (HTML-safe) ─────────────────────────
STOP_MSG = (
    "🔒 That was your {limit}ᵗʰ free score.\n"               # ← no <sup> tag
    "Drop a ⭐ once to unlock <b>unlimited feedback</b> – "
    "<i>cheaper than a coffee!</i>"
)


class QuotaMiddleware(BaseMiddleware):
    """
    • Each user may submit up to FREE_LIMIT items for automatic scoring.
    • When the quota is reached, send a gentle upsell + Telegram-Stars
      invoice and block further processing until payment succeeds.
    """

    async def __call__(self, handler, event: Message, data):
        # Ignore everything that is not a user message
        if not isinstance(event, Message) or not event.from_user:
            return await handler(event, data)

        user_id = event.from_user.id

        # ── 1 · Usage & premium status ───────────────────────────
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

        # ── 2 · Within quota or already premium → continue ──────
        if is_premium or used < FREE_LIMIT:
            return await handler(event, data)

        # ── 3 · Quota exhausted → upsell & block ────────────────
        await event.answer(STOP_MSG.format(limit=FREE_LIMIT), parse_mode="HTML")

        payload = f"unlim:{user_id}:{PRICE_STARS}"
        await event.bot.send_invoice(
            chat_id        = event.chat.id,
            title          = "IELTS Bot · Unlimited scoring",
            description    = "One-time purchase — lifetime essay & speaking scores.",
            payload        = payload,
            provider_token = "STARS",      # Telegram Stars
            currency       = "XTR",        # fixed code for Stars
            prices         = [{"label": "Unlimited", "amount": PRICE_STARS}],
        )

        # Swallow the update so the original handler is NOT executed
        return
