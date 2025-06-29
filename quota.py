# quota.py — Stars pay-wall middleware
# ════════════════════════════════════
# ● First N submissions (essay + voice) are free.  
# ● After the quota the user needs `credits_left > 0`.  
# ● Payments stay 100 % inside Telegram via provider_token="STARS".

import os
from aiogram import BaseMiddleware
from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import get_pool
from plans import PLANS                           # shared price-table

FREE_LIMIT = int(os.getenv("PAYWALL_FREE_LIMIT", 5))

# ── copy shown when quota exhausted ──────────────────────────────
STOP_MSG = (
    "🔒 That was your {limit}ᵗʰ free score.\n"
    "Choose a credit pack to keep getting feedback ⤵️"
)


def _plans_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard containing the three credit plans."""
    kb = InlineKeyboardBuilder()
    for plan, info in PLANS.items():
        kb.button(
            text=f"{plan.title()} — {info['credits']} scores (⭐{info['stars']})",
            callback_data=f"buy_{plan}",
        )
    kb.adjust(1)          # one button per row
    return kb.as_markup()


class QuotaMiddleware(BaseMiddleware):
    """
    • Allows each user up to `FREE_LIMIT` submissions for free.  
    • Afterwards the user must have positive `credits_left`.  
    • If not, shows the plans keyboard and stops further handling.
    """

    async def __call__(self, handler, event: Message, data):
        # ── 0 · ignore updates that should bypass the pay-wall ───────────
        if (
            not isinstance(event, Message)              # not a message update
            or not event.from_user                      # no sender (e.g. channel)
            or event.successful_payment is not None     # payment confirmation
        ):
            return await handler(event, data)

        # always allow basic commands so the bot UI works even without credits
        if event.text:
            cmd = event.text.split()[0].lower()
            if cmd in {"/start", "/plans", "/help", "/me", "/top"}:
                return await handler(event, data)

        uid = event.from_user.id

        # ── 1 · fetch current usage & credits ────────────────────────────
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
        used         = row["used"] if row else 0

        # ── 2 · within free quota OR has credits → let it pass ───────────
        if credits_left > 0 or used < FREE_LIMIT:
            return await handler(event, data)

        # ── 3 · no credits → upsell & swallow update ─────────────────────
        await event.answer(
            STOP_MSG.format(limit=FREE_LIMIT),
            parse_mode="HTML",
            reply_markup=_plans_keyboard(),
        )
        # do NOT call the original handler
        return
