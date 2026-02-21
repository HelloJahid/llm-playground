"""
scrape.py
---------
Utilities for fetching and parsing webpage content into structured data
suitable for brochure generation.
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

# Tags whose content is always boilerplate / noise
_NOISE_TAGS = [
    "script", "style", "noscript", "svg", "img",
    "input", "button", "form", "nav", "footer",
    "header", "aside", "iframe", "canvas",
]

# Regex patterns for contact detection
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(
    r"(?:\+?61|0)[- ]?(?:\d[- ]?){8,9}\d"  # Australian format
    r"|"
    r"\+?1?[- ]?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}"  # North-American format
)

# Known social-media hostnames (partial match)
_SOCIAL_HOSTS = {
    "linkedin.com", "twitter.com", "x.com", "facebook.com",
    "instagram.com", "youtube.com", "github.com", "tiktok.com",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_url(url: str, timeout: float = 15.0) -> str:
    """
    Fetch the raw HTML for *url*.

    Raises
    ------
    ValueError
        If the URL scheme is not http/https.
    requests.HTTPError
        On a non-2xx response.
    requests.ConnectionError / requests.Timeout
        If the server cannot be reached.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme '{parsed.scheme}'. Use http or https.")

    resp = requests.get(url, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()

    # Let requests / chardet pick the encoding; fall back to apparent if absent
    if not resp.encoding:
        resp.encoding = resp.apparent_encoding

    return resp.text


def extract_readable_text(html: str, base_url: str) -> dict:
    """
    Parse *html* and return a structured dict with the keys:

    * ``title``              – page <title> text
    * ``meta_description``   – content of <meta name="description">
    * ``main_text``          – cleaned, readable body text
    * ``detected_contacts``  – dict with keys ``emails`` and ``phones``
    * ``detected_social_links`` – list of social-media URLs found on the page

    Parameters
    ----------
    html:
        Raw HTML string from ``fetch_url``.
    base_url:
        The original page URL, used to resolve relative links.
    """
    soup = BeautifulSoup(html, "lxml")

    title = _extract_title(soup)
    meta_desc = _extract_meta_description(soup)
    main_text = _extract_main_text(soup)
    contacts = _detect_contacts(main_text, html)
    socials = _detect_social_links(soup, base_url)

    return {
        "title": title,
        "meta_description": meta_desc,
        "main_text": main_text,
        "detected_contacts": contacts,
        "detected_social_links": socials,
    }


def fetch_internal_links(html: str, base_url: str, limit: int = 5) -> list[str]:
    """
    Return up to *limit* unique internal absolute URLs found in *html*.
    Excludes common non-content paths (assets, auth pages, etc.).
    """
    soup = BeautifulSoup(html, "lxml")
    base_parsed = urlparse(base_url)
    seen: set[str] = {base_url}
    links: list[str] = []

    _skip_fragments = ("/login", "/logout", "/signup", "/register",
                       "/cdn-cgi/", ".pdf", ".png", ".jpg", ".zip")

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue

        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)

        # Keep only same-domain links
        if parsed.netloc != base_parsed.netloc:
            continue

        # Skip noisy paths
        if any(frag in parsed.path.lower() for frag in _skip_fragments):
            continue

        clean = parsed._replace(fragment="", query="").geturl()
        if clean not in seen:
            seen.add(clean)
            links.append(clean)
            if len(links) >= limit:
                break

    return links


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _extract_title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    # Fallback: first h1
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else "Unknown"


def _extract_meta_description(soup: BeautifulSoup) -> str:
    tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    if tag and tag.get("content"):
        return tag["content"].strip()
    # OpenGraph fallback
    og = soup.find("meta", attrs={"property": "og:description"})
    if og and og.get("content"):
        return og["content"].strip()
    return ""


def _extract_main_text(soup: BeautifulSoup) -> str:
    # Work on a copy so we don't mutate the original tree
    soup_copy = BeautifulSoup(str(soup), "lxml")

    # Remove all noise tags first
    for tag in soup_copy(["script", "style", "noscript", "svg",
                           "img", "input", "button", "form",
                           "iframe", "canvas"]):
        tag.decompose()

    # Prefer <main> semantic area; fall back to <article>, then <body>
    content_root = (
        soup_copy.find("main")
        or soup_copy.find("article")
        or soup_copy.find("body")
    )

    if content_root is None:
        return ""

    # Remove structural chrome inside the content root
    for tag in content_root(["nav", "footer", "header", "aside"]):
        tag.decompose()

    # Collapse whitespace while keeping paragraph breaks
    raw = content_root.get_text(separator="\n", strip=True)
    # Collapse runs of blank lines down to at most two
    cleaned = re.sub(r"\n{3,}", "\n\n", raw)
    return cleaned.strip()


def _detect_contacts(main_text: str, raw_html: str) -> dict:
    """Extract email addresses and phone numbers from visible text and raw HTML."""
    combined = main_text + raw_html
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
        parsed = urlparse(absolute)
        # Match against known social hostnames (strip leading 'www.')
        host = parsed.netloc.lower().lstrip("www.")
        if any(social in host for social in _SOCIAL_HOSTS):
            clean = parsed._replace(fragment="").geturl()
            if clean not in seen:
                seen.add(clean)
                found.append(clean)

    return found
