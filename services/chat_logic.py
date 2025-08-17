# services/chat_logic.py
from __future__ import annotations

from typing import Generator, Union, Iterable, Any, Optional, List, Tuple
import os
import re

from services.llm_client import call_llm, stream_llm
from services.retriever import retrieve


# ======================= System prompts (EN / AR) =======================

SYSTEM_PROMPT_EN = (
    "You are 'Ibtikar Chatbot'. Answer professionally and helpfully.\n"
    "STYLE:\n"
    "- Use short headings and bullet points.\n"
    "- Prefer naming resources over raw URLs. When adding a link, use Markdown: [Label](https://full.url) — do not write bare domains.\n"
    "DEPTH:\n"
    "- Aim for ~200–300 words: 1–2 sentence intro + 5–8 concise bullets + a short closing line.\n"
    "CONTEXT USE:\n"
    "- Base answers ONLY on the provided context snippets. If a fact is missing, say so plainly and suggest the closest relevant info.\n"
    "FORBIDDEN:\n"
    "- Never reveal chain-of-thought or internal analysis.\n"
)

SYSTEM_PROMPT_AR = (
    "أنت 'روبوت تجمّع ابتكار'. أجب باحترافية وبإيجاز مفيد.\n"
    "الأسلوب:\n"
    "- استخدم عناوين فرعية ونقاطًا مختصرة.\n"
    "- عند إدراج الروابط استخدم ماركداون: [اسم واضح](https://الرابط) — لا تكتب نطاقًا دون https.\n"
    "العمق:\n"
    "- نحو ٢٠٠–٣٠٠ كلمة: تمهيد قصير + ٥–٨ نقاط موجزة + سطر ختامي.\n"
    "استخدام السياق:\n"
    "- اعتمد فقط على المقاطع المتاحة. إن غابت المعلومة فاذكر ذلك واقترح أقرب بديل.\n"
    "ممنوع:\n"
    "- عدم إظهار التفكير الداخلي أو التحليل.\n"
)

# Allow overriding from .env (applies to both languages)
_ENV_PROMPT = os.getenv("SYSTEM_PROMPT")
if _ENV_PROMPT:
    SYSTEM_PROMPT_EN = SYSTEM_PROMPT_AR = _ENV_PROMPT

# If you want the model to include an inline "Sources" section, set INLINE_SOURCES=1 in .env
INLINE_SOURCES = os.getenv("INLINE_SOURCES", "0") == "1"


# ============================ Utilities ============================

def _detect_lang(text: str) -> str:
    """Return 'ar' if Arabic characters exist, else 'en'."""
    return "ar" if re.search(r"[\u0600-\u06FF]", text or "") else "en"


