import time, uuid, hashlib, hmac
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.utils import config

router = APIRouter()

@router.get("/_whoami")
async def whoami():
    return {
        "ok": True,
        "merchant_id": bool(config.PAYME_MERCHANT_ID),
        "secret": bool(config.PAYME_SECRET_KEY),
    }

@router.get("/create")
async def create(amount: int, chat_id: int = 0, description: str = "IELTS Bot"):
    """
    Stubbed Payme create; returns a payload you can send to Payme API/UI.
    When creds exist, you can sign/forward server-side as needed.
    """
    invoice_id = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    payload = {
        "merchant_id": config.PAYME_MERCHANT_ID,
        "amount": amount,   # integer UZS
        "account": {"chat_id": chat_id, "invoice_id": invoice_id},
        "description": description,
        "return_url": f"{config.APP_BASE_URL}/health",
    }
    return {"ok": True, "provider":"payme", "payload": payload, "hint":"Send this to Payme API or use their widget."}

@router.post("/callback")
async def callback(req: Request):
    """
    Accepts Payme callback; echoes JSON; placeholder for signature verification
    """
    try:
        data = await req.json()
    except:
        data = {"raw": (await req.body()).decode("utf-8","ignore")}
    # TODO: when PAYME_SECRET_KEY present, verify per Payme spec
    return {"ok": True, "echo": data}
