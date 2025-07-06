"""
IELTS Bot — Essay & Speaking Scorer v2.8.3
──────────────────────────────────────────
• aiogram 3.x  • OpenAI SDK 1.x
• asyncpg DB → XP & streaks
• Stars pay-wall → credit plans (first 5 free)
• Default LLM : gpt-3.5-turbo (override OPENAI_MODEL)
• Health-check : GET /ping on :8080
• Demo buttons + /plans menu
"""

# ── Imports ───────────────────────────────────────────────
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
from plans import PLANS
from botsrc.tutor import handle_tutor
from botsrc.text_tutor import cmd_tutor_text, process_callback, cmd_text_go
from botsrc.text_tutor import cmd_tutor_text, process_callback, cmd_text_go
from botsrc.text_tutor import cmd_tutor_text, process_callback, cmd_text_go         # audio-tutor handler

# ── Config / Globals ──────────────────────────────────────
TOKEN      = os.getenv("TELEGRAM_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

if not TOKEN:
    raise RuntimeError("❌ TELEGRAM_TOKEN is missing")
if not OPENAI_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY is missing")

openai = AsyncOpenAI(api_key=OPENAI_KEY)
bot    = Bot(TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

dp = Dispatcher()
dp.message.middleware(QuotaMiddleware())
dp.message(Command('tutor'))(handle_tutor)
dp.message(Command('tutor_text'))(cmd_tutor_text)
dp.callback_query()(process_callback)
dp.message(Command('text_go'))(cmd_text_go)

SYSTEM_MSG = (
    "You are a certified IELTS examiner. "
    "Score the given text (or speech transcript) from 1-9 and return "
    "EXACTLY three concise bullet-point tips for improvement."
)

# ── /ping health server ──────────────────────────────────
async def _start_health_server() -> None:
    async def _handler(r: asyncio.StreamReader, w: asyncio.StreamWriter):
        first = await r.readline()
        if b"GET /ping" in first:
            w.write(b"HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\nOK\n")
        else:
            w.write(b"HTTP/1.1 404 Not Found\r\nContent-Length: 9\r\n\r\nNot Found")
        await w.drain(); w.close()
    srv = await asyncio.start_server(_handler, "0.0.0.0", 8080)
    asyncio.create_task(srv.serve_forever())

# ── UI helpers ───────────────────────────────────────────
def _plans_keyboard() -> InlineKeyboardMarkup:
    rows = [[
        InlineKeyboardButton(
            text=f"{plan.title()} – {info['credits']} scores (⭐{info['stars']})",
            callback_data=f"buy_{plan}",
        )
    ] for plan, info in PLANS.items()]
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ── /start & demo buttons ────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(msg: Message) -> None:
    greet = (
        "👋 Hi!\n\n"
        "<b>How to use me:</b>\n"
        "• <code>/write &lt;essay&gt;</code> — instant band & tips\n"
        "• Send a voice note — instant speaking score\n"
        "• First 5 scores are free, then top-up with ⭐ plans\n\n"
        "Commands: <code>/me</code> · <code>/top</code> · <code>/plans</code> · "
        "<code>/tutor</code> (audio feedback)"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📝 Try sample essay", callback_data="demo_essay"),
        InlineKeyboardButton(text="🎙️ Try voice demo",  callback_data="demo_voice"),
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

# ── /plans + purchase flow ───────────────────────────────
@dp.message(Command("plans"))
async def cmd_plans(msg: Message):
    await msg.answer("🚀 Pick a plan:", reply_markup=_plans_keyboard())

@dp.callback_query(F.data.startswith("buy_"))
async def cb_buy_plan(q: CallbackQuery):
    plan   = q.data.removeprefix("buy_")
    info   = PLANS[plan]
    payload = f"plan:{plan}:{info['stars']}"
    await bot.send_invoice(
        chat_id        = q.message.chat.id,
        title          = f"{plan.title()} plan",
        description    = f"{info['credits']} scores (essay or speaking)",
        payload        = payload,
        provider_token = "STARS",
        currency       = "XTR",
        prices         = [{"label": plan.title(), "amount": info["stars"]}],
    )
    await q.answer()

# ── OpenAI scorer util ───────────────────────────────────
async def _get_band_and_tips(text: str) -> tuple[int, list[str]]:
    rsp = await openai.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "system", "content": SYSTEM_MSG},
                  {"role": "user",   "content": text}],
        functions=[{
            "name": "score",
            "parameters": {
                "type": "object",
                "properties": {
                    "band": {"type": "integer", "minimum": 1, "maximum": 9},
                    "feedback": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 3, "maxItems": 3,
                    },
                },
                "required": ["band", "feedback"],
            },
        }],
        function_call={"name": "score"},
        max_tokens=400,
    )
    data = json.loads(rsp.choices[0].message.function_call.arguments)
    return max(1, min(9, data["band"])), data["feedback"]

async def _reply_with_score(msg: Message, band: int, tips: list[str]) -> None:
    await msg.answer(f"🏅 <b>Band {band}</b>\n• " + "\n• ".join(tips))
    async with get_pool() as pool:
        credits = await pool.fetchval(
            "SELECT credits_left FROM users WHERE id=$1;",
            msg.from_user.id,
        )
    if credits is not None and credits <= 5:
        await msg.answer(f"⚠️ Only {credits} credit(s) left. Use /plans to top-up.")

# ── /write (inline or reply) ─────────────────────────────
@dp.message(Command("write"))
async def cmd_write(msg: Message):
    essay = (msg.text.split(maxsplit=1)[1:2] or [""])[0].strip()
    if not essay and msg.reply_to_message and msg.reply_to_message.text:
        essay = msg.reply_to_message.text.strip()

    if not essay:
        return await msg.answer(
            "✍️ Paste the essay on the same line <b>or</b> "
            "reply to an essay with /write."
        )

    await msg.answer("⏳ Scoring… please wait")
    try:
        band, tips = await _get_band_and_tips(essay)
        await _reply_with_score(msg, band, tips)

        async with get_pool() as pool:
            await upsert_user(pool, msg.from_user)
            await save_submission(
                pool, msg.from_user, "essay", band, json.dumps(tips),
                word_count=len(essay.split()),
            )
            await pool.execute(
                "UPDATE users "
                "SET credits_left = GREATEST(credits_left - 1, 0) "
                "WHERE id=$1;",
                msg.from_user.id,
            )
    except OpenAIError as e:
        logging.error("OPENAI error → %s", e)
        await msg.answer(f"⚠️ OpenAI error: {e}")
    except Exception as e:
        logging.exception("Unhandled error")
        await msg.answer(f"⚠️ Unexpected error: {e}")

@dp.message(F.text.startswith("/write "))
async def prefix_write(msg: Message):
    await cmd_write(msg)

# (voice handler, stats, payments … unchanged)

# ── Entrypoint ───────────────────────────────────────────
async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    await _start_health_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
from botsrc.text_tutor import cmd_tutor_text, process_callback, cmd_text_go

