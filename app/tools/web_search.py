"""DuckDuckGo web search tool with retry/backoff."""

import json

from ddgs import DDGS
from langchain_core.tools import tool
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    reraise=True,
)
def _ddgs_search(query: str, max_results: int = 5) -> list:
    with DDGS() as client:
        return list(client.text(query, max_results=max_results))


@tool
def free_duckduckgo_search(query: str) -> str:
    """Search the web for company information and news."""
    try:
        results = _ddgs_search(query)
        if not results:
            return json.dumps({"query": query, "results": []})
        cleaned = [
            {"title": r.get("title", ""), "snippet": r.get("body", ""), "url": r.get("href", "")}
            for r in results
        ]
        return json.dumps(cleaned, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "query": query})
