import streamlit as st
from dotenv import load_dotenv
from langchain_community.callbacks.streamlit import StreamlitCallbackHandler

from agent.core import build_agent

# Load OPENAI_API_KEY from .env
load_dotenv()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Research Assistant",
    page_icon="🔍",
    layout="centered",
)

st.title("🔍 Personal Research Assistant")
st.caption("Powered by GPT-4o + DuckDuckGo — searches the web so you don't have to")

# ── Session state ─────────────────────────────────────────────────────────────
# Build the agent once per session so memory carries across questions
if "agent" not in st.session_state:
    with st.spinner("Initialising agent…"):
        st.session_state.agent = build_agent()

if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Render past messages ──────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Chat input ────────────────────────────────────────────────────────────────
if question := st.chat_input("Ask me anything…"):
    # Show user message
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    # Run agent — StreamlitCallbackHandler streams each
    # Thought / Action / Observation step live inside the assistant bubble
    with st.chat_message("assistant"):
        cb = StreamlitCallbackHandler(
            st.container(),
            expand_new_thoughts=True,   # open thought boxes by default
            collapse_completed_thoughts=True,  # collapse them once done
        )
        result = st.session_state.agent.invoke(
            {"input": question},
            {"callbacks": [cb]},
        )
        answer = result["output"]
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
