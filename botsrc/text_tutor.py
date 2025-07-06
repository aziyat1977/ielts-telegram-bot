import textwrap, os, json
from aiogram import Bot, types
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from quota import consume_credit_if_needed
from scorer import score_essay_or_voice_async     # your existing helper

# ========== PROMPTS ========== #
TASK_MENU = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton("Task 1 – Academic 📊", callback_data="t1_a"),
    InlineKeyboardButton("Task 1 – General ✉️", callback_data="t1_g"),
    InlineKeyboardButton("Task 2 – Essay 📝",   callback_data="t2"),
]])
STYLE_MENU = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton("Section-based",  callback_data="fb_section"),
    InlineKeyboardButton("Sentence inline",callback_data="fb_inline"),
]])
BAND_MENU = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton("6",   callback_data="band6"),
    InlineKeyboardButton("6.5", callback_data="band6_5"),
    InlineKeyboardButton("7",   callback_data="band7"),
    InlineKeyboardButton("7.5", callback_data="band7_5"),
    InlineKeyboardButton("8+",  callback_data="band8"),
]])

# ========== STATE CACHE ========== #
# very light in-memory dict {user_id: {task,style,band}} – sufficient for MVP
_SESSION: dict[int, dict] = {}

def _prompt_key(u: types.User) -> int: return u.id   # one session per user

async def _ensure_quota(user_id: int, msg: types.Message) -> bool:
    ok = await consume_credit_if_needed(user_id, cost=1)
    if not ok:
        await msg.answer("⚠️ No credits left. Use /plans to top-up.")
    return ok

# ========== COMMAND ENTRYPOINT ========== #
async def cmd_tutor_text(message: types.Message, bot: Bot):
    _SESSION[_prompt_key(message.from_user)] = {}    # reset
    await message.answer("Which IELTS writing task?", reply_markup=TASK_MENU)

# ========== INLINE CALLBACK STEPS ========== #
async def process_callback(cb: CallbackQuery, bot: Bot):
    sid = _prompt_key(cb.from_user)
    sess = _SESSION.setdefault(sid, {})
    data = cb.data
    await cb.answer()

    # 1) Task choice
    if data in {"t1_a", "t1_g", "t2"}:
        sess["task"] = data
        await cb.message.answer("Choose feedback style:", reply_markup=STYLE_MENU)

    # 2) Style choice
    elif data.startswith("fb_"):
        sess["style"] = data
        await cb.message.answer("Target band?", reply_markup=BAND_MENU)

    # 3) Band choice → ask for text
    elif data.startswith("band"):
        sess["band"] = data.replace("band", "").replace("_", ".")
        await cb.message.answer(
            "Great! Now reply to your essay (or paste it) and send /text_go"
        )

# ========== /text_go – do the work ========== #
async def cmd_text_go(msg: types.Message, bot: Bot):
    sid  = _prompt_key(msg.from_user)
    sess = _SESSION.get(sid)
    if not sess or "band" not in sess:
        return await msg.answer("Start with /tutor_text to choose options first!")

    # grab the essay text
    essay = (msg.text.split(maxsplit=1)[1:] or [""])[0].strip() \
            if msg.text.startswith("/text_go") else msg.text
    if not essay:
        return await msg.answer("❔ Paste your essay after /text_go or reply with it.")

    if not await _ensure_quota(msg.from_user.id, msg):
        return

    # build system prompt
    task_map = {"t1_a":"Task 1 Academic","t1_g":"Task 1 General","t2":"Task 2 Essay"}
    style = "section-based critique" if sess["style"]=="fb_section" else \
            "sentence-level inline feedback"
    sys_prompt = (
      f"You are an IELTS examiner. Assess the user's {task_map[sess['task']]} "
      f"according to official IELTS criteria. Provide {style}. "
      f"Target band goal {sess['band']}. "
      "Use headings for each criterion, bullet points for issues, "
      "and show corrected versions where relevant."
    )

    res = await score_essay_or_voice_async(essay, system_msg=sys_prompt)
    feedback = res["tips"] if isinstance(res["tips"], str) else "\n".join(res["tips"])
    feedback = f"<b>Predicted Band {res['band']}</b>\n\n{feedback}"
    await msg.answer(feedback, parse_mode="HTML")

    # tidy
    _SESSION.pop(sid, None)
