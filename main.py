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

# ── Imports ────────────────────────────────────────────────
import asyncio, json, logging, os, pathlib, subprocess, tempfile, uuid
from contextlib import suppress

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    PreCheckoutQuery,
)
from openai import AsyncOpenAI, OpenAIError

from db    import get_pool, upsert_user, save_submission
from quota import QuotaMiddleware
from plans  import PLANS


# ── Config / Globals ───────────────────────────────────────
TOKEN      = os.getenv("TELEGRAM_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

if not TOKEN:
    raise RuntimeError("❌ TELEGRAM_TOKEN is missing")
if not OPENAI_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY is missing")

openai = AsyncOpenAI(api_key=OPENAI_KEY)
bot    = Bot(TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

# Dispatcher must exist BEFORE decorators are evaluated 👇
dp = Dispatcher()
dp.message.middleware(QuotaMiddleware())


SYSTEM_MSG = (
    "You are a certified IELTS examiner. "
    "Score the given text (or speech transcript) from 1-9 and return "
    "EXACTLY three concise bullet-point tips for improvement."
)

# ── /ping health server ────────────────────────────────────
async def _start_health_server() -> None:
    async def _handler(r: asyncio.StreamReader, w: asyncio.StreamWriter):
        first = await r.readline()
        if b"GET /ping" in first:
            w.write(b"HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\nOK\n")
        else:
            w.write(b"HTTP/1.1 404 Not Found\r\nContent-Length: 9\r\n\r\nNot Found")
        await w.drain()
        w.close()

    srv = await asyncio.start_server(_handler, "0.0.0.0", 8080)
    asyncio.create_task(srv.serve_forever())


# ── UI helpers ─────────────────────────────────────────────
def _plans_keyboard() -> InlineKeyboardMarkup:
    """Inline-keyboard with paid credit packs."""
    rows = [[
        InlineKeyboardButton(
            text=f"{plan.title()} – {info['credits']} scores (⭐{info['stars']})",
            callback_data=f"buy_{plan}",
        )
    ] for plan, info in PLANS.items()]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── /start + demo buttons ─────────────────────────────────
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
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton("📝 Try sample essay", callback_data="demo_essay"),
        InlineKeyboardButton("🎙️ Try voice demo",  callback_data="demo_voice"),
    ]])
    await msg.answer(greet, reply_markup=kb)


@dp.callback_query(F.data == "demo_essay")
async def cb_demo_essay(q: CallbackQuery) -> None:
    await q.answer()
    await q.message.answer(
        "/write Nowadays more and more people decide to live alone. "
        "Do the advantages of this trend outweigh its disadvantages?"
    )


@dp.callback_query(F.data == "demo_voice")
async def cb_demo_voice(q: CallbackQuery) -> None:
    await q.answer()
    await q.message.answer(
        "📌 Send a short voice note (5-10 s) and I’ll show you the speaking scorer!"
    )


# ── /plans & purchase flow (unchanged) ────────────────────
@dp.message(Command("plans"))
async def cmd_plans(msg: Message):
    await msg.answer("🚀 Pick a plan:", reply_markup=_plans_keyboard())


@dp.callback_query(F.data.startswith("buy_"))
async def cb_buy_plan(q: CallbackQuery):
    plan = q.data.removeprefix("buy_")
    info = PLANS[plan]
    payload = f"plan:{plan}:{info['stars']}"
    await bot.send_invoice(
        chat_id=q.message.chat.id,
        title=f"{plan.title()} plan",
        description=f"{info['credits']} scores (essay or speaking)",
        payload=payload,
        provider_token="STARS",
        currency="XTR",
        prices=[{"label": plan.title(), "amount": info["stars"]}],
    )
    await q.answer()


# ── voice→mp3, scorer, /write, voice handler, stats, payment,
#    fallback, etc. are **unchanged** from v2.8.1
#    (keep those sections exactly as they were).              


# ── Entrypoint ─────────────────────────────────────────────
async def main() -> None:
    """Bootstraps the bot, health server, and polling loop."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    await _start_health_server()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
