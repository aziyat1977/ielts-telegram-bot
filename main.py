"""
IELTS Bot — Essay & Speaking Scorer v2.8.2
──────────────────────────────────────────
• aiogram 3.x • OpenAI SDK 1.x
• asyncpg DB → XP & streaks
• Stars pay-wall → credit plans (first 5 free)
• Default LLM : gpt-3.5-turbo (override OPENAI_MODEL)
• Health-check : GET /ping on :8080
• Demo buttons + /plans menu
"""
#  <----- imports & config stay the same ----->

# ── 4 · UI helpers ─────────────────────────────────────────
def _plans_keyboard() -> InlineKeyboardMarkup:
    """Keyboard with the paid credit packs (keyword args only)."""
    rows: list[list[InlineKeyboardButton]] = []
    for plan, info in PLANS.items():
        rows.append([
            InlineKeyboardButton(
                text=f"{plan.title()} – {info['credits']} scores  (⭐{info['stars']})",
                callback_data=f"buy_{plan}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── 5 · /start & demo buttons ──────────────────────────────
@dp.message(Command("start"))
async def cmd_start(msg: Message):
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

#  <----- rest of file unchanged ----->
