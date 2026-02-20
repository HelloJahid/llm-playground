from langchain_community.tools import DuckDuckGoSearchRun
from langchain.tools import Tool

# DuckDuckGo requires no API key — perfect for getting started
_search = DuckDuckGoSearchRun()

tools = [
    Tool(
        name="web_search",
        func=_search.run,
        description=(
            "Useful for searching current, up-to-date information on the web. "
            "Use this whenever you need facts, news, or data you don't know. "
            "Input should be a concise search query string."
        ),
    )
]
