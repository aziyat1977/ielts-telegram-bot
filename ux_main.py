import os, asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from dotenv import load_dotenv
from app.ux_router import ROUTER

def env(name, default=None):
    v = os.getenv(name)
    return v if v not in (None, "") else default

def require(name):
    v = env(name)
    if not v: raise RuntimeError(f"{name} is missing")
    return v

async def main():
    load_dotenv()
    token = require("TELEGRAM_TOKEN")
    bot = Bot(token=token)
    dp = Dispatcher()
    await bot.set_my_commands([BotCommand(command="start", description="Show menu")])
    dp.include_router(ROUTER)
    print("IELTS Bot UX v1.0 — polling started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())