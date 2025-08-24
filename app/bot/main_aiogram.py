from aiogram import Bot, Dispatcher
from app.utils import config
from app.bot.handlers.reading import router as reading_router

def build_dp_and_bot():
    config.require_token()
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(reading_router)
    return dp, bot
