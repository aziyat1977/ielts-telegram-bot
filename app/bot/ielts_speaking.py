from __future__ import annotations
import io, json, httpx
from typing import Dict, Any
from .config import S

# OpenAI client (lazy)
def _client():
    from openai import OpenAI
    return OpenAI(api_key=S.openai_key) if S.openai_key else None

def get_file_url(bot_token: str, file_id: str) -> str:
    # 1) Get file_path via Telegram Bot API getFile
    r = httpx.get(
        f"https://api.telegram.org/bot{bot_token}/getFile",
        params={"file_id": file_id},
        timeout=15
    )
    r.raise_for_status()
    data = r.json()
    fp = data.get("result", {}).get("file_path")
    if not fp:
        raise RuntimeError("No file_path from Telegram getFile")
    return f"https://api.telegram.org/file/bot{bot_token}/{fp}"

def transcribe_file_url(file_url: str) -> str:
    cli = _client()
    if not cli:
        return ""
    # 2) Download the voice OGG
    r = httpx.get(file_url, timeout=60)
    r.raise_for_status()
    b = r.content
    bio = io.BytesIO(b); bio.name = "voice.ogg"  # give the stream a filename
    # 3) Transcribe with OpenAI (try gpt-4o-transcribe, then whisper-1)
    try:
        tr = cli.audio.transcriptions.create(model="gpt-4o-transcribe", file=bio)
    except Exception:
        bio.seek(0)
        tr = cli.audio.transcriptions.create(model="whisper-1", file=bio)
    # unified access
    if hasattr(tr, "text"):
        return tr.text or ""
    if isinstance(tr, dict):
        return tr.get("text", "")
    return ""

SPEAKING_SYSTEM = (
    "You are an experienced IELTS Speaking examiner. Rate answers with band scores for "
    "Fluency & Coherence, Lexical Resource, Grammatical Range & Accuracy, Pronunciation (estimate from transcript), "
    "and an Overall band (0–9, half-bands allowed). Be strict but fair. Return JSON only."
)
# Expected JSON: {"fluency":..,"lexical":..,"grammar":..,"pronunciation":..,"overall":..,
#                 "strengths":[...], "weaknesses":[...], "suggestions":[...]}

def grade_speaking(transcript: str) -> Dict[str, Any]:
    cli = _client()
    if not cli or not transcript.strip():
        return {"overall": None, "note": "Missing OpenAI key or empty transcript."}
    resp = cli.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        response_format={"type":"json_object"},
        messages=[
            {"role":"system","content": SPEAKING_SYSTEM},
            {"role":"user","content": transcript[:6000]}
        ],
    )
    content = resp.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except Exception:
        return {"overall": None, "raw": content}

def render_speaking_md(result: Dict[str, Any], transcript: str) -> str:
    if "note" in result and not result.get("overall"):
        return f"⚠️ {result['note']}"
    def band(x):
        try: return f"{float(x):.1f}"
        except Exception: return "—"
    parts = []
    parts.append("**IELTS Speaking — Pro feedback**")
    parts.append(f"• Fluency & Coherence: **{band(result.get('fluency'))}**")
    parts.append(f"• Lexical Resource: **{band(result.get('lexical'))}**")
    parts.append(f"• Grammar: **{band(result.get('grammar'))}**")
    parts.append(f"• Pronunciation: **{band(result.get('pronunciation'))}**")
    parts.append(f"• Overall: **{band(result.get('overall'))}**")
    if transcript:
        parts.append("\n**Transcript (auto)**")
        t = transcript.strip()
        parts.append(t[:1200] + ("…" if len(t) > 1200 else ""))
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
