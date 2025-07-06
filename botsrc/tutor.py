import os, textwrap, json
from aiogram import types, Bot
from aiogram.types import BufferedInputFile
from openai import AsyncOpenAI, OpenAIError

from db     import get_pool, save_submission, upsert_user
from botsrc.tts_client import TTSClient


# ── OpenAI set-up ──────────────────────────────────────────
OPENAI_KEY  = os.environ["OPENAI_API_KEY"]
MODEL_NAME  = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
openai      = AsyncOpenAI(api_key=OPENAI_KEY)
SYSTEM_MSG  = (
    "You are a certified IELTS examiner. Score the text from 1-9 and return "
    "EXACTLY three concise bullet-point tips for improvement."
)


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
    band = max(1, min(9, data["band"]))
    return band, data["feedback"]


# ── Voice-ID helper ───────────────────────────────────────
def _voice_for_plan(plan: str | None) -> str:
    plan = (plan or "").lower()
    return {
        "starter": os.getenv("VOICE_ID_STARTER"),
        "plus":    os.getenv("VOICE_ID_PLUS"),
        "premium": os.getenv("VOICE_ID_PREMIUM"),
    }.get(plan, os.getenv("VOICE_ID_STARTER"))


# ── /tutor handler ────────────────────────────────────────
async def handle_tutor(message: types.Message, bot: Bot) -> None:
    # 1. get text from reply
    if message.reply_to_message and message.reply_to_message.voice:
        from asr import transcribe_async            # your Whisper util
        raw_text = await transcribe_async(message.reply_to_message.voice)
    elif message.reply_to_message and message.reply_to_message.text:
        raw_text = message.reply_to_message.text
    else:
        await message.answer("Reply to an essay or voice note so I can tutor you!")
        return

    # 2. IELTS scoring
    try:
        band, tips = await _get_band_and_tips(raw_text)
    except OpenAIError as e:
        await message.answer(f"⚠️ OpenAI error: {e}")
        return

    summary = textwrap.shorten(f"{band} / 9.0. {' '.join(tips)}",
                               width=500, placeholder="…")

    # 3. TTS
    tts   = TTSClient()
    audio = await tts.synth(text=summary,
                            voice_id=_voice_for_plan(None))   # plan-based later

    # 4. send audio
    await bot.send_voice(
        chat_id = message.chat.id,
        voice   = types.BufferedInputFile(audio, "feedback.mp3"),
        caption = "Here’s my audio feedback (-1 ⭐)."
    )

    # 5. DB bookkeeping & credit- -1
    async with get_pool() as pool:
        await upsert_user(pool, message.from_user)
        await save_submission(
            pool, message.from_user, "audio_tutor", band, json.dumps(tips),
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

    if credits is not None and credits <= 5:
        await message.answer(f"⚠️ Only {credits} credit(s) left. Use /plans to top-up.")
