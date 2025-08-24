import hashlib, time
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from app.utils import config

router = APIRouter()

def _md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()

@router.get("/_whoami")
async def whoami():
    return {"ok": True, "service_id": config.CLICK_SERVICE_ID != "", "secret": config.CLICK_SECRET != ""}

@router.get("/create")
async def create(amount: int = Query(..., ge=1000), chat_id: int = 0, comment: str = "IELTS Bot"):
    """
    Returns a ready payload and signature for Click link/button creation.
    If creds missing, still returns deterministic fields for testing.
    """
    merchant_trans_id = f"{int(time.time())}-{chat_id or 0}"
    payload = {
        "service_id": config.CLICK_SERVICE_ID,
        "merchant_trans_id": merchant_trans_id,
        "amount": amount,
        "comment": comment,
        "return_url": f"{config.APP_BASE_URL}/health"
    }
    sig_base = f"{config.CLICK_SERVICE_ID}{config.CLICK_SECRET}{merchant_trans_id}{amount}"
    signature = _md5(sig_base) if config.CLICK_SERVICE_ID and config.CLICK_SECRET else ""
    debug = {
        "sig_base": sig_base,
        "signature": signature,
    }
    return {"ok": True, "provider":"click", "payload": payload, "debug": debug, "hint": "Open this payload in your Click form/button."}

@router.post("/callback")
async def callback(req: Request):
    """
    Accepts Click callback. Verifies signature when creds are present.
    Echoes JSON for debugging; never 502.
    """
    data = await req.form()
    d = {k: data.get(k) for k in data.keys()}
    # Expected: sign = md5(service_id + secret + merchant_trans_id + amount)
    claimed = d.get("sign") or ""
    merchant_trans_id = d.get("merchant_trans_id") or ""
    amount = int(d.get("amount") or 0)
    if config.CLICK_SERVICE_ID and config.CLICK_SECRET:
        sig_base = f"{config.CLICK_SERVICE_ID}{config.CLICK_SECRET}{merchant_trans_id}{amount}"
        valid = _md5(sig_base)
        if claimed != valid:
            return JSONResponse({"ok": False, "error": "bad-signature", "expected": valid, "claimed": claimed}, status_code=400)
    return {"ok": True, "echo": d}
