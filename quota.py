# quota.py — Telegram Stars pay-wall middleware
# ---------------------------------------------
# • First N messages (essays + voices) are free.
# • After that the user must have a positive `credits_left`.
# • We keep the payment flow entirely inside Telegram by using provider_token="STARS".

import os
from aiogram import BaseMiddleware
from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db   import get_pool
from plans import PLANS          # shared price-table (avoids circular import)

FREE_LIMIT = int(os.getenv("PAYWALL_FREE_LIMIT", 5))

STOP_MSG = (
    "🔒 That was your {limit}ᵗʰ free score.\n"
    "Please pick a credit pack to continue receiving feedback:"
)

def _plans_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard with the three credit plans."""
    kb = InlineKeyboardBuilder()
    for plan, info in PLANS.items():
        kb.button(
            text=f"{plan.title()} — {info['credits']} scores  (⭐{info['stars']})",
            callback_data=f"buy_{plan}",
        )
    kb.adjust(1)           # one button per row
    return kb.as_markup()

class QuotaMiddleware(BaseMiddleware):
    """
    • Allows each user up to `FREE_LIMIT` submissions for free.
    • Afterwards the user must have `credits_left > 0`.
    • If not, sends the upsell message with plan buttons and blocks the update.
    """

    async def __call__(self, handler, event: Message, data):
        # ── 0 · ignore non-message or payment updates ───────────────────────
        if (
            not isinstance(event, Message)
            or not event.from_user
            or event.successful_payment is not None
        ):
            return await handler(event, data)

        uid = event.from_user.id

        # ── 1 · fetch current usage & credits ───────────────────────────────
        async with get_pool() as pool:
            row = await pool.fetchrow(
                """
                SELECT credits_left,
                       (SELECT COUNT(*) FROM submissions WHERE user_id = $1) AS used
                  FROM users
                 WHERE id = $1
                """,
                uid,
            )

        credits_left = row["credits_left"] if row else 0
        used         = row["used"]         if row else 0

        # ── 2 · still free quota OR has credits → pass through ──────────────
        if credits_left > 0 or used < FREE_LIMIT:
            return await handler(event, data)

        # ── 3 · out of credits → upsell & swallow update ────────────────────
        await event.answer(
            STOP_MSG.format(limit=FREE_LIMIT),
            parse_mode="HTML",
            reply_markup=_plans_keyboard(),
        )
        return  # block original handler
