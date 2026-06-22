"""Model Context Protocol (MCP) integration.

- server.py: expose this agent's tools to other MCP clients (FastMCP).
- client.py: consume tools from registered external MCP servers.
"""

from app.mcp.client import load_external_mcp_tools

__all__ = ["load_external_mcp_tools"]
