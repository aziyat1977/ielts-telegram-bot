from __future__ import annotations
import json
from typing import Dict, Any
from .config import S

def _client():
    from openai import OpenAI
    return OpenAI(api_key=S.openai_key) if S.openai_key else None

SYSTEM = (
    "You are an experienced IELTS examiner. Rate IELTS Writing Task 2 responses with band scores "
    "for Task Response, Coherence & Cohesion, Lexical Resource, Grammatical Range & Accuracy, "
    "and an Overall band (0–9, half-bands allowed). Be strict but fair. Return JSON only."
)

def grade_writing(essay: str) -> Dict[str, Any]:
    cli = _client()
    if not cli:
        return {
            "overall": None,
            "note": "OPENAI_API_KEY not configured; returning stub.",
            "suggestions": ["Add your OPENAI_API_KEY in .env and redeploy to enable real feedback."]
        }
    resp = cli.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        response_format={"type":"json_object"},
        messages=[
            {"role":"system","content":SYSTEM},
            {"role":"user","content": essay.strip()[:6000]}
        ],
    )
    content = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
    except Exception:
        data = {"overall": None, "raw": content}
    return data

def render_markdown(result: Dict[str, Any]) -> str:
    if "note" in result and not result.get("overall"):
        return f"⚠️ {result['note']}"
    def band(x):
        try: return f"{float(x):.1f}"
        except Exception: return "—"
    parts = []
    parts.append("**IELTS Writing — Pro feedback**")
    parts.append(f"• Task Response: **{band(result.get('task_response'))}**")
    parts.append(f"• Coherence & Cohesion: **{band(result.get('coherence'))}**")
    parts.append(f"• Lexical Resource: **{band(result.get('lexical'))}**")
    parts.append(f"• Grammar: **{band(result.get('grammar'))}**")
    parts.append(f"• Overall: **{band(result.get('overall'))}**")
    if result.get("strengths"):
        parts.append("\n**Strengths**")
        for s in result["strengths"][:6]: parts.append(f"• {s}")
    if result.get("weaknesses"):
        parts.append("\n**Weaknesses**")
        for s in result["weaknesses"][:6]: parts.append(f"• {s}")
    if result.get("suggestions"):
        parts.append("\n**How to improve**")
        for s in result["suggestions"][:8]: parts.append(f"• {s}")
    return "\n".join(parts)
