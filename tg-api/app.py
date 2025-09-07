# tg-api/app.py — logs, metrics, ping, in-memory per-chat rate limiter, reset_webhook
import os, json, time, threading, urllib.request, logging
from fastapi import FastAPI, Header, Request, HTTPException
from pydantic import BaseModel

BOT_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN","")
SECRET_TOKEN = os.getenv("TELEGRAM_SECRET_TOKEN","")
COACH_URL    = os.getenv("COACH_API_URL","")
if not BOT_TOKEN or not SECRET_TOKEN or not COACH_URL:
    raise RuntimeError("Missing env: TELEGRAM_BOT_TOKEN/SECRET/COACH")

API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
app = FastAPI(title="TG Webhook → RAG Coach (Sprint 9)")

logging.basicConfig(level=logging.INFO)
METRICS = {"total": 0, "errors": 0}
RATE = {}
LOCK = threading.Lock()
RATE_LIMIT = 5  # max messages
RATE_WINDOW = 60  # seconds

class Update(BaseModel):
    update_id: int|None = None
    message: dict|None = None

@app.get("/debug/ping")
def ping():
    return {"ok": True, "metrics": METRICS, "rate_keys": list(RATE.keys())}

def http_json(url,payload=None,timeout=30):
    data=json.dumps(payload).encode("utf-8") if payload else None
    req=urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return json.loads(r.read().decode())

@app.post("/tg/webhook")
async def tg_webhook(req: Request, update: Update, x_telegram_bot_api_secret_token: str|None = Header(None)):
    METRICS["total"] += 1
    chat = (update.message or {}).get("chat",{}).get("id")
    text = (update.message or {}).get("text","")
    now = time.time()
    with LOCK:
        q = RATE.get(chat, [])
        q = [ts for ts in q if now - ts < RATE_WINDOW]
        if len(q) >= RATE_LIMIT:
            raise HTTPException(429, "Rate limit exceeded")
        q.append(now)
        RATE[chat] = q
    logging.info(f"Msg from {chat}: {text}")
    try:
        resp = http_json(COACH_URL, {"query": text})
        bullets = resp.get("summary_bullets", [])[:3]
        rationale = resp.get("rationale","")
        reply = "*Grounded coach*\n" + "\n".join(bullets)
        if rationale: reply += f"\n\n_{rationale}_"
    except Exception as e:
        METRICS["errors"] +=1
        logging.error(f"Coach error: {e}")
        reply = "Sorry—coach unavailable."
    try:
        http_json(f"{API_BASE}/sendMessage", {"chat_id": chat, "text": reply[:3900], "parse_mode":"Markdown"})
    except Exception as e:
        logging.error(f"Send error: {e}")
    return {"ok": True}

# reset_webhook utility is provided as a separate PS script.
