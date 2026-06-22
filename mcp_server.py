"""Standalone entry point for the AI-Agent MCP server.

Exposes enrichment, web search and RAG knowledge-base search as MCP tools so
other MCP-compatible clients (Claude Desktop, IDEs, other agents) can consume
this agent's capabilities.

Usage:
    python mcp_server.py
"""

from dotenv import load_dotenv

from app.db import init_db
from app.mcp.server import run

if __name__ == "__main__":
    load_dotenv()
    init_db()
    run()
