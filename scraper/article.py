"""
Article fetch + extract.

Pattern lifted from accscent/scraper/py/scraper.py:
  - curl_cffi with Chrome TLS impersonation to bypass Cloudflare
  - optional Decodo/SmartProxy residential proxy rotation
  - retry with exponential backoff

Body extraction prefers `trafilatura` (purpose-built for news), falling
back to BeautifulSoup og:meta + largest <article>/<main> block if
trafilatura returns empty.
"""

from __future__ import annotations

import logging
import os
import random
import re
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

try:
    import trafilatura  # type: ignore
    _HAS_TRAFILATURA = True
except Exception:
    trafilatura = None  # type: ignore
    _HAS_TRAFILATURA = False

log = logging.getLogger("nextup.article")

_IMPERSONATE_TARGETS = ["chrome120", "chrome123", "chrome124"]

SKIP_HOSTS = {
    "youtube.com", "m.youtube.com", "youtu.be",
    "facebook.com", "m.facebook.com",
    "twitter.com", "x.com", "t.co",
    "reddit.com", "old.reddit.com",
    "instagram.com",
    "tiktok.com",
    "pinterest.com",
}

SKIP_EXT = (".pdf", ".mp4", ".mp3", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".mov", ".avi")


class FetchError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


def should_skip_url(url: str) -> Optional[str]:
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return "unparseable-url"
    host = host.lower().lstrip("www.")
    if host in SKIP_HOSTS:
        return f"skip-host:{host}"
    if url.lower().endswith(SKIP_EXT):
        return "skip-extension"
    return None


def _extra_headers(referer: str = "https://www.google.com/") -> Dict[str, str]:
    return {
        "Referer": referer,
        "Accept-Language": random.choice([
            "en-US,en;q=0.9",
            "en-US,en;q=0.9,fr;q=0.8",
            "en-GB,en;q=0.9",
        ]),
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }


def _proxy_url() -> Optional[str]:
    user = os.getenv("SMART_PROXY_USER")
    pw = os.getenv("SMART_PROXY_PASS")
    if not user or not pw:
        return None
    return f"http://{user}:{pw}@isp.decodo.com:10000"


def _create_session() -> curl_requests.Session:
    target = random.choice(_IMPERSONATE_TARGETS)
    proxy = _proxy_url()
    if proxy:
        return curl_requests.Session(
            impersonate=target,
            proxies={"http": proxy, "https": proxy},
        )
    return curl_requests.Session(impersonate=target)


class SessionPool:
    """Thread-local curl_cffi session with periodic rotation."""

    def __init__(self, rotate_every: int = 25):
        self.rotate_every = rotate_every
        self._local = threading.local()

    def get(self) -> curl_requests.Session:
        s: Optional[curl_requests.Session] = getattr(self._local, "session", None)
        n: int = getattr(self._local, "count", 0)
        if s is None or (self.rotate_every > 0 and n > 0 and n % self.rotate_every == 0):
            if s is not None:
                try:
                    s.close()
                except Exception:
                    pass
            s = _create_session()
            self._local.session = s
        self._local.count = n + 1
        return s

    def refresh(self) -> curl_requests.Session:
        old = getattr(self._local, "session", None)
        if old is not None:
            try:
                old.close()
            except Exception:
                pass
        s = _create_session()
        self._local.session = s
        self._local.count = 1
        return s


def fetch_html(
    pool: SessionPool,
    url: str,
    max_attempts: int = 3,
    timeout_s: int = 20,
) -> str:
    last_err: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        session = pool.get()
        try:
            res = session.get(
                url,
                headers=_extra_headers(),
                timeout=timeout_s,
                allow_redirects=True,
            )
        except Exception as exc:
            last_err = exc
            log.debug("fetch error %s (attempt %d/%d): %s", url, attempt, max_attempts, exc)
            time.sleep(min(2 ** attempt, 10) + random.random())
            continue

        if 200 <= res.status_code < 300:
            return res.text or ""

        if res.status_code == 429:
            pool.refresh()
            time.sleep(min(2 ** attempt, 15) + random.random())
            last_err = FetchError(f"HTTP 429 {url}", 429)
            continue

        if res.status_code in (403, 503):
            pool.refresh()
            time.sleep(min(2 ** attempt, 10) + random.random())
            last_err = FetchError(f"HTTP {res.status_code} {url}", res.status_code)
            continue

        last_err = FetchError(f"HTTP {res.status_code} {url}", res.status_code)
        break

    raise last_err or FetchError(f"unknown fetch failure for {url}")


_DATE_META_KEYS = (
    "article:published_time",
    "article:published",
    "datepublished",
    "date",
    "dc.date",
    "dc.date.issued",
    "pubdate",
    "og:pubdate",
    "parsely-pub-date",
    "sailthru.date",
)


def _parse_date(s: str) -> Optional[str]:
    if not s:
        return None
    s = s.strip()
    fmts = (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%B %d, %Y",
        "%b %d, %Y",
    )
    for fmt in fmts:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.date().isoformat()
        except Exception:
            continue
    m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def _fallback_extract(html: str, url: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()

    published = None
    for key in _DATE_META_KEYS:
        for attr in ("property", "name", "itemprop"):
            m = soup.find("meta", {attr: key})
            if m and m.get("content"):
                published = _parse_date(m["content"])
                if published:
                    break
        if published:
            break
    if not published:
        t = soup.find("time")
        if t:
            published = _parse_date(t.get("datetime") or t.get_text(" ", strip=True))

    author = None
    m = soup.find("meta", {"name": "author"}) or soup.find("meta", property="article:author")
    if m and m.get("content"):
        author = m["content"].strip()

    body_el = (
        soup.find("article")
        or soup.find("main")
        or soup.find(attrs={"class": re.compile(r"(article|story|post)-?body", re.I)})
        or soup.body
    )
    text = ""
    if body_el:
        for tag in body_el.find_all(["script", "style", "nav", "footer", "aside"]):
            tag.decompose()
        paragraphs = [p.get_text(" ", strip=True) for p in body_el.find_all(["p", "h1", "h2", "h3"])]
        text = "\n".join(p for p in paragraphs if p and len(p) > 25)

    host = urlparse(url).hostname or ""
    return {
        "title": title,
        "text": text,
        "link": url,
        "publishedDate": published,
        "author": author,
        "source": host.lstrip("www."),
    }


def extract_article(html: str, url: str) -> Dict[str, Any]:
    """
    Run trafilatura for the body + metadata, fall back to BS4 for anything
    trafilatura misses. Always returns the shape documented in the plan.
    """
    fallback = _fallback_extract(html, url)

    if not _HAS_TRAFILATURA:
        return fallback

    try:
        text = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        ) or ""
    except Exception as exc:
        log.debug("trafilatura extract failed for %s: %s", url, exc)
        text = ""

    meta = None
    try:
        meta = trafilatura.extract_metadata(html)
    except Exception:
        meta = None

    title = (getattr(meta, "title", None) or fallback["title"] or "").strip()
    author = getattr(meta, "author", None) or fallback["author"]
    published = getattr(meta, "date", None) or fallback["publishedDate"]
    host = getattr(meta, "hostname", None) or fallback["source"]

    if not text:
        text = fallback["text"]

    return {
        "title": title,
        "text": text or "",
        "link": url,
        "publishedDate": published,
        "author": author,
        "source": (host or "").lstrip("www."),
    }
