#services/llm_inference.py
import os
from .llm_client import call_llm, stream_llm

SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "You are a helpful assistant. Answer clearly and concisely."
)

def _extract_text(data) -> str:
    """Normalize various response shapes to a single string."""
    if isinstance(data, dict):
        return (
            data.get("output")
            or data.get("answer")
            or data.get("text")
            or data.get("response")   # ✅ Added
            or data.get("raw_text")
            or str(data)
        )
    return str(data)

def generate_response(prompt: str) -> str:
    try:
        data = call_llm(
            prompt,
            system=SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=800
        )
        return _extract_text(data)
    except Exception as e:
        return f"(Model error) {e}"

def stream_response(prompt: str):
    try:
        for chunk in stream_llm(
            prompt,
            system=SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=800
        ):
            if chunk:
                yield chunk
    except Exception as e:
        yield f"(Model error) {e}"
