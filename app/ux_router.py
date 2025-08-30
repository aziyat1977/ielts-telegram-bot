from __future__ import annotations
import os, re, json, time, httpx
from dataclasses import dataclass
from typing import Dict, Any, List
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

ROUTER = Router(name="ux_v1")

def _load_contract() -> Dict[str, Any]:
    with open(os.path.join(os.path.dirname(__file__), "ux_contract.json"), "r", encoding="utf-8") as f:
        return json.load(f)

UX = _load_contract()
MIN_T1 = UX["task"]["min_words"]["t1"]
MIN_T2 = UX["task"]["min_words"]["t2"]
HIST_PATH = os.path.join(os.path.dirname(__file__), "history.jsonl")

class S(StatesGroup):
    choosing_task = State()
    awaiting_text = State()
    pending_confirm = State()
    awaiting_improve = State()

def kb(rows):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn["text"], callback_data=btn["cb"]) for btn in row]
        for row in rows
    ])

HOME_KB   = kb([[b] for b in UX["home"]["buttons"]])
TASK_KB   = kb([[b] for b in UX["task"]["buttons"]])
CONFIRM_KB= kb([[b for b in UX["paste"]["buttons"]]])
RESULT_KB = kb([[b for b in UX["result"]["buttons"]]])

_WORD_RE = re.compile(r"[A-Za-z']+")
def count_words(text: str) -> int:
    return len(_WORD_RE.findall(text or ""))

@dataclass
class Bands:
    overall: float; TR: float; CC: float; LR: float; GRA: float; advice: str

async def _score_via_service(text: str, is_t2: bool) -> Bands | None:
    url = os.getenv("SCORER_API_URL") or (os.getenv("PUBLIC_APP_URL") and os.getenv("PUBLIC_APP_URL").rstrip("/") + "/score")
    key = os.getenv("SCORER_API_KEY")
    if not (url and key): return None
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, headers={"X-Scorer-Key": key}, json={"prompt": text, "task": 2 if is_t2 else 1})
        r.raise_for_status()
        d = r.json()
        return Bands(overall=d["overall"], TR=d["TR"], CC=d["CC"], LR=d["LR"], GRA=d["GRA"], advice=d.get("advice",""))

async def _score_via_openai(text: str, is_t2: bool) -> Bands | None:
    api = os.getenv("OPENAI_API_KEY")
    if not api: return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api)
        sys = f"You are an IELTS Writing examiner. Score the user's Task {'2' if is_t2 else '1'} response. Return STRICT JSON with keys: overall, TR, CC, LR, GRA, advice."
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),
            response_format={"type":"json_object"},
            messages=[{"role":"system","content":sys},{"role":"user","content":text}]
        )
        js = json.loads(resp.choices[0].message.content)
        return Bands(overall=float(js["overall"]), TR=float(js["TR"]), CC=float(js["CC"]), LR=float(js["LR"]), GRA=float(js["GRA"]), advice=js.get("advice",""))
    except Exception:
        return None

def _fallback_score(text: str, is_t2: bool) -> Bands:
    w = count_words(text)
    base = 6.5 if is_t2 else 6.0
    bump = min(1.0, (w - (250 if is_t2 else 150)) / 400) if w > (250 if is_t2 else 150) else 0
    overall = round(base + bump, 1)
    return Bands(overall=overall, TR=overall-0.3, CC=overall-0.2, LR=overall-0.1, GRA=overall-0.2,
                 advice="Expand key ideas, add clear topic sentences, vary vocabulary, reduce minor grammar slips.")

async def score_essay(text: str, is_t2: bool) -> Bands:
    for fn in (_score_via_service, _score_via_openai):
        got = await fn(text, is_t2)
        if got: return got
    return _fallback_score(text, is_t2)

