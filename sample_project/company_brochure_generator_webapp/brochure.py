"""
brochure.py
-----------
Prompt construction and orchestration layer between the scraper and the
Ollama client.  Keeps all LLM-facing logic in one place so that the
prompts are easy to iterate on without touching the UI.
"""

from ollama_client import ollama_generate, ollama_stream, OllamaConnectionError, OllamaResponseError

# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

_SYSTEM_MESSAGE = """\
You are a professional copywriter who specialises in creating compelling \
company brochures. You write in clear, engaging Australian English.

Rules you MUST follow:
1. Base every claim strictly on the text provided by the user. \
   Do NOT invent facts, statistics, client names, or product features.
2. If a section cannot be filled from the provided content, write \
   exactly: *Not stated on the website.*
3. Output only the brochure in Markdown. Do not include preamble, \
   meta-commentary, or closing remarks outside the brochure itself.
4. Use the exact section headings listed in the instructions.
5. Write in third person (e.g. "The company offers…", not "We offer…") \
   unless the source text is clearly first-person marketing copy.
6. Tone: professional, concise, and benefit-focused.
"""

_PROMPT_TEMPLATE = """\
## Source material

**Page URL:** {url}
**Page title:** {title}
**Meta description:** {meta_description}

**Main content:**
{main_text}

**Detected contact / social info:**
- Emails: {emails}
- Phones: {phones}
- Social links: {social_links}

---

## Your task

Using ONLY the source material above, write a company brochure in Markdown \
with the following sections in order. Use these exact headings (level 2, i.e. `##`):

## Company Overview
A short paragraph (3–5 sentences) describing what the company does, \
its mission, and its background if available.

## Products & Services
A bulleted list of products or services. Be specific; use names / details \
from the source text.

## Key Differentiators
A bulleted list of what sets this company apart from competitors, \
based only on claims in the source text.

## Target Customers
Who the company serves. Use any explicit mentions or infer carefully \
from the tone and content.

## Social Proof
Testimonials, case studies, awards, or notable clients mentioned \
on the page. If none are present write *Not stated on the website.*

## Call to Action
What the website asks visitors to do next (e.g. book a demo, \
contact sales, start a free trial).

## Contact Information
List any emails, phone numbers, or office addresses found in the source text.

Do not add any other sections or commentary outside these headings.
"""


def build_brochure_prompt(scraped: dict, url: str) -> tuple[str, str]:
    """
    Build the (system, user-prompt) pair for the Ollama call.

    Parameters
    ----------
    scraped:
        Dict returned by ``scrape.extract_readable_text``.
    url:
        The original page URL (for context in the prompt).

    Returns
    -------
    tuple[str, str]
        ``(system_message, user_prompt)``
    """
    contacts = scraped.get("detected_contacts", {})
    emails = ", ".join(contacts.get("emails", [])) or "None detected"
    phones = ", ".join(contacts.get("phones", [])) or "None detected"
    socials = "\n".join(scraped.get("detected_social_links", [])) or "None detected"

    # Truncate main text to avoid overwhelming smaller models.
    # ~6 000 chars is roughly 1 500 tokens — safe for 8 B-class models.
    main_text = scraped.get("main_text", "")
    if len(main_text) > 6_000:
        main_text = main_text[:5_997] + "…"

    user_prompt = _PROMPT_TEMPLATE.format(
        url=url,
        title=scraped.get("title", "Unknown"),
        meta_description=scraped.get("meta_description", "Not provided"),
        main_text=main_text or "No readable text could be extracted.",
        emails=emails,
        phones=phones,
        social_links=socials,
    )

    return _SYSTEM_MESSAGE, user_prompt


def generate_brochure(
    scraped: dict,
    url: str,
    model: str,
    temperature: float = 0.4,
) -> str:
    """
    Generate and return the complete brochure as a Markdown string.

    Parameters
    ----------
    scraped:
        Structured dict from ``scrape.extract_readable_text``.
    url:
        The original page URL.
    model:
        Ollama model tag (e.g. ``"llama3.1:8b"``).
    temperature:
        LLM sampling temperature.

    Returns
    -------
    str
        Markdown brochure text.

    Raises
    ------
    OllamaConnectionError
        If Ollama is not running.
    OllamaResponseError
        If the model returns an unexpected response.
    """
    system, prompt = build_brochure_prompt(scraped, url)
    return ollama_generate(
        model=model,
        prompt=prompt,
        system=system,
        temperature=temperature,
    )


def stream_brochure(
    scraped: dict,
    url: str,
    model: str,
    temperature: float = 0.4,
):
    """
    Streaming variant of ``generate_brochure``.

    Yields incremental Markdown text chunks as they arrive from Ollama.
    Useful for updating a Streamlit placeholder in real time.

    Parameters
    ----------
    Same as ``generate_brochure``.

    Yields
    ------
    str
        Incremental text tokens from the model.
    """
    system, prompt = build_brochure_prompt(scraped, url)
    yield from ollama_stream(
        model=model,
        prompt=prompt,
        system=system,
        temperature=temperature,
    )
