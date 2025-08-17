import httpx, bs4, urllib.parse, time

def harvest(seed:str, allow:list[str], deny:list[str]) -> list[dict]:
    seen, q, out = set(), [seed], []
    with httpx.Client(timeout=15.0, follow_redirects=True) as s:
        while q:
            url = q.pop(0)
            if url in seen:
                continue
            seen.add(url)
            r = s.get(url)
            if "text/html" not in r.headers.get("content-type", ""):
                continue
            soup = bs4.BeautifulSoup(r.text, "lxml")
            for bad in soup(["script","style","noscript","header","footer","nav"]): bad.decompose()
            text = " ".join(soup.get_text(" ").split())
            if text:
                out.append({"source": url, "text": text})
            for a in soup.select("a[href]"):
                nxt = urllib.parse.urljoin(url, a["href"])
                if any(nxt.startswith(a_) for a_ in allow) and not any(nxt.startswith(d_) for d_ in deny):
                    q.append(nxt)
            time.sleep(0.25)
    return out
