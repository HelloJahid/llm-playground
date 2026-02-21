# Website Insight Extractor

A Streamlit app that scrapes any public website and uses a **locally-running Ollama model** to extract structured insights — no paid APIs, no data leaving your machine.

---

## What it produces

For any URL you paste in, the app returns:

- **Overview** — what the organisation is and what it does
- **Mission** — stated purpose or values (inferred with a label if not explicit)
- **Important Information** — key facts, offerings, audience, contacts, policies, and anything else explicitly present

After extraction, you can ask **follow-up questions** about the same page. The app answers from the already-extracted content — it never re-scrapes unless you change the URL.

---

## Project structure

```
sample_project/
└── website_insight_extractor_webapp/
    ├── streamlit_app.py   # Streamlit UI and session management
    ├── extract.py         # Prompt construction and LLM orchestration
    ├── scrape.py          # Web scraping utilities
    ├── ollama_client.py   # HTTP client for local Ollama
    ├── requirements.txt   # Python dependencies
    └── README.md          # This file
```

The app lives inside the `llm-playground` monorepo which uses **uv** for environment management. The root `.venv` and `pyproject.toml` are shared across all sub-projects.

---

## Prerequisites

| Requirement | Version  | Notes |
|---|---|---|
| Python | 3.11+    | Managed by uv at the repo root |
| uv | latest   | [docs.astral.sh/uv](https://docs.astral.sh/uv) |
| Ollama | latest   | [ollama.com/download](https://ollama.com/download) |
| A pulled model | any | See step 2 below |

---

## Setup

### 1. Install dependencies

From the **repo root** (`llm-playground/`):

```bash
uv add streamlit requests beautifulsoup4 lxml
```

Or, if you prefer a standalone virtual environment outside the monorepo:

```bash
cd sample_project/website_insight_extractor_webapp
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Install Ollama and pull a model

Download Ollama from [https://ollama.com/download](https://ollama.com/download), then:

```bash
# Start the Ollama server
ollama serve

# Pull the default model (~4.7 GB, good balance of speed and quality)
ollama pull llama3.1:8b

# Lighter alternatives
ollama pull gemma3:4b      # ~2.0 GB, faster on CPU
ollama pull mistral        # ~4.1 GB, strong reasoning
ollama pull phi3           # ~2.2 GB, very fast

# See all locally available models
ollama list
```

> On macOS, Ollama may start automatically after installation — check the menu-bar icon.

### 3. Run the app

**Using uv (recommended for this repo):**

```bash
# From the repo root: llm-playground/
uv run streamlit run sample_project/website_insight_extractor_webapp/streamlit_app.py
```

**Using an activated standalone venv:**

```bash
# From the webapp directory
streamlit run app.py
```

Streamlit opens at **http://localhost:8501**.

---

## Usage

1. Confirm the sidebar shows **Ollama is running** (green tick).
2. Select a model from the dropdown, or type a model tag manually.
3. Paste a company or organisation URL into the text box.
4. Click **Extract insights** — the app scrapes the page and calls Ollama.
5. Read the structured output: Overview, Mission, Important Information.
6. Use **Ask a follow-up question** to dig deeper without re-scraping.
7. Click **Download insights (.md)** to save the output.
8. Click **Clear session** in the sidebar to start fresh.

---

## Troubleshooting

### "Ollama is NOT running" in the sidebar

```bash
ollama serve
```

If that says "address already in use", Ollama is already running — just refresh the browser page.

### `model not found` error from Ollama

The model tag you entered does not match any pulled model.

```bash
ollama list                  # see what you have locally
ollama pull llama3.1:8b      # pull the one you want
```

Model tags are case-sensitive and must include the version suffix (e.g. `llama3.1:8b`, not `llama3`).

### "Could not fetch the page" error

- The site may block automated requests (Cloudflare, login walls, SPAs).
- JavaScript-rendered pages (React, Vue, Angular) are not supported — the scraper reads static HTML only.
- Try a different URL, or the site's `/about` or `/contact` sub-page which are often static.

### Generation is very slow

- Switch to a lighter model: `gemma3:4b`, `phi3`, or `mistral`.
- A GPU-accelerated setup (NVIDIA with CUDA, or Apple Silicon with Metal) is significantly faster than CPU-only inference.
- Disable unused Streamlit tabs or background processes to free RAM.

### Follow-up answers seem off or incomplete

- The follow-up uses the same ~6 000 character window as the initial extraction.
  Very long pages are truncated — some detail may not be in the context.
- Rephrase the question to be more specific, or refer to a section heading from the insights output.

### Answers contain invented facts

Lower the temperature is already set to 0.2 (highly factual). If hallucinations persist:
- Try a larger or more capable model (e.g. `llama3.1:70b` if you have enough VRAM).
- The site may have very little textual content — inspect the "Scraped page details" expander to see how much was extracted.

---

## Environment variables

No environment variables or API keys are required. All inference is local via Ollama.
