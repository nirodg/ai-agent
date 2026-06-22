"""Notion connector — pull page/database text into a project knowledge base."""

import os

from app.db import load_setting
from app.rag.ingest import ingest_text


def _client():
    from notion_client import Client

    token = (load_setting("notion_api_key") or os.getenv("NOTION_API_KEY") or "").strip()
    if not token:
        raise ValueError("Notion API key not configured. Set NOTION_API_KEY or save it in settings.")
    return Client(auth=token)


def _rich_text(blocks) -> str:
    return "".join(b.get("plain_text", "") for b in blocks or [])


def _block_to_text(block: dict) -> str:
    btype = block.get("type", "")
    payload = block.get(btype, {})
    if isinstance(payload, dict) and "rich_text" in payload:
        return _rich_text(payload["rich_text"])
    return ""


def import_page(project_id: int, page_id: str) -> int:
    """Import a Notion page's text blocks into the project. Returns chunk count."""
    client = _client()
    page_id = page_id.replace("-", "")
    results = []
    cursor = None
    while True:
        resp = client.blocks.children.list(block_id=page_id, start_cursor=cursor)
        results.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")

    text = "\n".join(t for t in (_block_to_text(b) for b in results) if t.strip())
    if not text.strip():
        return 0
    return ingest_text(project_id, source=f"notion:{page_id}", text=text, source_type="notion")
