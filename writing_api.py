# === WRITING API: IELTS rubric scoring + optional AI-style signal ===
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import os, re, json
HAS_OAI = bool(os.getenv("OPENAI_API_KEY")); SCORER_KEY = os.getenv("SCORER_API_KEY","")
try:
    if HAS_OAI:
        from openai import OpenAI
        _oai_client = OpenAI()
except Exception:
    HAS_OAI=False; _oai_client=None
router = APIRouter(prefix="", tags=["writing"])
class ScoreRequest(BaseModel):
    task_type: str = Field(pattern="^(task2|task1|gt_letter)$")
    text: str; topic: Optional[str] = None; target_band: Optional[float] = None; ai_style_check: bool = True
class RewriteReq(BaseModel):
    text: str; scores: Dict[str, Any]
_FN_WORDS=set(("the a an of to in for on at by with from as that which who whom whose this these those and or but so because although though however therefore moreover meanwhile whereas while if unless until since after before during above below between under into through over again further then once here there when where why how all any both each few more most other some such no nor not only own same so than too very can will just don don’t shouldn shouldn’t").split())
def _words(s:str)->List[str]: return re.findall(r"[A-Za-z']+", (s or "").lower())
def _sentences(s:str)->List[str]: return [t.strip() for t in re.split(r"(?<=[.!?])\s+|\n{2,}", s or "") if t.strip()]
def _ttr(tokens:List[str])->float: return (len(set(tokens))/max(1,len(tokens)))
def _function_word_ratio(tokens:List[str])->float:
    if not tokens: return 0.0
    fw = sum(1 for t in tokens if t in _FN_WORDS); return fw/len(tokens)
def _ngram_repetition(tokens:List[str], n:int=3)->float:
    if len(tokens)<n: return 0.0
    grams = [" ".join(tokens[i:i+n]) for i in range(len(tokens)-n+1)]
    total=len(grams); uniq=len(set(grams)); return 1 - (uniq/max(1,total))
def _ai_style_signal(text:str)->Dict[str,Any]:
    sents=_sentences(text); toks=_words(text); lens=[len(_words(s)) for s in sents] or [0]
    mean = sum(lens)/len(lens); sd = (sum((x-mean)**2 for x in lens)/len(lens))**0.5 if lens else 0.0
    cv = (sd/mean) if mean>0 else 0.0; ttr=_ttr(toks); fwr=_function_word_ratio(toks); rep=_ngram_repetition(toks,3)
    signals=[];
    if cv < 0.12 and len(sents)>=5: signals.append("sentence_length_uniformity")
    if ttr < 0.26: signals.append("low_type_token_ratio")
    if fwr < 0.35 or fwr > 0.72: signals.append("function_word_profile_outlier")
    if rep > 0.22: signals.append("repetitive_phrasing_3gram")
    lvl="low";  lvl="medium" if len(signals)>=2 else lvl;  lvl="high" if len(signals)>=3 else lvl
    return {"level": lvl, "signals": signals, "disclaimer":"Indicator, not proof; known false positives (esp. non-native writers)."}
def _min_words(task_type:str)->int: return 250 if task_type=="task2" else 150
def _prompt(task_type:str, text:str, topic:Optional[str])->str:
    goal = "Task Response (Task 2 essay)" if task_type=="task2" else "Task Achievement (Task 1 report/GT letter)"
    return f"""
You are an IELTS Writing examiner. Score strictly against PUBLIC band descriptors.
Criteria: {goal} as TA_TR, Coherence & Cohesion (CC), Lexical Resource (LR), Grammatical Range & Accuracy (GRA).
Return STRICT JSON:
{{
  "scores": {{"TA_TR": <float>, "CC": <float>, "LR": <float>, "GRA": <float>, "overall": <float>}},
  "rationale": {{
    "TA_TR": {{"band": <float>, "why": "<rubric mapping>", "evidence": [{{"quote":"...", "offset":[start,end]}}], "fix":"<one-line>" }},
    "CC":    {{"band": <float>, "why": "<rubric mapping>", "evidence": [{{"quote":"...", "offset":[start,end]}}], "fix":"<one-line>" }},
    "LR":    {{"band": <float>, "why": "<rubric mapping>", "evidence": [{{"quote":"...", "offset":[start,end]}}], "fix":"<one-line>" }},
    "GRA":   {{"band": <float>, "why": "<rubric mapping>", "evidence": [{{"quote":"...", "offset":[start,end]}}], "fix":"<one-line>" }}
  }},
  "highlights": [{{"criterion":"CC","span":[start,end],"note":"<short>"}}]
}}
Topic: {topic or "n/a"}

TEXT:
{text}
"""
def _oai_score(task_type:str, text:str, topic:Optional[str])->Dict[str,Any]:
    if not HAS_OAI: raise RuntimeError("OpenAI not configured")
    resp = _oai_client.chat.completions.create(model="gpt-4o-mini",
        messages=[{"role":"system","content":"Return ONLY JSON."},{"role":"user","content":_prompt(task_type,text,topic)}],
        temperature=0.2)
    content = resp.choices[0].message.content
    try: import json as _j; return _j.loads(content)
    except Exception:
        import re as _re, json as _j; m=_re.search(r"\{.*\}\s*$", content, _re.S);
        if not m: raise; return _j.loads(m.group(0))
