# api/app.py
import os, json, subprocess, sys
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent
RAG = ROOT / "rag"
STORE = RAG / "store" / "index.json"

app = FastAPI(title="RAG Coach API", version="0.1.0")

def run_py(p, *args):
    r = subprocess.run([sys.executable, str(p), *args], capture_output=True, text=True, check=True)
    return r.stdout

# Build store at startup (idempotent)
try:
    if not STORE.exists():
        run_py(RAG/"build_store.py")
except Exception as e:
    # Log but don't crash; /healthz will still report 'ok': false
    (ROOT/"startup_error.txt").write_text(str(e), encoding="utf-8")

class GroundedReq(BaseModel):
    query: str

@app.get("/healthz")
def healthz():
    ok = STORE.exists()
    return {"ok": ok, "store_exists": ok}

@app.post("/coach/grounded")
def grounded(req: GroundedReq):
    out = run_py(RAG/"query.py", req.query)
    return json.loads(out)
