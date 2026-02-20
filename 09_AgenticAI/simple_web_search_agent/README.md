# 🔍 Personal Research Assistant — Agentic AI

A minimal but genuinely **agentic** AI that autonomously searches the web, reasons over results, and writes you a clean answer — all in ~100 lines of Python.

Built to demonstrate the **ReAct loop** (Reason → Act → Observe → Repeat) without any complex infrastructure.

---

## 🎬 Demo

> **You:** *"What are the latest developments in quantum computing?"*

```
Thought: I need to find current information on quantum computing.
Action: web_search("latest quantum computing developments 2025")
Observation: [DuckDuckGo results...]
Thought: I have enough information to answer.
Final Answer: Researchers at UNSW have developed a silicon quantum processor...
```

The agent's full thought process streams **live in the UI** as it works.

---

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| LLM | OpenAI GPT-4o |
| Search Tool | DuckDuckGo (no API key needed) |
| Agent Framework | LangChain (ReAct pattern) |
| UI | Streamlit |

---

## 🗺️ Agentic Concepts Covered

| Concept | Implementation |
|---|---|
| **Tool use** | `web_search` tool backed by DuckDuckGo |
| **Reasoning** | GPT-4o decides *when* and *what* to search |
| **Memory** | Full conversation history passed each turn |
| **Autonomy** | Loops until it has a complete answer (max 6 iterations) |
| **Observability** | Every Thought / Action / Observation shown live in UI |

---

## 📁 Project Structure

```
simple_web_search_agent/
├── .env                  # Your OPENAI_API_KEY (never committed)
├── .gitignore
├── requirements.txt
├── agent/
│   ├── __init__.py
│   ├── tools.py          # DuckDuckGo search tool definition
│   └── core.py           # LangChain ReAct agent + memory
└── app.py                # Streamlit UI — entry point
```

---

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/HelloJahid/AgenticAI.git
cd AgenticAI/simple_web_search_agent
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set your API key

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=sk-...your-key-here...
```

> You only need an **OpenAI API key**. DuckDuckGo search requires no key.

### 5. Run

```bash
streamlit run app.py
```

Open **http://localhost:8501** and start researching.

---

## 🔄 How the ReAct Loop Works

```
┌─────────────────────────────────────────────────┐
│                  User Question                  │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │    Thought     │  GPT-4o reasons about what it needs
              └───────┬────────┘
                      │
                      ▼
              ┌────────────────┐
              │     Action     │  Calls web_search(query)
              └───────┬────────┘
                      │
                      ▼
              ┌────────────────┐
              │  Observation   │  Reads DuckDuckGo results
              └───────┬────────┘
                      │
              ┌───────▼────────┐
              │  Enough info?  │
              └──┬─────────┬───┘
                 │ No      │ Yes
                 │         ▼
                 │  ┌─────────────────┐
                 │  │  Final Answer   │
                 │  └─────────────────┘
                 │
                 └──► (loop back to Thought, max 6 times)
```

---

## 🚀 Extensions

Once the core loop is working, level it up:

- **Add a calculator tool** — give the agent arithmetic ability
- **Long-term memory** — plug in a vector store (e.g. ChromaDB) for persistent memory
- **Multi-agent** — one agent researches, another writes/formats
- **Swap the LLM** — try Claude (Anthropic) instead of GPT-4o
- **Better search** — replace DuckDuckGo with [Tavily](https://tavily.com) for cleaner results

---

## 📦 Dependencies

```
langchain==0.3.19
langchain-openai==0.3.7
langchain-community==0.3.18
duckduckgo-search==7.5.0
streamlit==1.42.2
python-dotenv==1.0.1
```

---

## 📄 License

MIT — free to use, modify, and build on.

---

*Built as a beginner-friendly introduction to agentic AI patterns.*
