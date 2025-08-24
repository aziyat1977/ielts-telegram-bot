import os
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(__file__))
ENV_PATH = os.path.join(os.path.dirname(ROOT), ".env")
load_dotenv(ENV_PATH)

BOT_TOKEN       = os.getenv("BOT_TOKEN","").strip()
ADMIN_ID        = int(os.getenv("ADMIN_ID","0") or 0)
APP_BASE_URL    = os.getenv("APP_BASE_URL","").strip()     # e.g. https://yourapp.fly.dev
WEBHOOK_SECRET  = os.getenv("WEBHOOK_SECRET","").strip()
CURRENCY        = os.getenv("CURRENCY","UZS").strip()

# Click
CLICK_SERVICE_ID = os.getenv("CLICK_SERVICE_ID","").strip()
CLICK_SECRET     = os.getenv("CLICK_SECRET","").strip()

# Payme
PAYME_MERCHANT_ID = os.getenv("PAYME_MERCHANT_ID","").strip()
PAYME_SECRET_KEY  = os.getenv("PAYME_SECRET_KEY","").strip()

def require_token():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing in .env")
