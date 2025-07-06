import json, os
from openai import AsyncOpenAI, OpenAIError

MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
SYSTEM_MSG = (
    "You are a certified IELTS examiner. "
    "Score the given text (or speech transcript) from 1-9 and return "
    "EXACTLY three concise bullet-point tips for improvement."
)
_openai = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

async def score_essay_or_voice_async(text: str) -> dict:
    """Return {'band': int, 'tips': [str]} — raises OpenAIError on failure."""
    rsp = await _openai.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "system", "content": SYSTEM_MSG},
                  {"role": "user",   "content": text}],
        functions=[{
            "name": "score",
            "parameters": {
                "type": "object",
                "properties": {
                    "band": {"type": "integer", "minimum": 1, "maximum": 9},
                    "feedback": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 3, "maxItems": 3,
                    },
                },
                "required": ["band", "feedback"],
            },
        }],
        function_call={"name": "score"},
        max_tokens=400,
    )
    data = json.loads(rsp.choices[0].message.function_call.arguments)
    return {"band": max(1, min(9, data["band"])), "tips": data["feedback"]}
