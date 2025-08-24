from pydantic import BaseModel
from dotenv import load_dotenv
import os
load_dotenv()
class Settings(BaseModel):
    bot_token: str = os.getenv("BOT_TOKEN","")
    openai_key: str = os.getenv("OPENAI_API_KEY","")
    webhook_secret: str = os.getenv("WEBHOOK_SECRET","")
    app_base_url: str = os.getenv("APP_BASE_URL","http://127.0.0.1:8080")
    stars_mode: bool = os.getenv("STARS_MODE","on").lower() in {"1","true","yes","on"}
    upstash_url: str | None = os.getenv("UPSTASH_REDIS_REST_URL")
    upstash_token: str | None = os.getenv("UPSTASH_REDIS_REST_TOKEN")
S = Settings()
assert S.bot_token, "BOT_TOKEN missing"
assert S.webhook_secret, "WEBHOOK_SECRET missing"
