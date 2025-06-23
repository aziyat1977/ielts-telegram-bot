"""
IELTS Bot — Essay & Speaking Scorer v2.4
────────────────────────────────────────
• aiogram 3.x   • OpenAI SDK 1.x
• asyncpg DB  → XP & streaks
• Stars-only paywall (first 5 free → one-time ⭐ unlock)
• Default model: gpt-3.5-turbo (override with OPENAI_MODEL)
"""

import asyncio, json, logging, os, pathlib, subprocess, tempfile, uuid
from contextlib import suppress

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message, PreCheckoutQuery
from openai import AsyncOpenAI, OpenAIError

# ── local helpers ──────────────────────────────────────────────
from db    import get_pool, upsert_user, save_submission
from quota import QuotaMiddleware                 # ⭐ Stars paywall

# ── 1 · Config ────────────────────────────────────────────────
TOKEN      = os.getenv("TELEGRAM_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

if not TOKEN:
    raise RuntimeError("❌ TELEGRAM_TOKEN is missing")
if not OPENAI_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY is missing")

openai = AsyncOpenAI(api_key=OPENAI_KEY)

bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp  = Dispatcher()
dp.message.middleware(QuotaMiddleware())          # paywall middleware

SYSTEM_MSG = (
    "You are a certified IELTS examiner. "
    "Score the given text (or speech transcript) from 1‒9 and return "
    "EXACTLY three concise bullet-point tips for improvement."
)

# ── 2 · voice → mp3 helper ───────────────────────────────────
async def _voice_to_mp3(bot_obj: Bot, file_id: str) -> pathlib.Path:
    tg_file  = await bot_obj.get_file(file_id)
    tmp      = pathlib.Path(tempfile.gettempdir())
    oga      = tmp / f"{uuid.uuid4()}.oga"
    mp3      = oga.with_suffix(".mp3")

    await bot_obj.download_file(tg_file.file_path, destination=oga)
    subprocess.run(
        ["ffmpeg", "-i", str(oga), "-vn", "-acodec", "libmp3lame", "-y", str(mp3)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    oga.unlink(missing_ok=True)
    return mp3

# ── 3 · OpenAI scorer ────────────────────────────────────────
async def _get_band_and_tips(text: str) -> tuple[int, list[str]]:
    rsp = await openai.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_MSG},
            {"role": "user",   "content": text},
        ],
        functions=[{
            "name": "score",
            "parameters": {
                "type": "object",
                "properties": {
                    "band":     {"type": "integer", "minimum": 1, "maximum": 9},
                    "feedback": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 3, "maxItems": 3
                    }
                },
                "required": ["band", "feedback"]
            }
        }],
        function_call={"name": "score"},
        max_tokens=400,
    )
    data = json.loads(rsp.choices[0].message.function_call.arguments)
    return max(1, min(9, data["band"])), data["feedback"]

async def _reply_with_score(msg: Message, band: int, tips: list[str]) -> None:
    await msg.answer(f"🏅 <b>Band {band}</b>\n• " + "\n• ".join(tips))

# ── 4 · /start greeting ──────────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(msg: Message):
    await msg.answer(
        "👋 Hi!\n\n"
        "<b>How to use me:</b>\n"
        "• <code>/write your essay text</code> — I’ll grade it.\n"
        "• Send a <b>voice note</b> — I’ll transcribe & grade.\n"
        "• First 5 scores are free, then unlock with ⭐ once.\n\n"
        "Commands: <code>/me</code> (stats) · <code>/top</code> (leaderboard)"
    )

# ── 5 · /write ------------------------------------------------
@dp.message(Command("write"))
async def cmd_write(msg: Message):
    essay = (msg.text.split(maxsplit=1)[1:2] or [""])[0].strip()
    if not essay:
        return await msg.answer("✍️ Paste the essay on the same line after /write …")

    await msg.answer("⏳ Scoring … please wait")
    try:
        band, tips = await _get_band_and_tips(essay)
        await _reply_with_score(msg, band, tips)

        async with get_pool() as pool:
            await upsert_user(pool, msg.from_user)
            await save_submission(
                pool, msg.from_user, "essay", band, tips,
                word_count=len(essay.split())
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

# ── 6 · voice handler ----------------------------------------
@dp.message(F.voice)
async def handle_voice(msg: Message):
    mp3 = await _voice_to_mp3(bot, msg.voice.file_id)
    await msg.answer("⏳ Transcribing …")
    try:
        transcript = await openai.audio.transcriptions.create(
            model="whisper-1", file=open(mp3, "rb"), response_format="text"
        )
    finally:
        mp3.unlink(missing_ok=True)

    await msg.answer("⏳ Scoring … please wait")
    try:
        band, tips = await _get_band_and_tips(transcript)
        await _reply_with_score(msg, band, tips)

        async with get_pool() as pool:
            await upsert_user(pool, msg.from_user)
            await save_submission(
                pool, msg.from_user, "speaking", band, tips,
                seconds=msg.voice.duration
            )
    except OpenAIError as e:
        logging.error("OPENAI error → %s", e)
        await msg.answer(f"⚠️ OpenAI error: {e}")
    except Exception as e:
        logging.exception("Unhandled error")
        await msg.answer(f"⚠️ Unexpected error: {e}")

# ── 7 · Stats commands ---------------------------------------
@dp.message(Command("me"))
async def cmd_me(msg: Message):
    async with get_pool() as pool:
        row = await pool.fetchrow(
            "SELECT xp, streak, is_premium FROM users WHERE id = $1",
            msg.from_user.id,
        )
    if not row:
        return await msg.answer("No stats yet—send an essay or voice note first!")
    premium = "✔️" if row["is_premium"] else "❌"
    await msg.answer(
        f"🏅 XP: <b>{row['xp']}</b>\n"
        f"🔥 Streak: <b>{row['streak']}</b> day(s)\n"
        f"💎 Premium: {premium}"
    )

@dp.message(Command("top"))
async def cmd_top(msg: Message):
    async with get_pool() as pool:
        rows = await pool.fetch(
            "SELECT username, xp FROM users ORDER BY xp DESC LIMIT 10"
        )
    if not rows:
        return await msg.answer("Nobody on the board yet—be the first!")
    await msg.answer(
        "\n".join(
            f"#{i+1} @{r['username'] or 'anon'} — {r['xp']} XP"
            for i, r in enumerate(rows)
        )
    )

# ── 8 · Stars payment callbacks ------------------------------
@dp.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(q.id, ok=True)

@dp.message(F.successful_payment)
async def payment_success(msg: Message):
    async with get_pool() as pool:
        await pool.execute(
            "UPDATE users SET is_premium=TRUE WHERE id=$1", msg.from_user.id
        )
    await msg.answer("✅ Unlimited scoring unlocked – thank you!")

# ── 9 · Heart-beat / fallback -------------------------------
@dp.message(F.text)
async def echo(msg: Message):
    with suppress(TelegramBadRequest):
        await msg.answer("👋 Hello from <a href='https://fly.io'>Fly.io</a>!")

# ── Entrypoint -----------------------------------------------
async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    await dp.start_polling(bot)  # default update types (fix applied)

if __name__ == "__main__":
    asyncio.run(main())
