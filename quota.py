# quota.py · Stars-only paywall middleware
import os
from aiogram import BaseMiddleware
from aiogram.types import Message

from db import get_pool                       # fresh pool each call

FREE_LIMIT  = int(os.getenv("PAYWALL_FREE_LIMIT", 5))
PRICE_STARS = int(os.getenv("PRICE_STARS", 300))   # set via Fly secret


class QuotaMiddleware(BaseMiddleware):
    """
    • Lets every user score up to FREE_LIMIT submissions.
    • After that, blocks the request and sends a Telegram-Stars invoice.
    """

    async def __call__(self, handler, event: Message, data):
        # Ignore non-message updates or bot/system senders
        if not isinstance(event, Message) or not event.from_user:
            return await handler(event, data)

        # ── 1 · Fetch usage & premium flag ───────────────────────
        async with get_pool() as pool:
            row = await pool.fetchrow(
                """
                SELECT is_premium,
                       (SELECT COUNT(*) FROM submissions WHERE user_id = $1) AS used
                  FROM users
                 WHERE id = $1
                """,
                event.from_user.id,
            )

        is_premium = row and row["is_premium"]
        used        = row["used"] if row else 0

        # ── 2 · Allow if under quota or already premium ─────────
        if is_premium or used < FREE_LIMIT:
            return await handler(event, data)

        # ── 3 · Otherwise send Stars invoice & block ────────────
        payload = f"unlim:{event.from_user.id}:{PRICE_STARS}"
        await event.bot.send_invoice(
            chat_id      = event.chat.id,
            title        = "IELTS Bot · Unlimited Scoring",
            description  = "One-time purchase — unlimited essay & speaking scores.",
            payload      = payload,
            provider_token = "",          # empty ⇒ Telegram Stars
            currency       = "XTR",       # fixed currency code for Stars
            prices         = [{"label": "Unlimited", "amount": PRICE_STARS}],
        )
        return  # stops the original handler
