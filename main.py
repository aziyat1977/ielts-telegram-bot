"""
IELTS Bot — Essay & Speaking Scorer v2.8.2
──────────────────────────────────────────
• aiogram 3.x • OpenAI SDK 1.x
• asyncpg DB → XP & streaks
• Stars pay-wall → credit plans (first 5 free)
• Default LLM : gpt-3.5-turbo  (override OPENAI_MODEL)
• Health-check : GET /ping on :8080
• Demo buttons + /plans menu
"""

# ── imports & config (unchanged) ───────────────────────────
import asyncio, json, logging, os, pathlib, subprocess, tempfile, uuid
from contextlib import suppress

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,   # ← must be imported before use
    Message,
    PreCheckoutQuery,
)
from openai import AsyncOpenAI, OpenAIError

from db    import get_pool, upsert_user, save_submission
from quota import QuotaMiddleware
from plans import PLANS
# … (rest of config code exactly as before) …

# ── 4 · UI helpers ─────────────────────────────────────────
def _plans_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard with the paid credit packs."""
    rows: list[list[InlineKeyboardButton]] = []
    for plan, info in PLANS.items():
        rows.append([
            InlineKeyboardButton(
                text=f"{plan.title()} – {info['credits']} scores (⭐{info['stars']})",
                callback_data=f"buy_{plan}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── 5 · /start & demo buttons ──────────────────────────────
@dp.message(Command("start"))
async def cmd_start(msg: Message) -> None:
    greet = (
        "👋 Hi!\n\n"
        "<b>How to use me:</b>\n"
        "• <code>/write &lt;essay&gt;</code> — instant band & tips\n"
        "• Send a voice note — instant speaking score\n"
        "• First 5 scores are free, then top-up with ⭐ plans\n\n"
        "Commands: <code>/me</code> · <code>/top</code> · <code>/plans</code>"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="📝 Try sample essay", callback_data="demo_essay"),
            InlineKeyboardButton(text="🎙️ Try voice demo",  callback_data="demo_voice"),
        ]]
    )
    await msg.answer(greet, reply_markup=kb)

# ── rest of file remains unchanged ─────────────────────────
# (write/voice handlers, payment hooks, etc.)
