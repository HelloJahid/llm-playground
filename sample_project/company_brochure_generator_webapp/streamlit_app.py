"""
streamlit_app.py
----------------
Company Brochure Generator — Streamlit front-end.

Run with:
    streamlit run streamlit_app.py
"""

import sys
import textwrap
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Make sure sibling modules are importable when running from any cwd
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))

from brochure import generate_brochure, stream_brochure
from ollama_client import (
    OllamaConnectionError,
    OllamaResponseError,
    check_ollama_running,
    list_local_models,
)
from scrape import extract_readable_text, fetch_internal_links, fetch_url

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Company Brochure Generator",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar — settings
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("⚙️ Settings")

    # --- Ollama health indicator ---
    ollama_ok = check_ollama_running()
    if ollama_ok:
        st.success("Ollama is running", icon="✅")
    else:
        st.error("Ollama is NOT running", icon="🚫")
        st.markdown(
            "Start it with:\n```\nollama serve\n```\n"
            "Then refresh this page."
        )

    st.divider()

    # --- Model selector ---
    st.subheader("Model")
    local_models = list_local_models()

    default_model = "llama3.1:8b"

    if local_models:
        # Pre-select a sensible default if it is available locally
        default_index = (
            local_models.index(default_model)
            if default_model in local_models
            else 0
        )
        model_choice = st.selectbox(
            "Choose a local model",
            options=local_models,
            index=default_index,
            help="Models already pulled to your machine appear here.",
        )
    else:
        # Ollama not running or no models pulled — fall back to free text
        model_choice = st.text_input(
            "Model name",
            value=default_model,
            help=(
                "Enter the exact Ollama model tag, e.g. `llama3.1:8b`, "
                "`mistral`, `gemma3:4b`.\n\n"
                "Pull a model first with: `ollama pull llama3.1:8b`"
            ),
        )

    st.divider()

    # --- Generation settings ---
    st.subheader("Generation")

    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.4,
        step=0.05,
        help="Lower = more factual, higher = more creative.",
    )

    use_streaming = st.checkbox(
        "Stream output (live preview)",
        value=True,
        help="Show the brochure token-by-token as it is generated.",
    )

    follow_links = st.checkbox(
        "Follow internal links (limited)",
        value=False,
        help=(
            "Fetch up to 5 internal pages and include their text in the "
            "prompt. Makes the brochure richer but slower."
        ),
    )

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------

st.title("📄 Company Brochure Generator")
st.caption("Powered by a local Ollama model — no paid APIs required.")

st.markdown(
    "Paste any company URL below and click **Generate brochure**. "
    "The app will scrape the page, extract the key content, and ask "
    "your local Ollama model to write a structured brochure."
)

url_input = st.text_input(
    "Company website URL",
    placeholder="https://example.com",
    label_visibility="visible",
)

generate_btn = st.button(
    "Generate brochure",
    type="primary",
    disabled=not ollama_ok,
)

# ---------------------------------------------------------------------------
# Generation flow
# ---------------------------------------------------------------------------

