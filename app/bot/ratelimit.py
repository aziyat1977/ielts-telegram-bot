from .config import S
allow = lambda uid=None: True
reason = None
if S.upstash_url and S.upstash_token:
    try:
        from upstash_redis import Redis
        from upstash_ratelimit import Ratelimit, SlidingWindow
        _r = Redis(url=S.upstash_url, token=S.upstash_token)
        _rl = Ratelimit(_r, SlidingWindow(10,60))
        def allow(uid=None):
            ok,_ = _rl.limit(f"rl:{uid}")
            return ok
    except Exception:
        pass
