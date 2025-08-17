# ingest/ingest_runner.py
import os
from pathlib import Path
from collections import deque
from urllib.parse import urljoin, urlparse

import yaml
from dotenv import load_dotenv
from .build_index import build_index

SOCIAL_HOSTS = ("facebook.com","fb.com","instagram.com","t.me","telegram.me","x.com","twitter.com","youtube.com","linkedin.com","wa.me","whatsapp.com")

def _simple_crawl(seed: str, allow=None, deny=None, max_pages: int = 120, timeout: int = 12):
    """Same-domain BFS crawler with simple social-links capture."""
    import httpx
    from bs4 import BeautifulSoup

    allow = allow or []
    deny  = deny or []

    seen, out = set(), []
    q = deque([seed])
    base_host = urlparse(seed).netloc
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
        while q and len(seen) < max_pages:
            url = q.popleft()
            if url in seen: continue
            seen.add(url)
            try:
                r = client.get(url)
                if r.status_code >= 400: continue
                if "text/html" not in r.headers.get("content-type",""): continue

                soup = BeautifulSoup(r.text, "lxml")

                # --- capture social links BEFORE stripping layout -------------
                socials = []
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if any(h in href for h in SOCIAL_HOSTS):
                        label = (a.get_text(strip=True) or urlparse(href).netloc).strip()
                        socials.append(f"{label}: {href}")
                if socials:
                    out.append({"source": url, "text": "روابط التواصل الاجتماعي: " + " | ".join(sorted(set(socials))) })

                # --- strip & extract text ------------------------------------
                for tag in soup(["script","style","noscript","header","nav","footer","aside"]):
                    tag.decompose()
                text = " ".join(soup.stripped_strings)
                if len(text) >= 200:
                    out.append({"source": url, "text": text})

                # --- enqueue same-domain links --------------------------------
                for a in soup.find_all("a", href=True):
                    link = urljoin(url, a["href"])
                    p = urlparse(link)
                    if p.netloc != base_host: continue
                    if any(link.startswith(d) for d in deny): continue
                    if allow and not any(link.startswith(a) for a in allow): continue
                    if "#" in link: continue
                    if link not in seen: q.append(link)
            except Exception:
                continue
    return out

def main():
    load_dotenv()
    cfg_path = Path(__file__).with_name("sources.yaml")
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))

    # ENV knobs for crawler
    max_pages = int(os.getenv("CRAWL_MAX_PAGES", "200"))
    timeout   = int(os.getenv("CRAWL_TIMEOUT", "15"))

    records = []

    # --- Google Docs (optional) ----------------------------------------------
    gdoc_ids = [it["id"] for it in cfg.get("gdocs", [])]
    try:
        from .gdoc import fetch_gdocs_texts
    except Exception:
        fetch_gdocs_texts = None
    if gdoc_ids and fetch_gdocs_texts:
        print(f"[ingest] Google Docs: {len(gdoc_ids)}")
        try:
            records += fetch_gdocs_texts(gdoc_ids)
        except Exception as e:
            print(f"[warn] gdoc fetch failed: {e}")
    elif gdoc_ids:
        print("[warn] gdoc.fetch_gdocs_texts not available; skipping gdocs.")

    # --- Public crawl(s) -----------------------------------------------------
    for w in cfg.get("web", []):
        seed = w["seed"]; allow = w.get("allow", []); deny = w.get("deny", [])
        print(f"[ingest] crawl: {seed}")
        records += _simple_crawl(seed, allow=allow, deny=deny, max_pages=max_pages, timeout=timeout)

    # --- Logged-in crawl(s) (optional) --------------------------------------
    for lw in cfg.get("login_web", []):
        try:
            from .login_site import crawl_logged_in
        except Exception:
            crawl_logged_in = None
        if crawl_logged_in:
            print(f"[ingest] login crawl: {lw['base']} -> {lw.get('after_paths', [])}")
            try:
                records += crawl_logged_in(base=lw["base"], after_paths=lw.get("after_paths", []))
            except Exception as e:
                print(f"[warn] login crawl failed: {e}")
        else:
            print("[warn] login crawler unavailable; skipping login_web.")

    # --- Build vector store --------------------------------------------------
    faiss_path = os.getenv("FAISS_INDEX_PATH", "vectorstore/index.faiss")
    docs_json  = os.getenv("DOCS_JSON_PATH", "vectorstore/docs.json")
    pkl_path   = os.getenv("METADATA_PATH", "vectorstore/index.pkl")
    model_path = os.getenv("BGE_MODEL_PATH")

    Path(faiss_path).parent.mkdir(parents=True, exist_ok=True)
    print(f"[ingest] Building index ->\n  FAISS: {faiss_path}\n  DOCS : {docs_json}\n  PKL  : {pkl_path}\n")
    build_index(records, faiss_path, docs_json, model_path=model_path, pkl_path=pkl_path)
    print(f"[done] records={len(records)} -> {faiss_path} / {docs_json}")

if __name__ == "__main__":
    main()
