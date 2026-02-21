"""
extract.py
----------
Prompt construction and LLM orchestration for the Website Insight Extractor.
All prompt logic lives here so it can be iterated independently of the UI.
"""

from ollama_client import ollama_generate

# ---------------------------------------------------------------------------
# System messages
# ---------------------------------------------------------------------------

_EXTRACT_SYSTEM = """\
You are a precise research assistant who writes in Australian English.

Rules you MUST follow:
1. Use ONLY the website text supplied by the user. Never invent facts, statistics, \
names, products, or claims that are not present in the text.
2. If the mission is not explicitly stated, you may infer it cautiously from the \
stated text and label it clearly as "(Inferred from website text)". \
If there is no reasonable basis for inference, write "Not stated on the website."
3. If information for any section is absent, write exactly: \
"Not stated on the website."
4. If you encounter conflicting claims in the text, note the uncertainty explicitly.
5. Be concise. Favour short, clear bullet points over long paragraphs.
6. Do not add commentary, disclaimers, or sections beyond those requested.
"""

_FOLLOWUP_SYSTEM = """\
You are a helpful research assistant who writes in Australian English.

Rules you MUST follow:
1. Answer ONLY using the website text and extracted insights supplied below.
2. If the answer is not present in the supplied content, respond with: \
"Not stated on the website."
3. Never speculate beyond what the supplied text supports.
4. Keep answers concise — a few sentences or a short bulleted list is ideal.
5. When it adds clarity, include a brief supporting quote (maximum 25 words) \
from the supplied text, introduced with "Source text:".
"""

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_EXTRACT_PROMPT_TEMPLATE = """\
## Website details

URL: {url}
Title: {title}
Meta description: {meta_description}

Detected emails: {emails}
Detected phone numbers: {phones}
Detected social links:
{social_links}

## Website text

{main_text}

---

## Your task

Using ONLY the website text above, produce the following three sections. \
Use these exact Markdown headings:

## Overview
A concise summary (3–5 bullet points) of what this organisation is and what it does.

## Mission
The organisation's stated purpose, values, or goals. \
If not explicitly stated, infer cautiously and label it "(Inferred from website text)". \
If there is no basis, write "Not stated on the website."

## Important Information
A bulleted list of key facts explicitly present in the text. Include any of the \
following that appear: key offerings, target audience, locations, contact details, \
policies, notable achievements, partnerships, pricing signals, or anything else \
a reader would find useful. Omit anything not present in the supplied text.
"""

_FOLLOWUP_PROMPT_TEMPLATE = """\
## Original website content

URL: {url}
Title: {title}

{main_text}

---

## Previously extracted insights

{insights}

---

## Prior questions and answers

{history_block}

---

## New question

{question}

Answer using ONLY the website content and extracted insights above. \
If the answer is not present, say "Not stated on the website."
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_extract_prompt(scraped: dict, url: str) -> tuple[str, str]:
    """
    Build the (system, user_prompt) pair for the initial insights extraction.

    Parameters
    ----------
    scraped:
        Dict returned by ``scrape.extract_readable_text``.
    url:
        The original page URL.

    Returns
    -------
    tuple[str, str]
        ``(system_message, user_prompt)``
    """
    contacts = scraped.get("detected_contacts", {})
    emails   = ", ".join(contacts.get("emails", [])) or "None detected"
    phones   = ", ".join(contacts.get("phones", [])) or "None detected"
    socials  = "\n".join(
        f"  - {link}" for link in scraped.get("detected_social_links", [])
    ) or "  None detected"

    # Cap main text at ~6 000 chars (~1 500 tokens) to stay within small-model
    # context windows without truncating so aggressively that meaning is lost.
    main_text = scraped.get("main_text", "") or "No readable text could be extracted."
    if len(main_text) > 6_000:
        main_text = main_text[:5_997] + "…"

    prompt = _EXTRACT_PROMPT_TEMPLATE.format(
        url=url,
        title=scraped.get("title", "Unknown"),
        meta_description=scraped.get("meta_description", "Not provided"),
        emails=emails,
        phones=phones,
        social_links=socials,
        main_text=main_text,
    )

    return _EXTRACT_SYSTEM, prompt


def generate_insights(scraped: dict, url: str, model: str) -> str:
    """
    Run the extraction prompt through Ollama and return the insights as a
    Markdown string.

    Parameters
    ----------
    scraped:
        Dict from ``scrape.extract_readable_text``.
    url:
        Original page URL.
    model:
        Ollama model tag, e.g. ``"llama3.1:8b"``.

    Returns
    -------
    str
        Markdown-formatted insights (Overview / Mission / Important Information).

    Raises
    ------
    OllamaConnectionError / OllamaResponseError
        Propagated from ``ollama_client``.
    """
    system, prompt = build_extract_prompt(scraped, url)
    return ollama_generate(model=model, prompt=prompt, system=system, temperature=0.2)


def build_followup_prompt(
    scraped: dict,
    url: str,
    insights: str,
    history: list[tuple[str, str]],
    question: str,
) -> tuple[str, str]:
    """
    Build the (system, user_prompt) pair for a follow-up question.

    Parameters
    ----------
    scraped:
        The original scraped dict (same object stored in session_state).
    url:
        The original page URL.
    insights:
        The Markdown string returned by ``generate_insights``.
    history:
        List of ``(question, answer)`` tuples from prior turns.
    question:
        The new question from the user.

    Returns
    -------
    tuple[str, str]
        ``(system_message, user_prompt)``
    """
    # Format prior Q&A pairs for the prompt
    if history:
        history_lines = []
        for i, (q, a) in enumerate(history, start=1):
            history_lines.append(f"Q{i}: {q}\nA{i}: {a}")
        history_block = "\n\n".join(history_lines)
    else:
        history_block = "No prior questions."

    # Reuse the same capped main_text as extraction to keep context consistent
    main_text = scraped.get("main_text", "") or "No readable text available."
    if len(main_text) > 6_000:
        main_text = main_text[:5_997] + "…"

    prompt = _FOLLOWUP_PROMPT_TEMPLATE.format(
        url=url,
        title=scraped.get("title", "Unknown"),
        main_text=main_text,
        insights=insights,
        history_block=history_block,
        question=question,
    )

    return _FOLLOWUP_SYSTEM, prompt


def answer_followup(
    scraped: dict,
    url: str,
    insights: str,
    history: list[tuple[str, str]],
    question: str,
    model: str,
) -> str:
    """
    Answer a follow-up question using the stored website content and conversation
    history. Does not re-scrape.

    Returns
    -------
    str
        The model's answer as plain text (may contain Markdown).
    """
    system, prompt = build_followup_prompt(scraped, url, insights, history, question)
    return ollama_generate(model=model, prompt=prompt, system=system, temperature=0.2)
