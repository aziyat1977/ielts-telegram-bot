import os, importlib
from typing import Any

def load_app() -> Any:
    candidates = [
        ("app.mux_main", "APP"),
        ("app.mux_main", "app"),
        ("mux_main",     "APP"),
        ("mux_main",     "app"),
    ]
    for mod, attr in candidates:
        try:
            m = importlib.import_module(mod)
            if hasattr(m, attr):
                return getattr(m, attr)
        except Exception:
            continue
    from fastapi import FastAPI
    a = FastAPI()
    @a.get("/health")
    def _health(): return {"ok": True}
    return a

app = load_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT","8080")))






