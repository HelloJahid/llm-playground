from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urldefrag

# Standard headers to fetch a website
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/117.0.0.0 Safari/537.36"
    )
}

def _get(url: str, timeout: float = 15.0) -> requests.Response:
    """
    Small helper to fetch a URL with sane defaults.
    Raises for HTTP errors and ensures encoding is set.
    """
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    # requests usually guesses well, but this makes text extraction more reliable
    if not resp.encoding:
        resp.encoding = resp.apparent_encoding
    return resp

def fetch_website_contents(url: str, max_chars: int = 2000) -> str:
    """
    Return the title and visible text content of the website at the given url,
    truncated to max_chars characters.
    """
    resp = _get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else "No title found"

    text = ""
    if soup.body:
        for tag in soup.body(["script", "style", "img", "input", "noscript"]):
            tag.decompose()
        # Normalise whitespace and keep line breaks
        text = soup.body.get_text(separator="\n", strip=True)

    out = f"{title}\n\n{text}".strip()
    if len(out) > max_chars:
        out = out[: max_chars - 1].rstrip() + "…"
    return out

def fetch_website_links(url: str) -> list[str]:
    """
    Return normalised, absolute links from the website at the given url.
    Filters out empty, fragment-only, mailto, tel, and javascript links.
    Removes URL fragments and de-duplicates while preserving order.
    """
    resp = _get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    seen = set()
    out: list[str] = []

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if not href:
            continue

        # Skip non-navigational links
        lower = href.lower()
        if lower.startswith(("javascript:", "mailto:", "tel:")):
            continue

        # Make absolute and remove fragment (#...)
        absolute = urljoin(url, href)
        absolute, _frag = urldefrag(absolute)

        if absolute not in seen:
            seen.add(absolute)
            out.append(absolute)

    return out