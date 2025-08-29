# === MERGE WRAPPER: Telegram webhook + Writing UX; real app mounted at /app ===
import os, importlib, contextlib, asyncio, httpx, html
from fastapi import FastAPI, Request, HTTPException
from starlette.responses import PlainTextResponse
app = FastAPI()
SECRET=os.getenv("TELEGRAM_WEBHOOK_SECRET",""); TOKEN=os.getenv("TELEGRAM_BOT_TOKEN",""); API=f"https://api.telegram.org/bot{TOKEN}" if TOKEN else ""
with contextlib.suppress(Exception): from writing_api import score_text
STATE={}
def esc(s:str)->str: return html.escape(s or "")
async def tg_send(chat_id, text, reply_markup=None):
    if not TOKEN: return
    payload={"chat_id":chat_id,"text":text,"parse_mode":"HTML","disable_web_page_preview":True}
    if reply_markup: payload["reply_markup"]=reply_markup
    async with httpx.AsyncClient(timeout=10) as cli: await cli.post(f"{API}/sendMessage", json=payload)
def menu_keyboard():
    return {"inline_keyboard":[[{"text":"Task 2 Essay","callback_data":"task2"},{"text":"Task 1 Report","callback_data":"task1"},{"text":"GT Letter","callback_data":"gt_letter"}],[{"text":"Help","callback_data":"help"}]]}
@app.get("/health")
def health(): return {"ok":True}
@app.get("/version")
def version(): return {"name":"ielts-bot","mode":"merge+writing","v":"ci-prebuilt"}
def _check_secret(req: Request):
    tok=req.headers.get("X-Telegram-Bot-Api-Secret-Token");
    if SECRET and tok != SECRET: raise HTTPException(status_code=401, detail="bad secret")
def _word_count(s:str)->int:
    import re; return len(re.findall(r"[A-Za-z']+", s or ""))
async def handle_command(chat_id:int, txt:str):
    t=(txt or "").strip().lower()
    if t.startswith("/start") or t=="/writing":
        STATE[chat_id]={"mode":"idle"}; await tg_send(chat_id,"Welcome! Choose your writing type:",reply_markup=menu_keyboard())
    elif t=="/cancel":
        STATE.pop(chat_id,None); await tg_send(chat_id,"Canceled. Type /start to begin.")
    else:
        await tg_send(chat_id,"Send /start to begin the IELTS Writing scorer.")
async def handle_callback(chat_id:int, data:str):
    if data in ("task2","task1","gt_letter"):
        STATE[chat_id]={"mode":"await_text","task_type":data}; need="≥250 words" if data=="task2" else "≥150 words"
        await tg_send(chat_id,f"Paste your answer ({need}). Optionally first line: <b>Topic:</b> ...")
    elif data=="help":
        await tg_send(chat_id,"We score TA/TR, CC, LR, GRA using public descriptors. AI-style check is an indicator only.")
    else:
        await tg_send(chat_id,"Unknown action.")
async def run_scoring(chat_id:int, task_type:str, text:str):
    topic=None; lines=(text or "").splitlines()
    if lines and lines[0].strip().lower().startswith("topic:"): topic=lines[0].split(":",1)[1].strip(); text="\n".join(lines[1:]).strip()
    try: result=score_text(task_type,text,topic,ai_style=True)
    except Exception as e: await tg_send(chat_id,f"Scoring error: {esc(str(e))}"); return
    s=result.get("scores",{}); ai=result.get("ai_style",{})
    msg=f"<b>Your bands</b>\nTA/TR: <b>{s.get('TA_TR')}</b> | CC: <b>{s.get('CC')}</b> | LR: <b>{s.get('LR')}</b> | GRA: <b>{s.get('GRA')}</b>\n<b>Overall:</b> {s.get('overall')}" + (f"\n<i>AI-style:</i> {esc(ai.get('level','n/a'))}" + (f" — {esc(', '.join(ai.get('signals',[])[:2]))}" if ai.get('signals') else "" ))
    await tg_send(chat_id,msg)
    R=result.get("rationale",{}); parts=[]
    for k in ("TA_TR","CC","LR","GRA"):
        r=R.get(k) or {}; band=r.get("band"); why=(r.get("why","") or "").strip(); fix=(r.get("fix","") or "").strip()
        p=f"<b>{k}</b> {band}: {esc(why)}";  p+=f"\n– Fix: {esc(fix)}" if fix else ""; parts.append(p)
    await tg_send(chat_id,"\n\n".join(parts)[:3800])
async def process_update(data:dict):
    cq=data.get("callback_query")
    if cq: chat_id=cq["message"]["chat"]["id"]; await handle_callback(chat_id,cq.get("data","")); return
    msg=data.get("message") or data.get("edited_message") or {}; chat=msg.get("chat") or {}; chat_id=chat.get("id")
    if not chat_id: return
    txt=(msg.get("text") or "").strip()
    if txt.startswith("/"): await handle_command(chat_id,txt); return
    st=STATE.get(chat_id) or {}
    if st.get("mode")=="await_text":
        task_type=st.get("task_type","task2"); need=250 if task_type=="task2" else 150; wc=_word_count(txt)
        if wc < need: await tg_send(chat_id,f"Too short ({wc} words). Need at least {need}."); return
        STATE[chat_id]={"mode":"idle"}; await tg_send(chat_id,"Scoring…"); asyncio.create_task(run_scoring(chat_id,task_type,txt))
    else:
        await tg_send(chat_id,"✅ IELTS bot is alive.\nSend /start to try the Writing scorer.")
async def _handle_update(req: Request):
    _check_secret(req); data={}
    with contextlib.suppress(Exception): data=await req.json()
    asyncio.create_task(process_update(data if isinstance(data,dict) else {}))
    return PlainTextResponse("ok", status_code=200)
@app.post("/telegram")
async def telegram_webhook(req: Request): return await _handle_update(req)
@app.post("/webhook")
async def telegram_webhook_alt(req: Request): return await _handle_update(req)
if os.getenv("FF_WRITING_UX","1") != "0":
    from writing_api import router as writing_router; app.include_router(writing_router)
def _load_real():
    for modpath in ("main","app","src.main","backend.main","server.main","api.main","application.main"):
        with contextlib.suppress(Exception):
            mod=importlib.import_module(modpath); real=getattr(mod,"app",None)
            if real is not None: return real
    return None
_real=_load_real()
if _real is not None: app.mount("/app", _real)
# === END ===
