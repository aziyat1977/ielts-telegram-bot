# notebooks/hitl_aggregate.py — aggregate labels → QWK/confusion matrix; simple weight tuning for TR/CC/LR/GR → OV
import json, os, math, itertools, re
from pathlib import Path

DATA = Path("data/sprint3_t2_samples.json")
LABELS = Path("annotations/sprint4_labels.json")
OUT = Path("notebooks/outputs"); OUT.mkdir(parents=True, exist_ok=True)

def load_json(p, fallback):
    try:
        with open(p,"r",encoding="utf-8") as f: return json.load(f)
    except: return fallback

def qwk(raterA, raterB, min_rating, max_rating):
    n = max_rating - min_rating + 1
    O = [[0]*n for _ in range(n)]
    for a,b in zip(raterA,raterB):
        ai, bi = a-min_rating, b-min_rating
        if 0<=ai<n and 0<=bi<n: O[ai][bi]+=1
    A = [sum(r) for r in O]
    B = [sum(O[i][j] for i in range(n)) for j in range(n)]
    N = sum(A)
    if N==0: return 1.0
    E = [[(A[i]*B[j])/N for j in range(n)] for i in range(n)]
    wNum=wDen=0.0
    for i in range(n):
        for j in range(n):
            w = ((i-j)*(i-j))/((n-1)*(n-1)) if n>1 else 0.0
            wNum += w * O[i][j]
            wDen += w * E[i][j]
    return 1.0 if wDen==0 else 1.0 - (wNum/wDen)

def conf_matrix(gold, pred, min_rating=5, max_rating=9):
    size = max_rating-min_rating+1
    M = [[0]*size for _ in range(size)]
    for g,p in zip(gold,pred):
        M[g-min_rating][p-min_rating]+=1
    return M

def main():
    data = load_json(DATA, [])
    gold_map = { x["id"]: int(x.get("gold",7)) for x in data }
    labels = load_json(LABELS, [])
    # if no human labels, derive OV by simple avg of TR/CC/LR/GR where present, else 7
    preds=[]
    gold=[]
    detailed=[]
    for x in data:
        gold.append(gold_map.get(x["id"],7))
        lab = next((l for l in labels if l.get("id")==x["id"]), None)
        if lab and all(int(lab.get(k,0)) in range(5,10) for k in ["TR","CC","LR","GR"]):
            ov = round(sum(int(lab[k]) for k in ["TR","CC","LR","GR"])/4)
        elif lab and int(lab.get("OV",0)) in range(5,10):
            ov = int(lab["OV"])
        else:
            ov = 7
        preds.append(ov)
        detailed.append({"id":x["id"],"gold":gold[-1],"pred":ov,"lab":lab or {}})
    kappa = round(qwk(gold,preds,5,9),4)
    cm = conf_matrix(gold,preds,5,9)

    # simple weight tuning for TR/CC/LR/GR to maximize QWK on labeled items
    labeled = [d for d in detailed if d["lab"]]
    best={"qwk":kappa,"weights":[1,1,1,1]}
    if labeled:
        g=[d["gold"] for d in labeled]
        scores=[[int(d["lab"].get(k,7)) for k in ["TR","CC","LR","GR"]] for d in labeled]
        for w in itertools.product([1,2,3], repeat=4):
            p=[]
            for s in scores:
                num=sum(a*b for a,b in zip(s,w))
                den=sum(w)
                p.append(round(num/den))
            q=qwk(g,p,5,9)
            if q > best["qwk"]: best={"qwk":q,"weights":list(w)}

    out = {"count":len(data),"labeled":len(labeled),"qwk":kappa,"best_tuned":best,"confusion":cm,"details":detailed}
    with open(OUT/"sprint4_hitl_metrics.json","w",encoding="utf-8") as f: json.dump(out,f,indent=2)
    print(json.dumps({"qwk":kappa,"n":len(data),"labeled":len(labeled),"best_weights":best["weights"],"best_qwk":round(best["qwk"],4)},indent=2))

if __name__ == "__main__":
    main()
