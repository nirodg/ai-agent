"""LLM client + ReAct agent factory."""

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from app.tools.web_search import free_duckduckgo_search

from .settings import (
    get_llm_model,
    get_llm_provider,
    get_llm_timeout,
    get_ollama_base_url,
    get_ollama_client_kwargs,
    get_openrouter_api_key,
    get_openrouter_base_url,
    get_perplexity_api_key,
    get_perplexity_base_url,
)


def get_llm_client(temperature: float = 0.0):
    provider = get_llm_provider()
    model_name = get_llm_model(provider)
    timeout_seconds = get_llm_timeout()

    if provider == "openrouter":
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            base_url=get_openrouter_base_url(),
            api_key=get_openrouter_api_key() or "missing-openrouter-key",
            request_timeout=timeout_seconds,
        )

    if provider == "perplexity":
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            base_url=get_perplexity_base_url(),
            api_key=get_perplexity_api_key() or "missing-pplx-key",
            request_timeout=timeout_seconds,
        )

    if provider == "ollama":
        return ChatOllama(
            model=model_name,
            temperature=temperature,
            base_url=get_ollama_base_url(),
            client_kwargs=get_ollama_client_kwargs(timeout_seconds),
        )

    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        request_timeout=timeout_seconds,
    )


def invoke_with_provider_fallback(prompt: str, temperature: float, where: str) -> str:
    model = get_llm_client(temperature=temperature)
    return model.invoke(prompt).content.strip()


def build_agent(system_prompt: str, temperature: float = 0.0,
                project_id: int | None = None, include_mcp: bool = True):
    """Build a ReAct agent.

    - When ``project_id`` is set, a project-scoped RAG knowledge-base search tool
      is added so the agent can read that project's private data.
    - When ``include_mcp`` is True, tools from any enabled external MCP servers
      are appended, letting the agent consume third-party capabilities.
    """
    model = get_llm_client(temperature=temperature)
    tools = [free_duckduckgo_search]

    if project_id is not None:
        try:
            from app.rag.retriever import make_rag_tool
            tools.append(make_rag_tool(project_id))
        except Exception:
            pass

    if include_mcp:
        try:
            from app.mcp import load_external_mcp_tools
            tools.extend(load_external_mcp_tools())
        except Exception:
            pass

    agent = create_react_agent(
        model=model,
        tools=tools,
        prompt=system_prompt,
    )
    return agent, model


def test_ollama_connection() -> str:
    model = ChatOllama(
        model=get_llm_model("ollama"),
        base_url=get_ollama_base_url(),
        temperature=0.0,
        client_kwargs=get_ollama_client_kwargs(get_llm_timeout()),
    )
    response = model.invoke("Reply with exactly: OK")
    return response.content.strip()
