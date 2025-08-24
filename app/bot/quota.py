from __future__ import annotations
import time
from datetime import datetime, timezone, timedelta
from typing import Tuple
from .config import S

_r = None
try:
    if S.upstash_url and S.upstash_token:
        from upstash_redis import Redis
        _r = Redis(url=S.upstash_url, token=S.upstash_token)
except Exception:
    _r = None

_mem: dict[str, tuple[int, float]] = {}

def _secs_to_midnight_utc() -> int:
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).date()
    reset = datetime.combine(tomorrow, datetime.min.time(), tzinfo=timezone.utc)
    return max(60, int((reset - now).total_seconds()))

def _key(uid: int, kind: str) -> str:
    d = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"quota:{kind}:{uid}:{d}"

def remaining_today(uid: int, kind: str, limit: int) -> int:
    if _r:
        v = _r.get(_key(uid, kind))
        used = int(v or "0")
        return max(0, limit - used)
    k = _key(uid, kind)
    cnt, exp = _mem.get(k, (0, time.time() + _secs_to_midnight_utc()))
    if exp < time.time():
        cnt = 0; exp = time.time() + _secs_to_midnight_utc()
    _mem[k] = (cnt, exp)
    return max(0, limit - cnt)

def take(uid: int, kind: str, limit: int) -> Tuple[bool, int]:
    """Increment usage and return (allowed, remaining_after)."""
    if _r:
        k = _key(uid, kind)
        new = int(_r.incr(k))
        if new == 1:
            _r.expire(k, _secs_to_midnight_utc())
        return (new <= limit, max(0, limit - new))
    k = _key(uid, kind)
    cnt, exp = _mem.get(k, (0, time.time() + _secs_to_midnight_utc()))
    if exp < time.time():
        cnt = 0; exp = time.time() + _secs_to_midnight_utc()
    cnt += 1
    _mem[k] = (cnt, exp)
    return (cnt <= limit, max(0, limit - cnt))
