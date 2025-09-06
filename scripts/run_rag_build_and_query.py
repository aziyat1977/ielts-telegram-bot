# scripts/run_rag_build_and_query.py — builds store and runs a sample query; emits artifacts under notebooks/outputs/
import os, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTD = ROOT / "notebooks" / "outputs"
OUTD.mkdir(parents=True, exist_ok=True)

env = dict(os.environ)
# OPENAI_API_KEY picked up automatically if present

def run(pyfile, *args):
    cmd = [sys.executable, str(pyfile)] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return r.stdout.strip()

def main():
    build_out = run(ROOT/"rag"/"build_store.py")
    with open(OUTD/"sprint5_build.json","w",encoding="utf-8") as f: f.write(build_out+"\n")

    query_out = run(ROOT/"rag"/"query.py", "How to write a Band 7+ Task 1 overview without numbers?")
    with open(OUTD/"sprint5_query.json","w",encoding="utf-8") as f: f.write(query_out+"\n")

    print(json.dumps({"build": json.loads(build_out), "query_sample": json.loads(query_out)["query"]}, indent=2))

if __name__ == "__main__":
    main()