if generate_btn:
    url = url_input.strip()

    # --- Input validation ---
    if not url:
        st.warning("Please enter a URL before clicking Generate.")
        st.stop()

    if not url.startswith(("http://", "https://")):
        url = "https://" + url
        st.info(f"Assuming HTTPS — using: `{url}`")

    # --- Scraping ---
    with st.status("Fetching webpage…", expanded=True) as status:
        try:
            st.write(f"Downloading `{url}`…")
            html = fetch_url(url)
            scraped = extract_readable_text(html, url)
            st.write(
                f"Extracted **{len(scraped['main_text'])}** characters "
                f"from *{scraped['title']}*."
            )

            # Optionally crawl internal links
            if follow_links:
                internal_links = fetch_internal_links(html, url, limit=5)
                extra_texts: list[str] = []
                for link in internal_links:
                    try:
                        st.write(f"Fetching internal page: `{link}`")
                        inner_html = fetch_url(link)
                        inner = extract_readable_text(inner_html, link)
                        if inner["main_text"]:
                            extra_texts.append(
                                f"### {inner['title']}\n\n{inner['main_text']}"
                            )
                    except Exception as link_err:
                        st.write(f"⚠️ Skipped `{link}`: {link_err}")

                if extra_texts:
                    combined = (
                        scraped["main_text"]
                        + "\n\n---\n\n"
                        + "\n\n---\n\n".join(extra_texts)
                    )
                    scraped["main_text"] = combined
                    st.write(
                        f"Combined text now **{len(scraped['main_text'])}** characters "
                        f"(after following {len(extra_texts)} internal page(s))."
                    )

            status.update(label="Page fetched successfully.", state="complete")

        except ValueError as exc:
            status.update(label="Invalid URL.", state="error")
            st.error(f"**Invalid URL:** {exc}")
            st.stop()

        except Exception as exc:
            status.update(label="Scraping failed.", state="error")
            st.error(
                f"**Could not fetch the page.**\n\n"
                f"Reason: {exc}\n\n"
                "Check that the URL is correct and the site is publicly accessible."
            )
            st.stop()

    # --- Show scraped metadata ---
    with st.expander("Scraped page details", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Title:** {scraped['title']}")
            st.markdown(f"**Meta description:** {scraped['meta_description'] or '—'}")
        with col2:
            contacts = scraped.get("detected_contacts", {})
            if contacts.get("emails"):
                st.markdown("**Emails:** " + ", ".join(contacts["emails"]))
            if contacts.get("phones"):
                st.markdown("**Phones:** " + ", ".join(contacts["phones"]))
            if scraped.get("detected_social_links"):
                st.markdown(
                    "**Social links:**\n"
                    + "\n".join(f"- {l}" for l in scraped["detected_social_links"])
                )

    # --- LLM generation ---
    st.divider()
    st.subheader(f"Generated brochure — `{scraped['title']}`")

    brochure_text = ""

    if use_streaming:
        # Stream tokens into a Markdown placeholder
        placeholder = st.empty()
        try:
            with st.spinner(f"Generating with `{model_choice}`…"):
                for chunk in stream_brochure(
                    scraped=scraped,
                    url=url,
                    model=model_choice,
                    temperature=temperature,
                ):
                    brochure_text += chunk
                    placeholder.markdown(brochure_text)
        except OllamaConnectionError as exc:
            st.error(f"**Ollama connection error:** {exc}")
            st.stop()
        except OllamaResponseError as exc:
            st.error(f"**Ollama response error:** {exc}")
            st.stop()
        except Exception as exc:
            st.error(f"**Unexpected error during generation:** {exc}")
            st.stop()
    else:
        # Non-streaming — wait for the full response
        with st.spinner(f"Generating with `{model_choice}`… (this may take a minute)"):
            try:
                brochure_text = generate_brochure(
                    scraped=scraped,
                    url=url,
                    model=model_choice,
                    temperature=temperature,
                )
            except OllamaConnectionError as exc:
                st.error(f"**Ollama connection error:** {exc}")
                st.stop()
            except OllamaResponseError as exc:
                st.error(f"**Ollama response error:** {exc}")
                st.stop()
            except Exception as exc:
                st.error(f"**Unexpected error during generation:** {exc}")
                st.stop()

        st.markdown(brochure_text)

    # ---------------------------------------------------------------------------
    # Download options
    # ---------------------------------------------------------------------------

    st.divider()
    st.subheader("Download")

    col_md, col_pdf = st.columns(2)

    # --- Markdown download (always available) ---
    with col_md:
        md_bytes = brochure_text.encode("utf-8")
        filename_stem = (
            scraped["title"]
            .lower()
            .replace(" ", "_")
            .replace("/", "-")[:50]
        )
        st.download_button(
            label="⬇️ Download as Markdown (.md)",
            data=md_bytes,
            file_name=f"{filename_stem}_brochure.md",
            mime="text/markdown",
        )

    # --- PDF download (requires reportlab) ---
    with col_pdf:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.lib.enums import TA_LEFT
            from reportlab.platypus import (
                SimpleDocTemplate,
                Paragraph,
                Spacer,
            )
            from io import BytesIO
            import re as _re

            def _brochure_to_pdf(markdown_text: str) -> bytes:
                """Convert the Markdown brochure to a simple PDF using reportlab."""
                buf = BytesIO()
                doc = SimpleDocTemplate(
                    buf,
                    pagesize=A4,
                    leftMargin=2.5 * cm,
                    rightMargin=2.5 * cm,
                    topMargin=2.5 * cm,
                    bottomMargin=2.5 * cm,
                )
                styles = getSampleStyleSheet()

                # Custom styles
                h1_style = ParagraphStyle(
                    "BrochureH1",
                    parent=styles["Heading1"],
                    fontSize=20,
                    spaceAfter=10,
                )
                h2_style = ParagraphStyle(
                    "BrochureH2",
                    parent=styles["Heading2"],
                    fontSize=14,
                    spaceAfter=6,
                    spaceBefore=14,
                )
                body_style = ParagraphStyle(
                    "BrochureBody",
                    parent=styles["Normal"],
                    fontSize=10,
                    leading=15,
                    spaceAfter=4,
                    alignment=TA_LEFT,
                )
                italic_style = ParagraphStyle(
                    "BrochureItalic",
                    parent=body_style,
                    fontName="Helvetica-Oblique",
                )

                story = []
                for line in markdown_text.splitlines():
                    stripped = line.strip()
                    if not stripped:
                        story.append(Spacer(1, 6))
                        continue
                    if stripped.startswith("# "):
                        story.append(Paragraph(stripped[2:], h1_style))
                    elif stripped.startswith("## "):
                        story.append(Paragraph(stripped[3:], h2_style))
                    elif stripped.startswith(("- ", "* ")):
                        # Bullet point
                        text = "• " + stripped[2:]
                        story.append(Paragraph(text, body_style))
                    elif stripped.startswith("*") and stripped.endswith("*"):
                        # *Italic* line
                        story.append(Paragraph(stripped.strip("*"), italic_style))
                    else:
                        # Replace **bold** with <b>bold</b> for reportlab
                        formatted = _re.sub(
                            r"\*\*(.+?)\*\*", r"<b>\1</b>", stripped
                        )
                        story.append(Paragraph(formatted, body_style))

                doc.build(story)
                return buf.getvalue()

            pdf_bytes = _brochure_to_pdf(brochure_text)
            st.download_button(
                label="⬇️ Download as PDF (.pdf)",
                data=pdf_bytes,
                file_name=f"{filename_stem}_brochure.pdf",
                mime="application/pdf",
            )

        except ImportError:
            st.info(
                "PDF export is not available. "
                "Install `reportlab` to enable it:\n"
                "```\npip install reportlab\n```",
                icon="ℹ️",
            )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.divider()
st.caption(
    "Company Brochure Generator • Powered by Ollama • No data leaves your machine."
)
