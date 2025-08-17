# services/retriever.py
from typing import List, Dict, Any, Optional
import os, json
import faiss, numpy as np
from FlagEmbedding import BGEM3FlagModel
try:
    from FlagEmbedding import FlagReranker
except Exception:
    FlagReranker = None  # graceful fallback

# --------------------------- Source allowlist --------------------------------
ALLOW_DOMAINS = {
    "teknofest.ibtikar.org.tr",
    "ibtikar.org.tr",
}
def _allowed(src: str) -> bool:
    if not src: return False
    if src.startswith("gdoc:"): return True
    try:
        from urllib.parse import urlparse
        return urlparse(src).netloc in ALLOW_DOMAINS
    except Exception:
        return False

# ------------------------------ Globals --------------------------------------
_model: Optional[BGEM3FlagModel] = None
_index = None
_docs: List[Dict[str, Any]] = []
_reranker: Any = None

def _load():
    global _model, _index, _docs, _reranker
    if _model is None:
        _model = BGEM3FlagModel(os.getenv("BGE_MODEL_PATH") or "BAAI/bge-m3", use_fp16=False)
    if _index is None:
        _index = faiss.read_index(os.getenv("FAISS_INDEX_PATH"))
    if not _docs:
        _docs = json.load(open(os.getenv("DOCS_JSON_PATH"), encoding="utf-8"))
    if _reranker is None and FlagReranker:
        try:
            _reranker = FlagReranker(os.getenv("RERANK_MODEL", "BAAI/bge-reranker-large"), use_fp16=False)
        except Exception:
            _reranker = None

def _embed(texts: List[str]) -> np.ndarray:
    vecs = _model.encode(texts, return_dense=True)["dense_vecs"]
    return np.asarray(vecs, dtype="float32")

def _dedup_by_text(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen, out = set(), []
    for r in items:
        t = (r.get("text") or "").strip().lower()
        if t and t not in seen:
            seen.add(t); out.append(r)
    return out

def _ar_normalize(s: str) -> str:
    import re
    s = re.sub(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]", "", s or "")
    return s.replace("أ","ا").replace("إ","ا").replace("آ","ا").replace("ى","ي").replace("ة","ه")

def retrieve(query: str, top_k: int = 6) -> List[Dict[str, Any]]:
    _load()
    recall_k = int(os.getenv("RECALL_K", "60"))

    # Search with original + Arabic-normalized query (if Arabic present)
    queries = [query]
    if any("\u0600" <= c <= "\u06FF" for c in query):
        queries.append(_ar_normalize(query))

    # Merge recall results
    idxs: List[int] = []
    for q in _embed(queries):
        D, I = _index.search(q.reshape(1, -1), recall_k)
        idxs.extend([i for i in I[0] if i >= 0])

    # Unique while preserving order
    seen = set(); merged = []
    for i in idxs:
        if i not in seen and 0 <= i < len(_docs):
            seen.add(i); merged.append(_docs[i])

    # Filter by allowed sources (fallback if empty)
    cand = [r for r in merged if _allowed(r.get("source",""))] or merged[:max(top_k, 10)]

    # Optional reranking
    if _reranker and len(cand) > top_k:
        pairs = [(query, r.get("text","")) for r in cand]
        scores = _reranker.compute_score(pairs, batch_size=32)
        cand = [r for r,_ in sorted(zip(cand, scores), key=lambda x: x[1], reverse=True)]

    cand = _dedup_by_text(cand)
    return cand[:top_k]
