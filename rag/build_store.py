# rag/build_store.py — build a tiny vector store (JSON) from corpus using OpenAI embeddings if available; fallback to hashing trick.
import os, json, math, re, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "rag" / "corpus"
STORE  = ROOT / "rag" / "store" / "index.json"
STORE.parent.mkdir(parents=True, exist_ok=True)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY","").strip()

def read_corpus():
    docs=[]
    for p in sorted(CORPUS.glob("*.md")):
        txt = p.read_text(encoding="utf-8")
        # chunk by sections (simple: split on headers)
        parts = re.split(r"\n\s*#\s+", txt)
        if parts and not parts[0].strip().startswith("#"):
            # first item may be preface; treat as sectionless
            if parts[0].strip():
                docs.append({"id": f"{p.name}::0", "title": "General", "text": parts[0].strip()})
            parts = parts[1:]
        for i,sec in enumerate(parts):
            lines = sec.splitlines()
            title = lines[0].strip() if lines else f"Section {i+1}"
            body  = "\n".join(lines[1:]).strip()
            if body:
                docs.append({"id": f"{p.name}::{i+1}", "title": title, "text": body})
    return docs

def hash_embed(text, dim=512):
    vec = [0.0]*dim
    for w in re.findall(r"[a-z]{2,}", text.lower()):
        h = int(hashlib.sha256(w.encode()).hexdigest(),16)
        idx = h % dim
        vec[idx] += 1.0
    # l2 normalize
    norm = math.sqrt(sum(v*v for v in vec)) or 1.0
    return [v/norm for v in vec]

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

def get_embedding(text):
    if OPENAI_API_KEY:
        try:
            return openai_embed(text)
        except Exception as e:
            # fallback silently
            return hash_embed(text)
    return hash_embed(text)

def main():
    docs = read_corpus()
    out=[]
    for d in docs:
        emb = get_embedding(d["text"])
        out.append({"id": d["id"], "title": d["title"], "text": d["text"], "vector": emb})
    STORE.write_text(json.dumps({"dim": len(out[0]["vector"]) if out else 0, "docs": out}, indent=2), encoding="utf-8")
    print(json.dumps({"count": len(out), "dim": (len(out[0]["vector"]) if out else 0)}, indent=2))

if __name__ == "__main__":
    main()
