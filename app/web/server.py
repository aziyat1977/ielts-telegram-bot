import os, json
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from loguru import logger
from aiogram.types import Update

from app.utils import config
from app.bot.main_aiogram import build_dp_and_bot
from app.payments.click_routes import router as click_router
from app.payments.payme_routes import router as payme_router

config.require_token()
app = FastAPI(title="IELTS Rater Bot")

# build once, reuse
dp, bot = build_dp_and_bot()

@app.get("/health")
async def health():
    payload = {
        "ok": True,
        "env": {
            "has_token": bool(config.BOT_TOKEN),
            "app_base_url": config.APP_BASE_URL,
        }
    }
    return JSONResponse(payload)

@app.post("/webhook")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str = Header(None)):
    if not config.WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="WEBHOOK_SECRET not set")
    if x_telegram_bot_api_secret_token != config.WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret header")
    body = await request.body()
    if len(body) > 2_000_000:  # 2MB safety
        raise HTTPException(status_code=413, detail="Payload too large")
    try:
        update = Update.model_validate_json(body)
    except Exception as e:
        logger.warning(f"Bad update JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    await dp.feed_update(bot, update)
    return PlainTextResponse("OK")

# payments
app.include_router(click_router, prefix="/pay/click")
app.include_router(payme_router, prefix="/pay/payme")
