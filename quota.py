# quota.py — Stars pay-wall middleware
# ════════════════════════════════════
# • First N submissions (essay + voice) are free for any user.
# • After the free quota the user must have `credits_left > 0`.
# • All payments stay inside Telegram via provider_token="STARS".

import os
from aiogram import BaseMiddleware
from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db    import get_pool
from plans import PLANS                    # shared price-table

FREE_LIMIT = int(os.getenv("PAYWALL_FREE_LIMIT", 5))

STOP_MSG = (
    "🔒 That was your {limit}ᵗʰ free score.\n"
    "Choose a credit pack to keep getting feedback ⤵️"
)


def _plans_keyboard() -> InlineKeyboardMarkup:
    """Return an inline keyboard with the three credit plans."""
    kb = InlineKeyboardBuilder()
    for plan, info in PLANS.items():
        kb.button(
            text=f"{plan.title()} — {info['credits']} scores  (⭐{info['stars']})",
            callback_data=f"buy_{plan}",
        )
    kb.adjust(1)          # one button per row
    return kb.as_markup()


class QuotaMiddleware(BaseMiddleware):
    """
    • Allows each user up to `FREE_LIMIT` submissions for free.
    • After that the user needs positive `credits_left`.
    • On deficit, shows the plans menu and blocks the update.
    """

    async def __call__(self, handler, event: Message, data):
        # ── 0 · ignore non-message or payment updates ────────────────────
        if (
            not isinstance(event, Message)
            or not event.from_user
            or event.successful_payment is not None
        ):
            return await handler(event, data)

        uid = event.from_user.id

        # ── 1 · fetch usage & credits ─────────────────────────────────────
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

        # ── 2 · still within quota OR has credits —> pass through ─────────
        if credits_left > 0 or used < FREE_LIMIT:
            return await handler(event, data)

        # ── 3 · out of credits —> upsell & swallow the update ─────────────
        await event.answer(
            STOP_MSG.format(limit=FREE_LIMIT),
            parse_mode="HTML",
            reply_markup=_plans_keyboard(),
        )
        return  # original handler is NOT executed
