"""MCP client — load tools from registered external MCP servers.

External servers are registered in the DB (mcp_servers table). This module
connects to the enabled ones and converts their tools into LangChain tools the
agent can call. Networking is synchronous-friendly via a short-lived event loop
so it can be used from Streamlit without an existing async context.
"""

import asyncio
from typing import List

from app.db import load_mcp_servers


def _server_to_config(row) -> dict:
    transport = (row["transport"] or "stdio").strip()
    if transport == "stdio":
        parts = (row["command"] or "").split()
        if not parts:
            return {}
        return {
            "transport": "stdio",
            "command": parts[0],
            "args": parts[1:],
        }
    # http / sse style transports
    return {
        "transport": transport,
        "url": (row["url"] or "").strip(),
    }


async def _load_tools_async() -> List:
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "langchain-mcp-adapters is not installed. Run: "
            "pip install langchain-mcp-adapters"
        ) from exc

    servers = load_mcp_servers(enabled_only=True)
    connections = {}
    for row in servers:
        cfg = _server_to_config(row)
        if cfg:
            connections[row["name"]] = cfg

    if not connections:
        return []

    client = MultiServerMCPClient(connections)
    return await client.get_tools()


def load_external_mcp_tools() -> List:
    """Return LangChain tools from all enabled external MCP servers.

    Returns an empty list (and never raises) if no servers are configured or the
    optional adapter dependency is missing — keeping the agent usable regardless.
    """
    if not load_mcp_servers(enabled_only=True):
        return []
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            # Already inside an event loop — run in a dedicated thread.
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(lambda: asyncio.run(_load_tools_async())).result()
        return asyncio.run(_load_tools_async())
    except Exception:
        return []
