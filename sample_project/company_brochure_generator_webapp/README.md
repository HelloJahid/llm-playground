# Company Brochure Generator

A Streamlit app that scrapes any public company website and uses a **locally-running Ollama model** to produce a structured, ready-to-use company brochure — no paid API keys required.

---

## Features

- Paste any URL → get a professional Markdown brochure in seconds
- Streaming output (watch the brochure appear token-by-token)
- Optional internal-link crawling for richer content
- Download as `.md` (and optionally `.pdf` with `reportlab`)
- 100% local inference via [Ollama](https://ollama.com) — your data never leaves your machine

---

## Project structure

```
sample_project/
    └── company_brochure_generator_app/
        ├── streamlit_app.py   # Streamlit UI
        ├── brochure.py        # Prompt construction & LLM orchestration
        ├── scrape.py          # Web scraping utilities
        ├── ollama_client.py   # HTTP client for Ollama
        ├── requirements.txt   # Python dependencies
        ├── .env.example       # Placeholder (no secrets needed)
        └── README.md          # This file
```

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11 + | Earlier versions untested |
| Ollama | latest | [ollama.com/download](https://ollama.com/download) |
| An Ollama model | any | See step 3 below |

---

## Setup

### 1. Create the project folders

```bash
mkdir -p sample_project/app/company_brochure_generator
cd sample_project/app/company_brochure_generator
```

### 2. Create and activate a virtual environment

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

Optional — enable PDF export:

```bash
pip install reportlab
```

### 4. Install and start Ollama

Download Ollama from [https://ollama.com/download](https://ollama.com/download), then:

```bash
# Start the Ollama server (runs in the background)
ollama serve
```

> On macOS, Ollama may start automatically after installation. Check the menu-bar icon.

### 5. Pull a model

```bash
# Recommended — good balance of speed and quality (~4.7 GB)
ollama pull llama3.1:8b

# Lighter option (~2.0 GB, faster on CPU)
ollama pull gemma3:4b

# Other options
ollama pull mistral
ollama pull phi3
```

List all locally available models at any time:

```bash
ollama list
```

### 6. Run the app

```bash
# From the company_brochure_generator directory
streamlit run streamlit_app.py
```

Streamlit will open a browser tab at `http://localhost:8501`.

---

## Usage

1. Check that the sidebar shows **Ollama is running** (green tick).
2. Select your model from the dropdown (or type the name if none are listed).
3. Paste a company URL into the text box.
4. (Optional) Toggle **Follow internal links** to crawl up to 5 sub-pages for more content.
5. Click **Generate brochure**.
6. Watch the brochure stream into the page.
7. Use the **Download** buttons to save the result.

---

## Troubleshooting

### "Ollama is NOT running" in the sidebar

Ollama is not reachable at `http://localhost:11434`.

```bash
# Start it manually
ollama serve
```

If `ollama serve` says "address already in use", Ollama is already running — refresh the browser page.

### Model name not found / `model not found` error

The model name you typed does not match any pulled model.

```bash
# See what is available locally
ollama list

# Pull the model you want
ollama pull llama3.1:8b
```

Model names are case-sensitive and must include the tag (e.g. `llama3.1:8b`, not `llama3`).

### Generation is very slow

- Use a smaller model (`gemma3:4b`, `phi3`, `mistral`).
- Disable "Follow internal links" to reduce prompt size.
- Lower the temperature slider does not affect speed, but a GPU-accelerated setup will be significantly faster than CPU-only inference.

### "Could not fetch the page" scraping error

- The site may block bots. Try a different URL or check the site is publicly accessible.
- Corporate intranets, login-gated pages, and JavaScript-rendered single-page apps (SPAs) are not supported.

### PDF download button not showing

Install `reportlab`:

```bash
pip install reportlab
```

Then restart Streamlit (`Ctrl+C` then `streamlit run streamlit_app.py`).

---

## Environment variables

No environment variables or API keys are required. The `.env.example` file is provided for completeness in case you extend the app later.

---

## Licence

MIT — do whatever you like with this code.
