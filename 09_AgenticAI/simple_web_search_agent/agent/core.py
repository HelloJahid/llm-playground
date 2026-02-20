from langchain import hub
from langchain.agents import create_react_agent, AgentExecutor
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI

from agent.tools import tools


def build_agent() -> AgentExecutor:
    """
    Build and return the ReAct agent.

    The agent follows the pattern:
      Thought → Action (web_search) → Observation → … → Final Answer

    max_iterations=6 caps the search loop so it can't spin forever.
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)

    # Standard ReAct prompt from LangChain Hub
    prompt = hub.pull("hwchase17/react")

    agent = create_react_agent(llm, tools, prompt)

    # Short-term memory — passes full conversation history into every prompt
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
    )

    return AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=6,
    )
