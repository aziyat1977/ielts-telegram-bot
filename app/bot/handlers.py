from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
import os, asyncio
from .ratelimit import allow, reason
from .entitlements import is_pro, ttl_days, grant, extend, revoke
from .ielts_writing import grade_writing, render_markdown
from .ielts_speaking import get_file_url, transcribe_file_url, grade_speaking, render_speaking_md
from .quota import take, remaining_today
from .metrics import (
    mark_user, bump, dau_today, get_today, ref_hit, top_refs, ref_hits_today,
    _days_utc, get_for_day, dau_for_day, top_refs_for_day, all_refs_for_day
)
from .referrals import set_referrer, get_referrer
from .mdsafe import escape_md as esc_md
from .privacy_tools import erase_user_data

router = Router(name="core")

HELP_TEXT = (
    "🤖 *IELTS Rater Bot*\n"
    "• Send a Task 2 essay (≥50 chars) or a voice note.\n"
    "• Free preview: 1 essay + 1 voice daily.\n"
    "• Use /buy to unlock *Pro* (30 days) with Telegram Stars.\n"
    "• Use /status to see plan + preview balance.\n"
    "• Use /ref to get your invite link.\n"
)

ADMIN_ID = int(os.getenv("ADMIN_ID") or "0")
def _owner(uid: int) -> bool: return ADMIN_ID and int(uid) == ADMIN_ID

FREE_W = 1
FREE_S = 1

# ---------- Start ----------
@router.message(CommandStart(deep_link=True))
async def start_dl(msg: types.Message, command: CommandStart):
    mark_user(msg.from_user.id)
    code = (command.args or "").strip()
    ref_hit(code)
    try:
        if code.isdigit():
            rid = int(code)
            if rid != msg.from_user.id:
                set_referrer(msg.from_user.id, rid)
    except Exception:
        pass
    await msg.answer(
        f"👋 Welcome! Ref: `{command.args}`\nSend an essay (Task 2) or a voice note to begin.",
        parse_mode="Markdown",
    )

@router.message(CommandStart())
async def start(msg: types.Message):
    mark_user(msg.from_user.id)
    await msg.answer("👋 Welcome! Send an essay (Task 2) or a voice note to begin.")

# ---------- Help/Status ----------
@router.message(Command("help"))
async def help_cmd(msg: types.Message):
    await msg.answer(HELP_TEXT, parse_mode="Markdown")

@router.message(Command("status"))
async def status_cmd(msg: types.Message):
    if is_pro(msg.from_user.id):
        days = ttl_days(msg.from_user.id)
        await msg.answer("✅ Pro is active." if days is None else f"✅ Pro is active. {days} day(s) remaining.")
    else:
        wleft = remaining_today(msg.from_user.id, "W", FREE_W)
        sleft = remaining_today(msg.from_user.id, "S", FREE_S)
        await msg.answer(f"❌ Pro inactive.\n🎁 Free previews left today — Writing: {wleft}, Speaking: {sleft}\nBuy Pro → /buy")

# ---------- Referral ----------
@router.message(Command("ref"))
async def my_ref(msg: types.Message):
    me = await msg.bot.get_me()
    link = f"https://t.me/{me.username}?start={msg.from_user.id}"
    clicks = ref_hits_today(str(msg.from_user.id))
    text = (
        "*Invite friends, get +7 days when they buy*\n"
        f"• Your link: `{link}`\n"
        f"• Today’s referral starts: {clicks}\n"
        "_(Bonus applies once per friend’s first purchase.)_"
    )
    await msg.answer(text, parse_mode="Markdown", disable_web_page_preview=True)

# ---------- Policy ----------
PRIVACY_MD = (
    "*Privacy Policy*\n"
    "We store minimal data needed to run the bot (technical logs & counters). "
    "Essays and transcripts may be processed by AI providers to generate feedback, "
    "then discarded. We never sell your data."
)
TERMS_MD = (
    "*Terms of Use*\n"
    "This bot provides automated IELTS-style feedback for study purposes only and "
    "does not guarantee exam scores. Use at your own discretion."
)

@router.message(Command("privacy"))
async def privacy_cmd(msg: types.Message):
    await msg.answer(PRIVACY_MD, parse_mode="Markdown", disable_web_page_preview=True)

@router.message(Command("terms"))
async def terms_cmd(msg: types.Message):
    await msg.answer(TERMS_MD, parse_mode="Markdown", disable_web_page_preview=True)

@router.message(Command("erase"))
async def erase_cmd(msg: types.Message):
    n = 0
    try:
        n = erase_user_data(msg.from_user.id)
    except Exception:
        n = 0
    await msg.answer(
        f"🧹 Done. Removed {n} stored key(s) linked to your account (referrals & today’s quota). This does *not* cancel Pro.",
        parse_mode="Markdown"
    )

# ---------- Admin ----------
@router.message(Command("whoami"))
async def whoami(msg: types.Message):
    await msg.answer(f"🙋 Your ID: `{msg.from_user.id}`", parse_mode="Markdown")

