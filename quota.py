# quota.py — Telegram Stars pay-wall middleware
#
# First N scorings are free; after that the user must have credits.
# provider_token="STARS" keeps everything inside Telegram.

import os
from aiogram import BaseMiddleware
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from db import get_pool
from main import PLANS                         # reuse price table

FREE_LIMIT = int(os.getenv("PAYWALL_FREE_LIMIT", 5))

STOP_MSG = (
    "🔒 That was your {limit}ᵗʰ free score.\n"
    "Pick a credit pack to keep getting feedback:"
)

def _plans_keyboard() -> InlineKeyboardMarkup:
    from aiogram.utils.keyboard import InlineKeyboardBuilder  # lazy import
    kb = InlineKeyboardBuilder()
    for plan, info in PLANS.items():
        kb.button(
            text=f"{plan.title()} – {info['credits']} (⭐{info['stars']})",
            callback_data=f"buy_{plan}",
        )
        kb.adjust(1)
    return kb.as_markup()

class QuotaMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data):
        # ignore non-message or payment updates
        if (
            not isinstance(event, Message)
            or not event.from_user
            or event.successful_payment is not None
        ):
            return await handler(event, data)

        uid = event.from_user.id

        async with get_pool() as pool:
            row = await pool.fetchrow(
                """
                SELECT credits_left,
                       (SELECT COUNT(*) FROM submissions WHERE user_id=$1) AS used
                  FROM users WHERE id=$1
                """,
                uid,
            )

        credits_left = row["credits_left"] if row else 0
        used         = row["used"] if row else 0

        if credits_left > 0 or used < FREE_LIMIT:
            return await handler(event, data)

        # out of credits → upsell
        await event.answer(
            STOP_MSG.format(limit=FREE_LIMIT),
            parse_mode="HTML",
            reply_markup=_plans_keyboard(),
        )
        return  # swallow the update