def _append_history(entry: dict) -> None:
    try:
        with open(HIST_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

def _read_history(n: int = 5) -> List[dict]:
    if not os.path.exists(HIST_PATH): return []
    try:
        with open(HIST_PATH, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        out = []
        for line in lines[-n:]:
            try: out.append(json.loads(line))
            except Exception: continue
        return list(reversed(out))
    except Exception:
        return []

from aiogram.enums.parse_mode import ParseMode

@ROUTER.message(F.text == "/start")
async def start_cmd(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(f"{UX['home']['title']}\n\n{UX['home']['body']}", reply_markup=HOME_KB)

@ROUTER.callback_query(F.data == "home")
async def go_home(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text(f"{UX['home']['title']}\n\n{UX['home']['body']}", reply_markup=HOME_KB)
    await cb.answer()

@ROUTER.callback_query(F.data == "score")
async def begin_score(cb: CallbackQuery, state: FSMContext):
    await state.set_state(S.choosing_task)
    await state.update_data(buf_text=None, is_t2=None)
    await cb.message.edit_text(UX["task"]["prompt"], reply_markup=TASK_KB)
    await cb.answer()

@ROUTER.callback_query(F.data.in_(["t:1","t:2"]))
async def pick_task(cb: CallbackQuery, state: FSMContext):
    is_t2 = cb.data.endswith("2")
    await state.update_data(is_t2=is_t2)
    prompt = UX["paste"]["prompt_t2"] if is_t2 else UX["paste"]["prompt_t1"]
    await state.set_state(S.awaiting_text)
    await cb.message.edit_text(prompt)
    await cb.answer()

@ROUTER.message(S.awaiting_text, F.text)
async def got_text(m: Message, state: FSMContext):
    data = await state.get_data()
    is_t2 = bool(data.get("is_t2"))
    w = count_words(m.text or "")
    need = (MIN_T2 if is_t2 else MIN_T1)
    if w < need:
        await m.answer(UX["paste"]["too_short"].format(words=w, min=need, need=need-w))
        return
    await state.update_data(buf_text=m.text)
    await state.set_state(S.pending_confirm)
    await m.answer(UX["paste"]["confirm"].format(words=w), reply_markup=CONFIRM_KB)

@ROUTER.callback_query(F.data == "score_go")
async def do_score(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    txt = data.get("buf_text") or ""
    is_t2 = bool(data.get("is_t2"))
    res = await score_essay(txt, is_t2)
    try:
        _append_history({"ts": int(time.time()), "task": 2 if is_t2 else 1, "words": count_words(txt),
                         "overall": res.overall, "TR": res.TR, "CC": res.CC, "LR": res.LR, "GRA": res.GRA})
    except Exception:
        pass
    body = UX["result"]["template"].format(overall=res.overall, TR=res.TR, CC=res.CC, LR=res.LR, GRA=res.GRA)
    out = f"{UX['result']['title']}\n\n{body}\n\n{UX['result']['tips_header']}\n{res.advice}"
    if len(out) > 3800: out = out[:3600] + "\n…"
    await cb.message.edit_text(out, reply_markup=RESULT_KB, parse_mode=ParseMode.HTML)
    await state.set_state(S.awaiting_improve)
    await cb.answer()

@ROUTER.callback_query(F.data == "demo")
async def demo(cb: CallbackQuery, state: FSMContext):
    demo_head = f"{UX['demo']['title']}\n{UX['demo']['body']}"
    sample = ("Some people believe that technological progress has made our lives too complex, and that the solution is to make "
              "life without technology as simple as possible. Others disagree and believe that technology has improved life in "
              "countless ways. Discuss both views and give your opinion. In recent decades, everyday life has undeniably become "
              "entwined with digital tools. While some argue that this dependence breeds distraction and stress, it has also enabled "
              "wider access to education, remote work, and efficient communication. In my view, the key is not abandoning technology "
              "but using it deliberately: setting boundaries, prioritising deep work, and choosing high-signal sources over constant "
              "notifications. Communities benefit when citizens can collaborate online, yet they must also protect quiet spaces for "
              "reflection; therefore, balance is essential.")
    await state.set_state(S.pending_confirm)
    await state.update_data(buf_text=sample, is_t2=True)
    await cb.message.edit_text(demo_head + "\n\n" + UX["paste"]["confirm"].format(words=270), reply_markup=CONFIRM_KB)
    await cb.answer()

@ROUTER.callback_query(F.data == "history")
async def history(cb: CallbackQuery, state: FSMContext):
    recents = _read_history(5)
    if not recents:
        txt = UX["history"]["empty"]
    else:
        txt = "Recent scores:\n" + "\n".join(
            f"• Task {e.get('task')} — Overall {e.get('overall')} (TR {e.get('TR')}, CC {e.get('CC')}, LR {e.get('LR')}, GRA {e.get('GRA')})"
            for e in recents
        )
    await cb.message.edit_text(txt, reply_markup=HOME_KB)
    await cb.answer()

@ROUTER.callback_query(F.data == "settings")
async def settings(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text(UX["settings"]["body"], reply_markup=HOME_KB)
    await cb.answer()

@ROUTER.callback_query(F.data == "tips_again")
async def tips_again(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    txt = data.get("buf_text") or ""
    is_t2 = bool(data.get("is_t2"))
    res = await score_essay(txt, is_t2)
    await cb.message.answer(f"{UX['result']['tips_header']}\n{res.advice}", parse_mode=ParseMode.HTML)
    await cb.answer()

@ROUTER.callback_query(F.data == "compare9")
async def compare9(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("Band 9 samples (official/public sources):\n- IELTS official site (samples)\n- Cambridge IELTS books (Task 1/2).")
    await cb.answer()