def _clean_response(text: Optional[str]) -> str:
    """Strip provider artefacts / special tags."""
    if not text:
        return ""
    text = re.sub(r"\[/?thought\]|<\|[^>]*\|>|/think\b.*|<\|end_of_turn\|>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"^\s*(Answer|إجابة)\s*:\s*", "", text, flags=re.IGNORECASE)
    return text.strip()


# ---------- Linkification: preserve existing MD, then wrap the rest ----------

_MD_LINK_RE = re.compile(r"\[[^\]]+\]\((?:https?://)[^)]+\)")
_HTTP_RE     = re.compile(r"(?<!\()https?://[^\s)]+")
_BARE_DOMAIN_RE = re.compile(
    r"""(?<!\(|\])                # not right after '(' or ']'
        \b(
          (?:www\.)?
          [A-Za-z0-9.-]+\.[A-Za-z]{2,}   # domain.tld
          (?:/[^\s)]+)?                  # optional path
        )\b
    """,
    re.VERBOSE,
)

def _auto_linkify_markdown(s: str) -> str:
    """
    1) Temporarily mask existing Markdown links.
    2) Wrap naked http(s) links and bare domains with Markdown.
    3) Restore original Markdown links.
    """
    if not s:
        return ""

    # 1) Mask existing Markdown links
    placeholders: List[str] = []
    def _mask(m: re.Match) -> str:
        placeholders.append(m.group(0))
        return f"§§LINK{len(placeholders)-1}§§"
    masked = _MD_LINK_RE.sub(_mask, s)

    # 2a) Wrap naked http(s) links
    def _wrap_http(m: re.Match) -> str:
        url = m.group(0)
        label = re.sub(r"^https?://", "", url).split("/")[0]
        return f"[{label}]({url})"
    masked = _HTTP_RE.sub(_wrap_http, masked)

    # 2b) Convert bare domains to https://
    def _wrap_domain(m: re.Match) -> str:
        url = m.group(1)
        link = url if url.startswith(("http://", "https://")) else "https://" + url
        label = re.sub(r"^https?://", "", link).split("/")[0]
        return f"[{label}]({link})"
    masked = _BARE_DOMAIN_RE.sub(_wrap_domain, masked)

    # 3) Restore originals
    def _unmask(m: re.Match) -> str:
        idx = int(m.group(0)[6:-2])
        return placeholders[idx]
    unmasked = re.sub(r"§§LINK\d+§§", _unmask, masked)

    return unmasked


def _strip_model_sources(text: str) -> str:
    """Remove a trailing model-written 'Sources'/'المصادر' section to avoid duplication with UI."""
    if INLINE_SOURCES:
        return text
    # remove from the last occurrence of a heading/bold 'Sources' onward
    return re.sub(
        r"(?is)\n+\s*(?:#{1,3}\s*)?(?:\*\*?\s*)?(sources|المصادر)\s*(?:\*\*?)?\s*:?.*$",
        "",
        text,
    ).rstrip()


def _build_context(docs: Iterable[Any]) -> str:
    """Build the text block fed to the LLM from docs (strings or dicts)."""
    if not docs:
        return ""

    def to_text(d: Any) -> str:
        if isinstance(d, str):
            body, src = d, None
        elif isinstance(d, dict):
            body = d.get("text") or d.get("chunk") or d.get("content") or ""
            src  = d.get("source")
        else:
            body, src = str(d or ""), None
        body = (body or "").strip()
        if not body:
            return ""
        return f"{body}\n\n(Source: {src})" if src else body

    return "\n\n".join(t for t in (to_text(d) for d in docs) if t)


def _unique_sources(docs: Iterable[Any]) -> List[str]:
    seen, out = set(), []
    for d in docs or []:
        if isinstance(d, dict):
            s = d.get("source")
            if s and s not in seen:
                seen.add(s); out.append(s)
    return out


def _no_context_reply(lang: str) -> str:
    return (
        "This information isn’t available in our indexed sources. "
        "Try a more specific question or ask me to re-ingest the sources."
        if lang == "en" else
        "المعلومة غير متوفّرة في مصادرنا الحالية. "
        "جرّب سؤالًا أدق، أو اطلب إعادة فهرسة للمصادر."
    )


# ============================ Prompt builder ============================

_TOP_K = int(os.getenv("TOP_K", "6"))

def _make_prompt_and_docs(user_input: str) -> Tuple[Optional[str], str, List[dict]]:
    """
    Returns: (prompt or None if no docs, lang, docs)
    Also stores docs in Streamlit session_state['last_docs'] for the UI Sources box.
    """
    lang = _detect_lang(user_input)
    docs = retrieve(user_input, top_k=_TOP_K)

    # Expose docs to the Streamlit UI (to render clickable Sources separately)
    try:
        import streamlit as st
        st.session_state["last_docs"] = docs
    except Exception:
        pass

    if not docs:
        return None, lang, []

    context = _build_context(docs)
    srcs = _unique_sources(docs)
    src_hint = "\n".join(f"- {s}" for s in srcs) if srcs else "-"

    directive = "Respond in English." if lang == "en" else "أجب باللغة العربية."
    end_with_sources = (
        "End your answer with a short '**Sources**' section (use Markdown links).\n"
        if INLINE_SOURCES else
        "Do NOT include a 'Sources' section; the app will render sources below the answer.\n"
    )

    prompt = (
        "Use the following context to answer the user accurately. "
        "Answer ONLY with facts present in the context. If information is missing, say it is not available.\n\n"
        f"Context:\n{context}\n\n"
        f"Known sources (for reference only—do not invent new ones):\n{src_hint}\n\n"
        f"Question: {user_input}\n"
        f"{directive}\n"
        f"{end_with_sources}"
        "Answer:"
    )
    return prompt, lang, docs


# ============================== Public API ==============================

def process_user_input(user_input: str, stream: bool = False) -> Union[Generator[str, None, None], str]:
    prompt, lang, docs = _make_prompt_and_docs(user_input)
    system = SYSTEM_PROMPT_AR if lang == "ar" else SYSTEM_PROMPT_EN
    max_new = int(os.getenv("MAX_NEW_TOKENS", "800"))

    # If we have no docs, short-circuit.
    if not docs or not prompt:
        msg = _no_context_reply(lang)
        return msg if not stream else (m for m in [msg])

    if stream:
        try:
            for chunk in stream_llm(prompt, system=system, max_new_tokens=max_new):
                if chunk:
                    text = _strip_model_sources(_auto_linkify_markdown(_clean_response(chunk)))
                    if text:
                        yield text
        except Exception as e:
            yield f"⚠️ Model error: {e}"
    else:
        try:
            result = call_llm(prompt, system=system, max_new_tokens=max_new)["text"]
            cleaned = _strip_model_sources(_auto_linkify_markdown(_clean_response(result)))

            # If the answer is too short, expand once.
            if len(cleaned) < 80 and "غير متوف" not in cleaned and "available" not in cleaned.lower():
                expand_prompt = f"{prompt}\n\nExpand to ~200–300 words with 5–8 bullet points and proper Markdown links."
                cleaned = _strip_model_sources(
                    _auto_linkify_markdown(
                        _clean_response(call_llm(expand_prompt, system=system, max_new_tokens=max_new)["text"])
                    )
                )
            return cleaned
        except Exception as e:
            return f"⚠️ Model error: {e}"
