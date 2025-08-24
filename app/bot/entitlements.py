from __future__ import annotations
import time
from .config import S

_r = None
if S.upstash_url and S.upstash_token:
    try:
        from upstash_redis import Redis
        _r = Redis(url=S.upstash_url, token=S.upstash_token)
    except Exception:
        _r = None

_mem: dict[int, float] = {}

KEY = lambda uid: f"pro:{uid}"

def grant(user_id: int, days: int = 30) -> bool:
    ttl = max(1, int(days*24*60*60))
    try:
        if _r:
            _r.set(KEY(user_id), "1")
            _r.expire(KEY(user_id), ttl)
            return True
        _mem[int(user_id)] = time.time() + ttl
        return True
    except Exception:
        return False

def extend(user_id: int, add_days: int) -> bool:
    """Extend current TTL by add_days (if no key, behaves like grant)."""
    try:
        if _r:
            cur = _r.ttl(KEY(user_id))
            base = 0 if cur is None or cur < 0 else int(cur)
            _r.set(KEY(user_id), "1")
            _r.expire(KEY(user_id), base + int(add_days*24*60*60))
            return True
        now = time.time()
        cur = _mem.get(int(user_id), now)
        if cur < now: cur = now
        _mem[int(user_id)] = cur + int(add_days*24*60*60)
        return True
    except Exception:
        return False

def revoke(user_id: int) -> bool:
    try:
        if _r:
            try:
                _r.delete(KEY(user_id))
            except Exception:
                # fallback: expire immediately
                _r.expire(KEY(user_id), 1)
            return True
        _mem.pop(int(user_id), None)
        return True
    except Exception:
        return False

def is_pro(user_id: int) -> bool:
    try:
        if _r:
            return _r.get(KEY(user_id)) is not None
        exp = _mem.get(int(user_id))
        return bool(exp and exp > time.time())
    except Exception:
        return False

def ttl_days(user_id: int) -> int | None:
    try:
        if _r:
            t = _r.ttl(KEY(user_id))
            if t is None or t < 0:
                return None
            return (int(t) + 86400 - 1)//86400
        exp = _mem.get(int(user_id))
        if not exp: return None
        rem = int(exp - time.time())
        return (rem + 86400 - 1)//86400 if rem > 0 else None
    except Exception:
        return None
