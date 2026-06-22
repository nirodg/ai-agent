"""FastMCP server exposing this agent's capabilities as MCP tools.

Run with:  python mcp_server.py

Exposes:
    - enrich_company: run the full enrichment pipeline for a company
    - web_search: free DuckDuckGo web search
    - knowledge_base_search: query a project's RAG knowledge base
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ai-agent")


@mcp.tool()
def web_search(query: str) -> str:
    """Search the web (DuckDuckGo) and return the top results as text."""
    from app.tools.web_search import _ddgs_search

    results = _ddgs_search(query, max_results=5)
    if not results:
        return "No results found."
    return "\n\n".join(
        f"{r.get('title', '')}\n{r.get('href', '')}\n{r.get('body', '')}"
        for r in results
    )


@mcp.tool()
def knowledge_base_search(project_id: int, question: str) -> str:
    """Search a project's private RAG knowledge base for relevant information."""
    from app.rag.store import query as rag_query

    docs = rag_query(project_id, question, k=4)
    if not docs:
        return "No relevant information found in the project knowledge base."
    return "\n\n".join(
        f"(source: {d.metadata.get('source', 'unknown')})\n{d.page_content.strip()}"
        for d in docs
    )


@mcp.tool()
def enrich_company(company_name: str, depth: str = "balanced") -> dict:
    """Run the full enrichment pipeline for a company and return its profile.

    depth: one of 'shallow', 'balanced', 'deep'.
    """
    from app.agents.enrichment_agent import enrich_company as _enrich
    from app.config import DEFAULT_SYSTEM_PROMPT

    d, confidence, funding_info, competitors, job_signals, tech_stack = _enrich(
        company_name, DEFAULT_SYSTEM_PROMPT, depth
    )
    return {
        "profile": d,
        "confidence": confidence,
        "funding_info": funding_info,
        "competitors": competitors,
        "job_signals": job_signals,
        "tech_stack": tech_stack,
    }


def run():
    """Start the MCP server over stdio transport."""
    mcp.run()


if __name__ == "__main__":
    run()
