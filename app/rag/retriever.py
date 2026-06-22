"""RAG retrieval exposed as a LangChain tool the agent can call."""

from langchain_core.tools import tool

from app.rag.store import query


def make_rag_tool(project_id: int):
    """Build a project-scoped RAG retrieval tool.

    The agent receives a tool bound to one project so it can only read that
    project's knowledge base — keeping business data isolated.
    """

    @tool
    def knowledge_base_search(question: str) -> str:
        """Search the current project's private knowledge base (uploaded files,
        CRM exports, Notion pages, etc.) for information relevant to the question.
        Use this before web search when the answer may be in internal documents."""
        docs = query(project_id, question, k=4)
        if not docs:
            return "No relevant information found in the project knowledge base."
        parts = []
        for i, d in enumerate(docs, 1):
            src = d.metadata.get("source", "unknown")
            parts.append(f"[{i}] (source: {src})\n{d.page_content.strip()}")
        return "\n\n".join(parts)

    return knowledge_base_search
