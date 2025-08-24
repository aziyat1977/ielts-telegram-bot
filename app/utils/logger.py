from loguru import logger
import os

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".run", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app.log")

logger.remove()
logger.add(LOG_FILE, rotation="2 MB", retention=7, enqueue=True, backtrace=False, diagnose=False)
