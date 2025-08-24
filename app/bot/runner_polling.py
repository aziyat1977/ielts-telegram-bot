import asyncio, sys
from pathlib import Path

# Ensure project root (parent of "app/") is importable when run as a file
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from loguru import logger
from app.bot.main_aiogram import build_dp_and_bot

async def main():
    dp, bot = build_dp_and_bot()
    logger.info("Starting polling…")
    await dp.start_polling(bot, allowed_updates=None)

if __name__ == "__main__":
    asyncio.run(main())
