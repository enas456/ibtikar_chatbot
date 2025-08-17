# ingest/login_site.py
from __future__ import annotations
import os
from typing import List, Dict
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

AUTH_STATE = "auth.json"

def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script","style","noscript","header","nav","footer","aside"]):
        tag.decompose()
    return " ".join(soup.stripped_strings)

def _ensure_login(context, base: str):
    # If we already have storageState loaded, user is logged in
    page = context.new_page()
    page.goto(urljoin(base, "/my/"), wait_until="domcontentloaded")
    if "login" in page.url or "sesskey" in page.url:
        # try to login using env creds
        uname = os.getenv("LMS_USERNAME")
        pwd   = os.getenv("LMS_PASSWORD")
        if not uname or not pwd:
            raise RuntimeError("LMS_USERNAME/LMS_PASSWORD not set in .env")
        page.goto(urljoin(base, "/login/index.php"), wait_until="domcontentloaded")
        # Moodle typically uses id='username' and id='password'
        page.fill('input[name="username"],input#username', uname)
        page.fill('input[name="password"],input#password', pwd)
        # different themes use different selectors; click any 'Log in' button
        page.click('button[type="submit"], input[type="submit"]')
        page.wait_for_load_state("domcontentloaded")
        if "login" in page.url:
            raise RuntimeError("Login failed (still on login page).")
        # save new auth
        context.storage_state(path=AUTH_STATE)
    page.close()

def crawl_logged_in(base: str, after_paths: List[str]) -> List[Dict[str, str]]:
    """
    Returns: [{"source": full_url, "text": "..."}] for each page in after_paths.
    First run creates/updates auth.json (Playwright storage state).
    """
    out: List[Dict[str, str]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Reuse auth if present
        ctx_args = {"storage_state": AUTH_STATE} if os.path.exists(AUTH_STATE) else {}
        context = browser.new_context(**ctx_args)

        try:
            _ensure_login(context, base)
            page = context.new_page()
            for path in after_paths:
                url = urljoin(base, path)
                page.goto(url, wait_until="domcontentloaded")
                html = page.content()
                text = _extract_text(html)
                if len(text) >= 200:
                    out.append({"source": url, "text": text})
        finally:
            context.close()
            browser.close()
    return out
