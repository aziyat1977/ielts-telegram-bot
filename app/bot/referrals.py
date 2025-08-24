from __future__ import annotations
from typing import Optional
from .config import S

_r = None
try:
    if S.upstash_url and S.upstash_token:
        from upstash_redis import Redis
        _r = Redis(url=S.upstash_url, token=S.upstash_token)
except Exception:
    _r = None

_mem_ref_by: dict[int,int] = {}           # dev fallback
_mem_rewarded: set[int] = set()           # dev fallback

def set_referrer(user_id: int, referrer_id: int) -> bool:
    """Set once: remember who referred user_id. Returns True if newly set."""
    if referrer_id == user_id:
        return False
    if _r:
        try:
            # set only if not exists
            return bool(_r.set(f"ref_by:{user_id}", str(referrer_id), nx=True))
        except Exception:
            pass
    if user_id in _mem_ref_by:
        return False
    _mem_ref_by[user_id] = referrer_id
    return True

def get_referrer(user_id: int) -> Optional[int]:
    if _r:
        try:
            v = _r.get(f"ref_by:{user_id}")
            return int(v) if v is not None else None
        except Exception:
            return None
    return _mem_ref_by.get(user_id)

def mark_rewarded_once(buyer_id: int) -> bool:
    """Idempotence guard: returns True if we newly marked this buyer as rewarded."""
    if _r:
        try:
            # SETNX-style flag
            ok = _r.set(f"ref_rewarded:{buyer_id}", "1", nx=True)
            return bool(ok)
        except Exception:
            pass
    if buyer_id in _mem_rewarded:
        return False
    _mem_rewarded.add(buyer_id)
    return True
