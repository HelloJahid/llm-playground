"""
scrape.py
---------
Fetches a public webpage and extracts structured, readable content from it.
No external dependencies beyond requests and BeautifulSoup.
"""

import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# Tags that never contain user-facing content
_STRIP_TAGS = [
    "script", "style", "noscript", "svg", "img",
    "input", "button", "form", "iframe", "canvas",
]

# Structural chrome to remove from inside the content root
_CHROME_TAGS = ["nav", "footer", "header", "aside"]

# Regex patterns for contact detection
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(
    r"(?:\+?61|0)[- ]?(?:\d[- ]?){8,9}\d"   # Australian numbers
    r"|"
    r"\+?1?[- ]?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}"  # North-American numbers
)

# Social-media hostname fragments
_SOCIAL_HOSTS = {
    "linkedin.com", "twitter.com", "x.com", "facebook.com",
    "instagram.com", "youtube.com", "github.com", "tiktok.com",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_url(url: str, timeout: float = 15.0) -> str:
    """
    Download the raw HTML at *url* and return it as a string.

    Raises
    ------
    ValueError
        For unsupported URL schemes.
    requests.HTTPError
        On non-2xx responses.
    requests.ConnectionError / requests.Timeout
        When the server is unreachable or too slow.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"Unsupported scheme '{parsed.scheme}'. URL must start with http:// or https://"
        )

    resp = requests.get(url, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()

    # Ensure a reliable encoding is set before decoding
    if not resp.encoding:
        resp.encoding = resp.apparent_encoding

    return resp.text


def extract_readable_text(html: str, base_url: str) -> dict:
    """
    Parse *html* and return a structured dict with:

    * ``title``                 – page <title> text
    * ``meta_description``      – <meta name="description"> content
    * ``main_text``             – cleaned, deduplicated body text
    * ``detected_contacts``     – dict with ``emails`` and ``phones`` lists
    * ``detected_social_links`` – list of social-media profile URLs
    """
    soup = BeautifulSoup(html, "lxml")

    return {
        "title":                _extract_title(soup),
        "meta_description":     _extract_meta_description(soup),
        "main_text":            _extract_main_text(soup),
        "detected_contacts":    _detect_contacts(soup, html),
        "detected_social_links": _detect_social_links(soup, base_url),
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _extract_title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else "Unknown"


def _extract_meta_description(soup: BeautifulSoup) -> str:
    # Standard <meta name="description">
    tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    if tag and tag.get("content"):
        return tag["content"].strip()
    # OpenGraph fallback
    og = soup.find("meta", attrs={"property": "og:description"})
    if og and og.get("content"):
        return og["content"].strip()
    return ""


def _extract_main_text(soup: BeautifulSoup) -> str:
    # Parse a fresh copy so we don't mutate the caller's tree
    local = BeautifulSoup(str(soup), "lxml")

    # Strip always-noisy tags first
    for tag in local(_STRIP_TAGS):
        tag.decompose()

    # Prefer semantic content areas; fall back to full body
    root = local.find("main") or local.find("article") or local.find("body")
    if root is None:
        return ""

    # Remove structural chrome within the content root
    for tag in root(_CHROME_TAGS):
        tag.decompose()

    raw = root.get_text(separator="\n", strip=True)

    # Collapse runs of blank lines to at most two
    cleaned = re.sub(r"\n{3,}", "\n\n", raw)
    return cleaned.strip()


def _detect_contacts(soup: BeautifulSoup, raw_html: str) -> dict:
    """
    Scan both the visible text and raw HTML for email addresses and phone numbers.
    Scanning raw HTML catches addresses encoded in mailto: links or data attributes.
    """
    visible = soup.get_text(" ")
    combined = visible + " " + raw_html

    emails = sorted(set(_EMAIL_RE.findall(combined)))
    phones = sorted(set(_PHONE_RE.findall(combined)))
    return {"emails": emails, "phones": phones}


def _detect_social_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Return absolute URLs that point to known social-media platforms."""
    found: list[str] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href:
            continue
        absolute = urljoin(base_url, href)
        host = urlparse(absolute).netloc.lower().removeprefix("www.")
        if any(s in host for s in _SOCIAL_HOSTS):
            clean = urlparse(absolute)._replace(fragment="").geturl()
            if clean not in seen:
                seen.add(clean)
                found.append(clean)

    return found
