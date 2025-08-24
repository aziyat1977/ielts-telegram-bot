from __future__ import annotations
from datetime import datetime, timezone
from .config import S

_r = None
try:
    if S.upstash_url and S.upstash_token:
        from upstash_redis import Redis
        _r = Redis(url=S.upstash_url, token=S.upstash_token)
except Exception:
    _r = None

def _today():
    return datetime.now(timezone.utc).strftime("%Y%m%d")

def erase_user_data(user_id: int) -> int:
    """
    Deletes (if present):
      - ref_by:{uid}
      - ref_rewarded:{uid}
      - quota:W:{uid}:{YYYYMMDD}
      - quota:S:{uid}:{YYYYMMDD}
    Returns number of deleted keys (best-effort).
    """
    if not _r:
        # Nothing persisted server-side in fallback; count as 0.
        return 0
    keys = [
        f"ref_by:{user_id}",
        f"ref_rewarded:{user_id}",
        f"quota:W:{user_id}:{_today()}",
        f"quota:S:{user_id}:{_today()}",
    ]
    deleted = 0
    for k in keys:
        try:
            # Upstash returns int number of deleted keys
            deleted += int(_r.delete(k) or 0)
        except Exception:
            pass
    return deleted