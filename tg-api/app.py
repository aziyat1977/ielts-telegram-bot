# tg-api/app.py — Sprint 9 hardened webhook
import os, json, time, threading, urllib.request, logging
from fastapi import FastAPI, Header, Request, HTTPException
from pydantic import BaseModel

BOT_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
SECRET_TOKEN = os.getenv("TELEGRAM_SECRET_TOKEN","").strip()
COACH_URL    = os.getenv("COACH_API_URL","").strip()  # may be empty (graceful fallback)

if not BOT_TOKEN or not SECRET_TOKEN:
    raise RuntimeError("Missing env: TELEGRAM_BOT_TOKEN / TELEGRAM_SECRET_TOKEN")

API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Logging & in-process metrics
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
METRICS = {"total": 0, "errors": 0}
RATE    = {}    # chat_id -> timestamps[]
LOCK    = threading.Lock()
RATE_LIMIT  = int(os.getenv("RATE_LIMIT", "5"))      # messages
RATE_WINDOW = int(os.getenv("RATE_WINDOW", "60"))    # seconds

app = FastAPI(title="TG Webhook → RAG Coach (Sprint 9)", version="0.1.2")

class Update(BaseModel):
    update_id: int | None = None
    message: dict | None = None
    edited_message: dict | None = None

def http_json(url, payload=None, timeout=30):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req  = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def send_message(chat_id, text):
    try:
        return http_json(f"{API_BASE}/sendMessage", {"chat_id": chat_id, "text": text, "parse_mode":"Markdown"})
    except Exception as e:
        logging.error(f"Send error: {e}")

@app.get("/debug/ping")
def debug_ping():
    # show current metrics and rate keys
    return {"ok": True, "metrics": METRICS, "rate_keys": list(RATE.keys()), "has_coach": bool(COACH_URL)}

@app.post("/tg/webhook")
async def tg_webhook(update: Update, x_telegram_bot_api_secret_token: str | None = Header(None)):
    # Secret token verification (Telegram sends X-Telegram-Bot-Api-Secret-Token)
    # https://core.telegram.org/bots/api#setwebhook (secret_token)
    if (x_telegram_bot_api_secret_token or "") != SECRET_TOKEN:
        raise HTTPException(401, "unauthorized")

    METRICS["total"] += 1
    msg  = (update.message or {})
    chat = (msg.get("chat") or {}).get("id")
    text = (msg.get("text") or "").strip()

    if not chat:
        return {"ok": True}

    # Per-chat rate limiting
    now = time.time()
    with LOCK:
        q = [ts for ts in RATE.get(chat, []) if now - ts < RATE_WINDOW]
        if len(q) >= RATE_LIMIT:
            logging.warning(f"Rate limit exceeded for chat {chat}")
            raise HTTPException(429, "Rate limit exceeded")
        q.append(now); RATE[chat] = q

    logging.info(f"msg chat={chat} text={text!r}")

    reply = ""
    try:
        if COACH_URL:
            coach = http_json(COACH_URL, {"query": text})
            bullets = (coach.get("summary_bullets") or [])[:3]
            rationale = coach.get("rationale","")
            reply = "*Grounded coach*\n" + "\n".join(bullets)
            if rationale: reply += f"\n\n_{rationale}_"
        else:
            reply = "Coach not configured yet. Ask your admin to set COACH_API_URL."
    except Exception as e:
        METRICS["errors"] += 1
        logging.error(f"coach error: {e}")
        reply = "Sorry—coach unavailable."

    send_message(chat, reply[:3900])
    return {"ok": True}
