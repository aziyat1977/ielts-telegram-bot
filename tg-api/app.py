# tg-api/app.py — FastAPI Telegram webhook → RAG Coach
import os, json, urllib.request, urllib.error
from pathlib import Path
from fastapi import FastAPI, Header, Request
from pydantic import BaseModel

BOT_TOKEN    = os.environ.get("TELEGRAM_BOT_TOKEN","").strip()
SECRET_TOKEN = os.environ.get("TELEGRAM_SECRET_TOKEN","").strip()
COACH_URL    = os.environ.get("COACH_API_URL","").strip()
if not BOT_TOKEN or not SECRET_TOKEN or not COACH_URL:
    raise RuntimeError("Missing env: TELEGRAM_BOT_TOKEN / TELEGRAM_SECRET_TOKEN / COACH_API_URL")

API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = FastAPI(title="TG Webhook → RAG Coach", version="0.1.0")

def http_json(url, payload=None, headers=None, timeout=30):
    hs = {"Content-Type":"application/json"}
    if headers: hs.update(headers)
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=hs)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def send_message(chat_id, text):
    return http_json(f"{API_BASE}/sendMessage", {"chat_id": chat_id, "text": text, "parse_mode":"Markdown"})

class Update(BaseModel):
    update_id: int | None = None
    message: dict | None = None
    edited_message: dict | None = None
    # (other fields omitted)

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/tg/webhook")
async def tg_webhook(req: Request, update: Update, x_telegram_bot_api_secret_token: str | None = Header(None)):
    # Verify Telegram secret header
    if (x_telegram_bot_api_secret_token or "") != SECRET_TOKEN:
        return {"ok": False, "error": "unauthorized"}
    msg = (update.message or {}) 
    chat = (msg.get("chat") or {}).get("id")
    text = (msg.get("text") or "").strip()
    if not chat:
        return {"ok": True}  # ignore
    # Build grounded guidance
    try:
        coach_resp = http_json(COACH_URL, {"query": text})
        bullets = coach_resp.get("summary_bullets") or []
        rationale = coach_resp.get("rationale","")
        reply = "*Grounded coach*\n" + "\n".join(bullets[:3])
        if rationale:
            reply += f"\n\n_{rationale}_"
    except Exception as e:
        reply = "Sorry—coach backend unavailable."
    try:
        send_message(chat, reply[:3900])
    except Exception as e:
        pass
    return {"ok": True}
