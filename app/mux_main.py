from fastapi import FastAPI, Request, HTTPException
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Update

# Routers (keep everything you already have)
from .bot.handlers import router as core_router
try:
    from .bot.payments import router as payments_router
except Exception:
    payments_router = None

app = FastAPI()
BOT_TOKEN = os.getenv("BOT_TOKEN") or ""
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET") or ""

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(core_router)
if payments_router:
    dp.include_router(payments_router)

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/webhook")
async def webhook(request: Request):
    # Enforce Telegram secret header when configured
    if WEBHOOK_SECRET:
        got = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if got != WEBHOOK_SECRET:
            raise HTTPException(status_code=401, detail="bad secret header")
    data = await request.json()
    try:
        update = Update.model_validate(data)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid update payload")
    await dp.feed_update(bot, update)
    return {"ok": True}