@router.message(Command("admin"))
async def admin_help(msg: types.Message):
    if not _owner(msg.from_user.id):
        return await msg.answer("🚫 Owner only.")
    await msg.answer(
        "🔐 *Admin*\n"
        "• /grant7 [user_id] — grant 7 days (reply or pass user_id)\n"
        "• /grant30 [user_id] — grant 30 days\n"
        "• /revoke [user_id] — revoke Pro\n"
        "• /stats — usage today\n"
        "• /stats7 — 7-day CSV\n"
        "• /stats30 — 30-day CSV\n"
        "• /refs30 — referrals (30-day CSV)\n",
        parse_mode="Markdown"
    )

def _target_uid(msg: types.Message) -> int | None:
    if msg.reply_to_message and msg.reply_to_message.from_user:
        return msg.reply_to_message.from_user.id
    parts = (msg.text or "").split()
    if len(parts) > 1 and parts[1].isdigit():
        return int(parts[1])
    return msg.from_user.id

@router.message(Command("grant7"))
async def grant7_cmd(msg: types.Message):
    if not _owner(msg.from_user.id): return await msg.answer("🚫 Owner only.")
    uid = _target_uid(msg)
    ok = grant(uid, days=7)
    await msg.answer("✅ Granted 7 days." if ok else "⚠️ Failed to grant.")

@router.message(Command("grant30"))
async def grant30_cmd(msg: types.Message):
    if not _owner(msg.from_user.id): return await msg.answer("🚫 Owner only.")
    uid = _target_uid(msg)
    ok = grant(uid, days=30)
    await msg.answer("✅ Granted 30 days." if ok else "⚠️ Failed to grant.")

@router.message(Command("revoke"))
async def revoke_cmd(msg: types.Message):
    if not _owner(msg.from_user.id): return await msg.answer("🚫 Owner only.")
    uid = _target_uid(msg)
    ok = revoke(uid)
    await msg.answer("✅ Revoked." if ok else "⚠️ Failed to revoke.")

@router.message(Command("stats"))
async def stats_cmd(msg: types.Message):
    if not _owner(msg.from_user.id): return await msg.answer("🚫 Owner only.")
    dau = dau_today()
    w = get_today("writing_scored"); s = get_today("speaking_scored")
    fw = get_today("free_w_used"); fs = get_today("free_s_used")
    p = get_today("pro_purchases")
    lines = [
        "📊 *Today (UTC)*",
        f"• DAU: {dau}",
        f"• Writing graded: {w}",
        f"• Speaking graded: {s}",
        f"• Free previews used — W:{fw} S:{fs}",
        f"• Pro purchases: {p}",
    ]
    refs = top_refs()
    if refs:
        lines.append("\nTop referrals today")
        for code,score in refs: lines.append(f"• {code}: {int(score)} starts")
    await msg.answer("\n".join(lines), parse_mode="Markdown")

@router.message(Command("stats7"))
async def stats7_cmd(msg: types.Message):
    if not _owner(msg.from_user.id): return await msg.answer("🚫 Owner only.")
    import io, csv
    days = _days_utc(7)
    buf = io.StringIO(newline="")
    w = csv.writer(buf)
    w.writerow(["date_utc","dau","writing_scored","speaking_scored","free_w_used","free_s_used","pro_purchases","top_refs"])
    for d in days:
        vals = [
            d,
            dau_for_day(d),
            get_for_day("writing_scored", d),
            get_for_day("speaking_scored", d),
            get_for_day("free_w_used", d),
            get_for_day("free_s_used", d),
            get_for_day("pro_purchases", d),
        ]
        tr = top_refs_for_day(d, 5)
        vals.append(" | ".join([f"{code}:{int(score)}" for code,score in tr]) if tr else "")
        w.writerow(vals)
    data = buf.getvalue().encode("utf-8")
    try:
        await msg.answer_document(types.BufferedInputFile(data, filename=f"ielts_stats_{days[0]}_{days[-1]}.csv"), caption="📊 7-day stats (UTC).")
    except Exception:
        await msg.answer("```\n" + buf.getvalue() + "\n```", parse_mode="Markdown")

@router.message(Command("stats30"))
async def stats30_cmd(msg: types.Message):
    if not _owner(msg.from_user.id): return await msg.answer("🚫 Owner only.")
    import io, csv
    days = _days_utc(30)
    buf = io.StringIO(newline="")
    w = csv.writer(buf)
    w.writerow(["date_utc","dau","writing_scored","speaking_scored","free_w_used","free_s_used","pro_purchases","top_refs"])
    for d in days:
        vals = [
            d,
            dau_for_day(d),
            get_for_day("writing_scored", d),
            get_for_day("speaking_scored", d),
            get_for_day("free_w_used", d),
            get_for_day("free_s_used", d),
            get_for_day("pro_purchases", d),
        ]
        tr = top_refs_for_day(d, 5)
        vals.append(" | ".join([f"{code}:{int(score)}" for code,score in tr]) if tr else "")
        w.writerow(vals)
    data = buf.getvalue().encode("utf-8")
    try:
        await msg.answer_document(types.BufferedInputFile(data, filename=f"ielts_stats_{days[0]}_{days[-1]}.csv"), caption="📊 30-day stats (UTC).")
    except Exception:
        await msg.answer("```\n" + buf.getvalue() + "\n```", parse_mode="Markdown")

