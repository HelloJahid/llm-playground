"""
streamlit_app.py
----------------
Website Insight Extractor — Streamlit front-end.

Run with:
    streamlit run streamlit_app.py
"""

import sys
from pathlib import Path

import streamlit as st

# Ensure sibling modules are importable regardless of working directory
sys.path.insert(0, str(Path(__file__).parent))

from extract import answer_followup, generate_insights
from ollama_client import (
    OllamaConnectionError,
    OllamaResponseError,
    check_ollama_running,
    list_local_models,
)
from scrape import extract_readable_text, fetch_url

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Website Insight Extractor",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
# All per-URL state is stored under these keys so that changing the URL
# automatically invalidates stale data.

def _init_state() -> None:
    defaults = {
        "active_url":   "",       # URL that was last successfully extracted
        "scraped":      None,     # dict from scrape.extract_readable_text
        "insights":     "",       # Markdown string from extract.generate_insights
        "history":      [],       # list of (question, answer) tuples
        "followup_answer": "",    # most recent follow-up answer
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

_init_state()

# ---------------------------------------------------------------------------
# Sidebar — Ollama status & model selection
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("⚙️ Settings")

    # Live Ollama health check
    ollama_ok = check_ollama_running()
    if ollama_ok:
        st.success("Ollama is running", icon="✅")
    else:
        st.error("Ollama is NOT running", icon="🚫")
        st.markdown(
            "Start it in a terminal:\n```bash\nollama serve\n```\n"
            "Then refresh this page."
        )

    st.divider()

    # Model selector — populate from local Ollama if reachable
    st.subheader("Model")
    local_models = list_local_models()
    default_model = "llama3.1:8b"

    if local_models:
        idx = local_models.index(default_model) if default_model in local_models else 0
        model = st.selectbox(
            "Local model",
            options=local_models,
            index=idx,
            help="Models pulled to your machine via `ollama pull`.",
        )
    else:
        model = st.text_input(
            "Model name",
            value=default_model,
            help=(
                "Type an exact Ollama model tag.\n"
                "Pull one first: `ollama pull llama3.1:8b`"
            ),
        )

    st.divider()

    # Session management
    st.subheader("Session")
    if st.button("🗑️ Clear session", use_container_width=True):
        for key in ("active_url", "scraped", "insights", "history", "followup_answer"):
            st.session_state[key] = [] if key == "history" else ""
        st.session_state["scraped"] = None
        st.rerun()

    # Show conversation history length when a session is active
    if st.session_state["insights"]:
        n = len(st.session_state["history"])
        st.caption(
            f"Active session: **{st.session_state['active_url'][:40]}…**\n\n"
            f"{n} follow-up question{'s' if n != 1 else ''} in this session."
        )

# ---------------------------------------------------------------------------
# Main area — extraction
# ---------------------------------------------------------------------------

st.title("🔍 Website Insight Extractor")
st.caption("Local Ollama · no paid APIs · your data stays on your machine.")

st.markdown(
    "Paste any public website URL and click **Extract insights**. "
    "After extraction, ask follow-up questions about the same page "
    "without re-scraping."
)

url_input = st.text_input(
    "Website URL",
    placeholder="https://example.com",
    value=st.session_state.get("active_url", ""),
)

extract_btn = st.button(
    "Extract insights",
    type="primary",
    disabled=not ollama_ok,
)

# ---------------------------------------------------------------------------
# Extraction flow
# ---------------------------------------------------------------------------

if extract_btn:
    url = url_input.strip()

    if not url:
        st.warning("Please enter a URL.")
        st.stop()

    # Normalise scheme
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
        st.info(f"Assuming HTTPS → `{url}`")

    # If the URL changed, wipe the old session so stale data is never reused
    if url != st.session_state["active_url"]:
        st.session_state["scraped"]   = None
        st.session_state["insights"]  = ""
        st.session_state["history"]   = []
        st.session_state["followup_answer"] = ""

    # --- Scraping ---
    with st.status("Fetching page…", expanded=True) as status:
        try:
            st.write(f"Downloading `{url}` …")
            html    = fetch_url(url)
            scraped = extract_readable_text(html, url)
            st.write(
                f"Extracted **{len(scraped['main_text']):,}** characters "
                f"from *{scraped['title']}*."
            )
            status.update(label="Page fetched.", state="complete")
        except ValueError as exc:
            status.update(label="Invalid URL.", state="error")
            st.error(f"**Invalid URL:** {exc}")
            st.stop()
        except Exception as exc:
            status.update(label="Fetch failed.", state="error")
            st.error(
                f"**Could not fetch the page.**\n\n{exc}\n\n"
                "Check the URL is correct and the site is publicly accessible."
            )
            st.stop()

    # --- LLM extraction ---
    with st.spinner(f"Extracting insights with `{model}` …"):
        try:
            insights = generate_insights(scraped, url, model)
        except OllamaConnectionError as exc:
            st.error(f"**Ollama connection error:** {exc}")
            st.stop()
        except OllamaResponseError as exc:
            st.error(f"**Ollama response error:** {exc}")
            st.stop()
        except Exception as exc:
            st.error(f"**Unexpected error:** {exc}")
            st.stop()

    # Persist to session state
    st.session_state["active_url"] = url
    st.session_state["scraped"]    = scraped
    st.session_state["insights"]   = insights
    st.session_state["history"]    = []          # reset history for new URL
    st.session_state["followup_answer"] = ""

# ---------------------------------------------------------------------------
# Display insights (persisted across reruns)
# ---------------------------------------------------------------------------

if st.session_state["insights"]:
    scraped  = st.session_state["scraped"]
    insights = st.session_state["insights"]
    url      = st.session_state["active_url"]

    st.divider()

    # Scraped metadata in a collapsed expander
    with st.expander("Scraped page details", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Title:** {scraped['title']}")
            if scraped["meta_description"]:
                st.markdown(f"**Meta description:** {scraped['meta_description']}")
            st.markdown(f"**Characters extracted:** {len(scraped['main_text']):,}")
        with col2:
            contacts = scraped.get("detected_contacts", {})
            if contacts.get("emails"):
                st.markdown("**Emails:** " + " · ".join(contacts["emails"]))
            if contacts.get("phones"):
                st.markdown("**Phones:** " + " · ".join(contacts["phones"]))
            if scraped.get("detected_social_links"):
                st.markdown(
                    "**Social links:**\n"
                    + "\n".join(f"- {l}" for l in scraped["detected_social_links"])
                )

    # Main insights output
    st.subheader(f"Insights — {scraped['title']}")
    st.markdown(insights)

    # Download button
    md_bytes = insights.encode("utf-8")
    stem = scraped["title"].lower().replace(" ", "_")[:40]
    st.download_button(
        label="⬇️ Download insights (.md)",
        data=md_bytes,
        file_name=f"{stem}_insights.md",
        mime="text/markdown",
    )

    # -----------------------------------------------------------------------
    # Follow-up Q&A section
    # -----------------------------------------------------------------------

    st.divider()
    st.subheader("💬 Ask a follow-up question")
    st.caption(
        "Questions are answered using the already-extracted page content — "
        "no re-scraping."
    )

    # Show prior Q&A turns
    if st.session_state["history"]:
        with st.expander(
            f"Conversation history ({len(st.session_state['history'])} turns)",
            expanded=False,
        ):
            for i, (q, a) in enumerate(st.session_state["history"], start=1):
                st.markdown(f"**Q{i}:** {q}")
                st.markdown(f"**A{i}:** {a}")
                if i < len(st.session_state["history"]):
                    st.divider()

    # Input and submit
    followup_q = st.text_area(
        "Your question",
        placeholder="e.g. What services do they offer in Melbourne?",
        height=80,
        key="followup_input",
    )

    ask_btn = st.button("Ask", type="secondary", disabled=not ollama_ok)

    if ask_btn:
        question = followup_q.strip()
        if not question:
            st.warning("Please type a question.")
        else:
            with st.spinner(f"Answering with `{model}` …"):
                try:
                    answer = answer_followup(
                        scraped=scraped,
                        url=url,
                        insights=insights,
                        history=st.session_state["history"],
                        question=question,
                        model=model,
                    )
                except OllamaConnectionError as exc:
                    st.error(f"**Ollama connection error:** {exc}")
                    st.stop()
                except OllamaResponseError as exc:
                    st.error(f"**Ollama response error:** {exc}")
                    st.stop()
                except Exception as exc:
                    st.error(f"**Unexpected error:** {exc}")
                    st.stop()

            # Append to history and store latest answer separately for display
            st.session_state["history"].append((question, answer))
            st.session_state["followup_answer"] = answer
            st.rerun()  # refresh to clear the text area and show updated history

    # Show the most recent answer prominently
    if st.session_state.get("followup_answer"):
        latest_q, latest_a = st.session_state["history"][-1]
        st.markdown(f"**Q:** {latest_q}")
        st.info(latest_a)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.divider()
st.caption(
    "Website Insight Extractor · Powered by Ollama · "
    "No data leaves your machine."
)
