# services/llm_client.py
from typing import Optional, Dict, Any, Generator
import os, json, requests

def _get_cfg() -> Dict[str, str]:
    return {
        "url": os.getenv("LLMAR_API_URL") or "",
        "model": os.getenv("LLMAR_MODEL_NAME") or "",
        "version": os.getenv("LLMAR_MODEL_VERSION") or "",
        "api_key": os.getenv("LLMAR_API_KEY", ""),
    }

def _headers() -> Dict[str, str]:
    cfg = _get_cfg()
    h = {"Content-Type": "application/json"}
    if cfg.get("api_key"):
        h["Authorization"] = f"Bearer {cfg['api_key']}"
    return h

def _normalize_response(data: Any) -> Dict[str, Any]:
    text = ""
    if isinstance(data, dict):
        text = data.get("text") or data.get("output") or data.get("answer") or data.get("response") or data.get("raw_text","")
        if not text and isinstance(data.get("choices"), list):
            try:
                c = data["choices"][0]
                text = (c.get("message") or {}).get("content") or c.get("text","")
            except Exception: pass
        if not text and "generations" in data:
            try: text = data["generations"][0]["text"]
            except Exception: pass
    elif isinstance(data, str):
        text = data
    else:
        text = str(data)
    return {"text": text or "", "raw": data}

def _eff_max(max_new_tokens: Optional[int], max_tokens: Optional[int]) -> int:
    if isinstance(max_new_tokens, int) and max_new_tokens > 0: return max_new_tokens
    if isinstance(max_tokens, int) and max_tokens > 0: return max_tokens
    try: return int(os.getenv("MAX_NEW_TOKENS", "800"))
    except Exception: return 800

def call_llm(
    prompt: str,
    system: Optional[str] = None,
    temperature: float = 0.2,
    max_new_tokens: Optional[int] = None,
    max_tokens: Optional[int] = None,
    timeout: int = 20,
    **kwargs: Any,
) -> Dict[str, Any]:
    cfg = _get_cfg()
    if not cfg["url"]:
        raise RuntimeError("LLMAR_API_URL is not set.")
    full_prompt = prompt if not system else f"[SYSTEM]\n{system}\n[/SYSTEM]\n{prompt}"
    payload: Dict[str, Any] = {
        "prompt": full_prompt,
        "llm_model_name": cfg["model"],
        "llm_model_version": cfg["version"],
        "temperature": float(temperature),
        "max_tokens": _eff_max(max_new_tokens, max_tokens),
    }
    payload.update({k: v for k, v in kwargs.items() if v is not None})
    try:
        r = requests.post(cfg["url"], headers=_headers(), json=payload, timeout=timeout)
        r.raise_for_status()
        try: data = r.json()
        except ValueError: data = {"raw_text": r.text}
        return _normalize_response(data)
    except requests.RequestException as e:
        return _normalize_response({"raw_text": f"[HTTP error] {e}", "text": ""})

def stream_llm(
    prompt: str,
    system: Optional[str] = None,
    temperature: float = 0.2,
    max_new_tokens: Optional[int] = None,
    max_tokens: Optional[int] = None,
    timeout: int = 20,
    **kwargs: Any,
) -> Generator[str, None, None]:
    # Fallback to one-shot (implement SSE here later if your API supports it)
    norm = call_llm(prompt, system=system, temperature=temperature,
                    max_new_tokens=max_new_tokens, max_tokens=max_tokens,
                    timeout=timeout, **kwargs)
    yield norm["text"]