@router.message(Command("refs30"))
async def refs30_cmd(msg: types.Message):
    if not _owner(msg.from_user.id): return await msg.answer("🚫 Owner only.")
    import io, csv
    days = _days_utc(30)
    buf = io.StringIO(newline="")
    w = csv.writer(buf)
    w.writerow(["date_utc","code","starts"])
    for d in days:
        rows = all_refs_for_day(d)
        if rows:
            for code,score in rows:
                w.writerow([d, code, int(score)])
        else:
            w.writerow([d, "", 0])
    data = buf.getvalue().encode("utf-8")
    try:
        await msg.answer_document(types.BufferedInputFile(data, filename=f"ielts_refs_{days[0]}_{days[-1]}.csv"), caption="🔗 30-day referrals (UTC).")
    except Exception:
        await msg.answer("```\n" + buf.getvalue() + "\n```", parse_mode="Markdown")

# ---------- Writing ----------
@router.message(F.text.len() > 50)
async def writing(msg: types.Message):
    mark_user(msg.from_user.id)
    if not allow(msg.from_user.id):
        return await msg.answer(reason or "Too many requests, try again shortly.")
    if is_pro(msg.from_user.id):
        await msg.bot.send_chat_action(msg.chat.id, "typing")
        await msg.answer("✍️ Scoring your essay…")
        try:
            result = await asyncio.to_thread(grade_writing, msg.text)
            bump("writing_scored")
            await msg.answer(render_markdown(result), parse_mode="Markdown")
        except Exception:
            await msg.answer("⚠️ Sorry, could not grade right now. Please try again.")
    else:
        ok, _rem = take(msg.from_user.id, "W", FREE_W)
        if not ok:
            return await msg.answer("📝 Free preview used for today.\nUnlock unlimited feedback → /buy")
        bump("free_w_used")
        await msg.bot.send_chat_action(msg.chat.id, "typing")
        await msg.answer("🎁 Free preview (1/day): scoring your essay…")
        try:
            result = await asyncio.to_thread(grade_writing, msg.text)
            bump("writing_scored")
            md = render_markdown(result) + "\n\n— Free preview. Unlock unlimited & faster → /buy"
            await msg.answer(md, parse_mode="Markdown")
        except Exception:
            await msg.answer("⚠️ Sorry, could not grade now. Try again later.")

# ---------- Speaking ----------
@router.message(F.voice)
async def speaking(msg: types.Message):
    mark_user(msg.from_user.id)
    if not allow(msg.from_user.id):
        return await msg.answer(reason or "Too many requests, try again shortly.")
    if is_pro(msg.from_user.id):
        await msg.bot.send_chat_action(msg.chat.id, "record_voice")
        await msg.answer("🎧 Transcribing your voice…")
        try:
            file_url = await asyncio.to_thread(get_file_url, msg.bot.token, msg.voice.file_id)
            transcript = await asyncio.to_thread(transcribe_file_url, file_url)
            if not transcript.strip():
                return await msg.answer("⚠️ Couldn't transcribe the audio. Please try again.")
            await msg.bot.send_chat_action(msg.chat.id, "typing")
            await msg.answer("🗣️ Scoring your speaking…")
            result = await asyncio.to_thread(grade_speaking, transcript)
            bump("speaking_scored")
            md = render_speaking_md(result, esc_md(transcript))
            await msg.answer(md, parse_mode="Markdown")
        except Exception:
            await msg.answer("⚠️ Sorry, couldn't process your voice note right now. Please try again.")
    else:
        ok, _rem = take(msg.from_user.id, "S", FREE_S)
        if not ok:
            return await msg.answer("🎙️ Free preview used for today.\nUnlock unlimited STT + feedback → /buy")
        bump("free_s_used")
        await msg.bot.send_chat_action(msg.chat.id, "record_voice")
        await msg.answer("🎁 Free preview (1/day): transcribing…")
        try:
            file_url = await asyncio.to_thread(get_file_url, msg.bot.token, msg.voice.file_id)
            transcript = await asyncio.to_thread(transcribe_file_url, file_url)
            if not transcript.strip():
                return await msg.answer("⚠️ Couldn't transcribe the audio. Please try again.")
            await msg.bot.send_chat_action(msg.chat.id, "typing")
            await msg.answer("🗣️ Scoring your speaking…")
            result = await asyncio.to_thread(grade_speaking, transcript)
            bump("speaking_scored")
            md = render_speaking_md(result, esc_md(transcript)) + "\n\n— Free preview. Unlock unlimited & faster → /buy"
            await msg.answer(md, parse_mode="Markdown")
        except Exception:
            await msg.answer("⚠️ Sorry, couldn't process your voice note right now. Please try again.")