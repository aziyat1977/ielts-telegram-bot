# rag/query.py — load store, embed query, return top-k passages and a grounded explanation.
import os, json, math, re, sys, hashlib
from pathlib import Path

ROOT  = Path(__file__).resolve().parents[1]
STORE = ROOT / "rag" / "store" / "index.json"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY","").strip()

def hash_embed(text, dim=512):
    vec = [0.0]*dim
    for w in re.findall(r"[a-z]{2,}", text.lower()):
        h = int(hashlib.sha256(w.encode()).hexdigest(),16)
        vec[h % dim] += 1.0
    n = math.sqrt(sum(v*v for v in vec)) or 1.0
    return [v/n for v in vec]

def openai_embed(text):
    import json, urllib.request
    api = "https://api.openai.com/v1/embeddings"
    data = json.dumps({"model":"text-embedding-3-small","input": text}).encode("utf-8")
    req = urllib.request.Request(api, data=data, headers={
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.loads(r.read().decode("utf-8"))
        return j["data"][0]["embedding"]

def get_embedding(text, dim=512):
    if OPENAI_API_KEY:
        try:
            return openai_embed(text)
        except Exception:
            return hash_embed(text, dim)
    return hash_embed(text, dim)

def cosine(a,b):
    num = sum(x*y for x,y in zip(a,b))
    da = math.sqrt(sum(x*x for x in a)) or 1.0
    db = math.sqrt(sum(y*y for y in b)) or 1.0
    return num/(da*db)

def top_k(query, k=3):
    j = json.loads(STORE.read_text(encoding="utf-8"))
    qv = get_embedding(query, j.get("dim",512))
    scored=[]
    for d in j["docs"]:
        s = cosine(qv, d["vector"])
        scored.append((s,d))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"score": round(s,4), "id": d["id"], "title": d["title"], "text": d["text"]} for s,d in scored[:k]]

def grounded_explanation(query):
    hits = top_k(query, k=3)
    bullets = []
    for h in hits:
        bullets.append(f"- [{h['title']}] {h['text'].splitlines()[0][:180].rstrip()}")
    rationale = "This guidance is grounded in public IELTS descriptors: answer all parts; maintain a clear position; provide an overview in Task 1; select and compare key features with correct units/time; prefer 'invisible cohesion'."
    return {"query": query, "rationale": rationale, "evidence": hits, "summary_bullets": bullets}

def main():
    q = "How do I ensure 'answer all parts' and 'clear position' for Task 2?"
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    out = grounded_explanation(q)
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
