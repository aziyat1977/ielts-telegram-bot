from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Tuple

from .config import S

_r = None
try:
    if S.upstash_url and S.upstash_token:
        from upstash_redis import Redis
        _r = Redis(url=S.upstash_url, token=S.upstash_token)
except Exception:
    _r = None

# in-memory fallback (dev only)
_mem_counters: dict[str, int] = {}
_mem_sets: dict[str, set[str]] = {}
_mem_z: dict[str, dict[str, float]] = {}

DAY_TTL = 8*86400  # keep a week+1 day

def _day() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")

def _k_counter(name: str, day: str | None=None) -> str:
    return f"m:{name}:{day or _day()}"

def _k_dau(day: str | None=None) -> str:
    return f"dau:{day or _day()}"

# ---------- DAU (unique users per day) ----------
def mark_user(user_id: int) -> None:
    k = _k_dau()
    if _r:
        try:
            _r.sadd(k, str(user_id))
            _r.expire(k, DAY_TTL)
            return
        except Exception:
            pass
    s = _mem_sets.setdefault(k, set())
    s.add(str(user_id))

def dau_today() -> int:
    k = _k_dau()
    if _r:
        try:
            return int(_r.scard(k) or 0)
        except Exception:
            return 0
    return len(_mem_sets.get(k, set()))

# ---------- Counters (per-day) ----------
def bump(name: str, inc: int = 1) -> int:
    k = _k_counter(name)
    if _r:
        try:
            val = int(_r.incrby(k, inc))
            if val == inc:
                _r.expire(k, DAY_TTL)
            return val
        except Exception:
            pass
    _mem_counters[k] = _mem_counters.get(k, 0) + inc
    return _mem_counters[k]

def get_today(name: str) -> int:
    k = _k_counter(name)
    if _r:
        try:
            v = _r.get(k)
            return int(v or 0)
        except Exception:
            return 0
    return _mem_counters.get(k, 0)

# ---------- Referrals (deep-link start args) ----------
def ref_hit(code: str) -> None:
    if not code:
        return
    z = f"ref:{_day()}"
    if _r:
        try:
            _r.zincrby(z, 1, code)
            _r.expire(z, DAY_TTL)
            return
        except Exception:
            pass
    dz = _mem_z.setdefault(z, {})
    dz[code] = dz.get(code, 0) + 1.0

def top_refs(n: int = 5) -> list[tuple[str, float]]:
    z = f"ref:{_day()}"
    if _r:
        try:
            items = _r.zrevrange(z, 0, n-1, withscores=True) or []
            return [(m, float(s)) for m, s in items]
        except Exception:
            return []
    dz = _mem_z.get(z, {})
    return sorted(dz.items(), key=lambda kv: kv[1], reverse=True)[:n]

# --- helper: today's clicks for a specific referral code (uses existing _r, _mem_z, _day) ---
def ref_hits_today(code: str) -> int:
    z = f"ref:{_day()}"
    if _r:
        try:
            s = _r.zscore(z, code)
            return int(float(s)) if s is not None else 0
        except Exception:
            return 0
    dz = _mem_z.get(z, {})
    return int(dz.get(code, 0))

# ---- 7-day export helpers ----
from datetime import datetime, timezone, timedelta

def _days_utc(n:int=7) -> list[str]:
    """Return last n day strings YYYYMMDD in ascending order (oldest..today) UTC."""
    now = datetime.now(timezone.utc).date()
    seq = [(now - timedelta(days=i)).strftime("%Y%m%d") for i in range(n-1, -1, -1)]
    return seq

def get_for_day(name: str, day: str) -> int:
    """Read per-day counter m:{name}:{day}."""
    k = _k_counter(name, day)
    if _r:
        try:
            v = _r.get(k)
            return int(v or 0)
        except Exception:
            return 0
    return _mem_counters.get(k, 0)

def dau_for_day(day: str) -> int:
    k = _k_dau(day)
    if _r:
        try:
            return int(_r.scard(k) or 0)
        except Exception:
            return 0
    return len(_mem_sets.get(k, set()))

def top_refs_for_day(day: str, n:int=5) -> list[tuple[str, float]]:
    z = f"ref:{day}"
    if _r:
        try:
            items = _r.zrevrange(z, 0, n-1, withscores=True) or []
            return [(m, float(s)) for m, s in items]
        except Exception:
            return []
    dz = _mem_z.get(z, {})
    return sorted(dz.items(), key=lambda kv: kv[1], reverse=True)[:n]


# ---- full referral dump for a day ----
def all_refs_for_day(day: str) -> list[tuple[str, float]]:
    z = f"ref:{day}"
    if _r:
        try:
            items = _r.zrevrange(z, 0, -1, withscores=True) or []
            return [(m, float(s)) for m, s in items]
        except Exception:
            return []
    dz = _mem_z.get(z, {})
    return sorted(dz.items(), key=lambda kv: kv[1], reverse=True)

