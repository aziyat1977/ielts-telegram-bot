# rag/evaluator.py — evaluate retrieval quality on test queries
import os, json, math
from pathlib import Path

def load_store():
    return json.loads(Path("rag/store/index.json").read_text())

def embed_and_query(query, k=3):
    import subprocess, sys
    res = subprocess.run([sys.executable,"rag/query.py",query], capture_output=True, text=True)
    return json.loads(res.stdout)["evidence"]

def recall_mrr(test_file="rag/tests/test_queries.json"):
    data = json.loads(Path(test_file).read_text())
    store = load_store()
    r_at_1 = r_at_3 = mrr_sum = 0
    n = len(data)
    for item in data:
        q, gold_ids = item["query"], item["gold_ids"]
        hits = embed_and_query(q, k=3)
        ids = [h["id"] for h in hits]
        if gold_ids[0] in ids[:1]: r_at_1 += 1
        if any(g in ids for g in gold_ids): r_at_3 += 1
        for rank, hid in enumerate(ids, start=1):
            if hid in gold_ids:
                mrr_sum += 1/rank
                break
    return {"R@1": round(r_at_1/n,4),"R@3": round(r_at_3/n,4),"MRR": round(mrr_sum/n,4)}

if __name__ == "__main__":
    import sys
    print(json.dumps(recall_mrr(), indent=2))
