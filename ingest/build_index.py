# ingest/build_index.py

from typing import Optional, List, Dict
import os, json, pickle
from pathlib import Path

import numpy as np
import faiss
from FlagEmbedding import BGEM3FlagModel
from dotenv import load_dotenv

load_dotenv()

def build_index(
    records: List[Dict],
    faiss_path: str,
    docs_json_path: str,
    model_path: Optional[str] = None,
    pkl_path: Optional[str] = None,
) -> None:
    """
    records: list of {"source": str, "text": str}
    Writes: FAISS index + docs.json (+ optional legacy index.pkl)
    """
    if not records:
        raise ValueError("No records to index.")

    # 1) Chunk
    from ingest.text_utils import chunk  # local import to avoid cycles
    chunks: List[Dict] = []
    for r in records:
        src = r.get("source") or "unknown"
        txt = r.get("text") or ""
        for c in chunk(txt):
            chunks.append({"source": src, "text": c})

    if not chunks:
        raise ValueError("No chunks produced from records.")

    # 2) Encode (CPU-friendly defaults)
    model_name = model_path if (model_path and os.path.isdir(model_path)) else "BAAI/bge-m3"
    model = BGEM3FlagModel(model_name, use_fp16=False)
    vecs = model.encode([c["text"] for c in chunks], batch_size=16, return_dense=True)["dense_vecs"]
    embs = np.asarray(vecs, dtype="float32")   # shape: (N, 1024)

    # 3) FAISS
    Path(faiss_path).parent.mkdir(parents=True, exist_ok=True)
    index = faiss.IndexFlatL2(embs.shape[1])
    index.add(embs)
    faiss.write_index(index, faiss_path)

    # 4) docs.json (canonical)
    Path(docs_json_path).parent.mkdir(parents=True, exist_ok=True)
    with open(docs_json_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)

    # 5) Legacy pickle (optional)
    if pkl_path:
        Path(pkl_path).parent.mkdir(parents=True, exist_ok=True)
        with open(pkl_path, "wb") as f:
            pickle.dump([c["text"] for c in chunks], f)