def score_text(task_type:str, text:str, topic:Optional[str], ai_style:bool)->Dict[str,Any]:
    n_words=len(_words(text or ""));  need=_min_words(task_type)
    if n_words < need: raise HTTPException(status_code=400, detail=f"Too short: {n_words} words (min {need}).")
    if HAS_OAI:
        try: result=_oai_score(task_type, text, topic)
        except Exception:
            result={"scores":{"TA_TR":6.0,"CC":6.0,"LR":6.0,"GRA":6.0,"overall":6.0},
                    "rationale":{"TA_TR":{"band":6.0,"why":"fallback","evidence":[{"quote":(text or "")[:60],"offset":[0,min(60,len(text or ""))]}],"fix":"-"},
                                 "CC":{"band":6.0,"why":"fallback","evidence":[],"fix":"-"},
                                 "LR":{"band":6.0,"why":"fallback","evidence":[],"fix":"-"},
                                 "GRA":{"band":6.0,"why":"fallback","evidence":[],"fix":"-"}},"highlights":[]}
    else:
        result={"scores":{"TA_TR":6.0,"CC":6.0,"LR":6.0,"GRA":6.0,"overall":6.0},
                "rationale":{"TA_TR":{"band":6.0,"why":"Heuristic placeholder (enable OPENAI_API_KEY).","evidence":[],"fix":"Add clear overview/address all parts."},
                             "CC":{"band":6.0,"why":"Heuristic placeholder.","evidence":[],"fix":"Reduce over-linking; add referencing."},
                             "LR":{"band":6.0,"why":"Heuristic placeholder.","evidence":[],"fix":"Replace repetition; fix collocations."},
                             "GRA":{"band":6.0,"why":"Heuristic placeholder.","evidence":[],"fix":"Repair articles/tense drift; avoid comma splices."}},
                "highlights":[]}
    if ai_style: result["ai_style"]=_ai_style_signal(text)
    return result
@router.post("/score")
def score(req: ScoreRequest, request: Request):
    if SCORER_KEY and request.headers.get("X-Scorer-Key","") != SCORER_KEY: raise HTTPException(status_code=401, detail="unauthorized")
    return score_text(req.task_type, req.text, req.topic, req.ai_style_check)
@router.post("/rewrite_plan")
def rewrite_plan(req: RewriteReq, request: Request):
    if SCORER_KEY and request.headers.get("X-Scorer-Key","") != SCORER_KEY: raise HTTPException(status_code=401, detail="unauthorized")
    text=req.text or ""
    plan={"priority_fixes":[
        {"crit":"TA_TR","title":"Add overview","scaffold":"Overall, X rose while Y declined, with Z remaining stable."},
        {"crit":"CC","title":"Split long paragraph","ops":[{"action":"split","at":max(0,len(text)//2)}]},
        {"crit":"GRA","title":"Fix articles/commas","ops":[{"find":"the poverty","replace":"poverty"}]}
    ]}
    if HAS_OAI:
        try:
            from openai import OpenAI, json as _json
            r=OpenAI().chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":f"Create 3 prioritized fixes as JSON key priority_fixes. Text: {text}"}], temperature=0.2)
            j=_json.loads(r.choices[0].message.content)
            if isinstance(j,dict) and 'priority_fixes' in j: plan=j
        except Exception: pass
    return plan
# === END ===
