import os, textwrap
from aiogram import types, Bot

from db     import get_pool, save_submission, upsert_user
from scorer import score_essay_or_voice_async
from botsrc.tts_client import TTSClient   # local wrapper


def _voice_for_plan(plan: str | None) -> str:
    plan = (plan or "").lower()
    return {
        "starter": os.getenv("VOICE_ID_STARTER"),
        "plus":    os.getenv("VOICE_ID_PLUS"),
        "premium": os.getenv("VOICE_ID_PREMIUM"),
    }.get(plan, os.getenv("VOICE_ID_STARTER"))


async def handle_tutor(message: types.Message, bot: Bot) -> None:
    # 1️⃣  Pull text from the replied message
    if message.reply_to_message and message.reply_to_message.voice:
        from asr import transcribe_async                 # your Whisper util
        raw_text = await transcribe_async(message.reply_to_message.voice)
    elif message.reply_to_message and message.reply_to_message.text:
        raw_text = message.reply_to_message.text
    else:
        await message.answer("Reply to an essay or voice note so I can tutor you!")
        return                                            # nothing to do

    # 2️⃣  Run IELTS scoring + summary
    res = await score_essay_or_voice_async(raw_text)
    summary = textwrap.shorten(
        f"{res['band']} / 9.0. {res['tips']}",
        width=500,
        placeholder="…"
    )

    # 3️⃣  Text-to-speech
    tts   = TTSClient()
    audio = await tts.synth(text=summary, voice_id=_voice_for_plan(res.get("plan")))

    # 4️⃣  Send voice note back to the user
    await bot.send_voice(
        chat_id = message.chat.id,
        voice   = types.InputFile.from_buffer(audio, filename="feedback.mp3"),
        caption = "Here’s my audio feedback (-1 ⭐).",
    )

    # 5️⃣  DB bookkeeping: save submission & deduct 1 credit
    async with get_pool() as pool:
        await upsert_user(pool, message.from_user)
        await save_submission(
            pool, message.from_user, "audio_tutor", res["band"], str(res["tips"]),
            seconds=0
        )
        await pool.execute(
            "UPDATE users "
            "SET credits_left = GREATEST(credits_left - 1, 0) "
            "WHERE id = $1",
            message.from_user.id,
        )
        credits = await pool.fetchval(
            "SELECT credits_left FROM users WHERE id = $1",
            message.from_user.id,
        )

    # 6️⃣  Low-credit warning
    if credits is not None and credits <= 5:
        await message.answer(f"⚠️ Only {credits} credit(s) left. Use /plans to top-up.")
