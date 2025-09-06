# notebooks/run_offline_eval.py — offline heuristic scorer (prototype) + QWK
import json, re, math, statistics, os, sys
from pathlib import Path

DATA = Path("data/sprint3_t2_samples.json")
OUT_DIR = Path("notebooks/outputs"); OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_data():
    with open(DATA, "r", encoding="utf-8") as f:
        return json.load(f)

def check_tr(sample):
    prompt = (sample.get("prompt") or "").lower()
    essay  = (sample.get("essay")  or "")
    thesis = (sample.get("thesis") or "")
    parts_needed = 1
    if "both views" in prompt or ("advantages" in prompt and "disadvantages" in prompt) or ("cause" in prompt and "solved" in prompt):
        parts_needed = 2
    bodies = [p for p in re.split(r"\n{2,}", essay) if len(p.strip()) > 40]
    tr_parts = 1 if len(bodies) >= parts_needed else 0
    tr_position = 1 if thesis.strip() else 0
    dev_markers = re.findall(r"\b(for example|for instance|because|therefore|as a result)\b", essay, flags=re.I)
    tr_support = 1 if len(dev_markers) >= parts_needed else 0
    return {"tr.parts":tr_parts,"tr.position":tr_position,"tr.support":tr_support}

def check_cc(sample):
    essay = sample.get("essay") or ""
    paragraphs = [p for p in re.split(r"\n{2,}", essay) if p.strip()]
    cc_paragraph = 1 if len(paragraphs) >= 3 else 0
    linkers = re.findall(r"\b(moreover|furthermore|in addition|on the other hand|however|therefore)\b", essay, flags=re.I)
    cc_invisible = 1 if len(linkers) <= 6 else 0
    return {"cc.paragraph":cc_paragraph,"cc.invisible":cc_invisible}

def check_lr(sample):
    essay = sample.get("essay") or ""
    words = re.findall(r"[a-z]{6,}", essay.lower())
    lr_precision = 1 if len(set(words)) >= 30 else 0
    return {"lr.precision":lr_precision}

def check_gr(sample):
    essay = sample.get("essay") or ""
    commas = essay.count(",")
    subclauses = len(re.findall(r"\b(which|that|although|while|because|since)\b", essay, flags=re.I))
    gr_rangeacc = 1 if (commas + subclauses) >= 8 else 0
    return {"gr.rangeacc":gr_rangeacc}

def band(weighted, maximum):
    if maximum == 0: return 5
    ratio = weighted/maximum
    if   ratio >= 0.85: return 9
    elif ratio >= 0.70: return 8
    elif ratio >= 0.55: return 7
    elif ratio >= 0.40: return 6
    else: return 5

def score_sample(sample):
    tr = check_tr(sample)
    cc = check_cc(sample)
    lr = check_lr(sample)
    gr = check_gr(sample)
    crit = {
        "TR": (tr, {"tr.parts":3,"tr.position":3,"tr.support":2}),
        "CC": (cc, {"cc.paragraph":2,"cc.invisible":2}),
        "LR": (lr, {"lr.precision":2}),
        "GR": (gr, {"gr.rangeacc":2}),
    }
    bands = {}
    for k,(checks,weights) in crit.items():
        got=maxi=0
        for cid,val in checks.items():
            w = weights.get(cid,1)
            maxi += w; got += w*(1 if val else 0)
        bands[k] = band(got,maxi)
    overall = round(sum(bands.values())/len(bands))
    return bands, overall

def qwk(raterA, raterB, min_rating, max_rating):
    # Quadratic Weighted Kappa
    n = max_rating - min_rating + 1
    O = [[0]*n for _ in range(n)]
    for a,b in zip(raterA,raterB):
        ai, bi = a-min_rating, b-min_rating
        if 0 <= ai < n and 0 <= bi < n:
            O[ai][bi] += 1
    A = [sum(row) for row in O]
    B = [sum(O[i][j] for i in range(n)) for j in range(n)]
    N = sum(A) if A else 0
    if N == 0: return 1.0
    E = [[(A[i]*B[j])/N for j in range(n)] for i in range(n)]
    w_sum_O = 0.0; w_sum_E = 0.0
    for i in range(n):
        for j in range(n):
            w = ((i-j)*(i-j))/((n-1)*(n-1)) if n>1 else 0.0
            w_sum_O += w * O[i][j]
            w_sum_E += w * E[i][j]
    return 1.0 if w_sum_E == 0 else 1.0 - (w_sum_O / w_sum_E)

def main():
    data = load_data()
    preds = []
    gold  = []
    detailed = []
    for s in data:
        bands, overall = score_sample(s)
        preds.append(overall)
        gold.append(int(s.get("gold",7)))
        detailed.append({
            "id": s["id"], "gold": int(s.get("gold",7)), "pred": overall, "bands": bands
        })
    score = round(qwk(gold, preds, 5, 9), 4)
    out = {
        "count": len(data),
        "qwk": score,
        "gold": gold,
        "pred": preds,
        "details": detailed
    }
    with open(OUT_DIR/"sprint3_qwk.json","w",encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(json.dumps({"qwk":score, "count":len(data)}, indent=2))

if __name__ == "__main__":
    main()
