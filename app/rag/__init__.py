"""Retrieval-Augmented Generation (RAG) package.

Per-project ChromaDB knowledge bases with file + external-source ingestion.
"""

from app.rag.ingest import ingest_file, ingest_text
from app.rag.retriever import make_rag_tool
from app.rag.store import (
    add_documents,
    delete_by_source,
    delete_collection,
    get_vectorstore,
    query,
)

__all__ = [
    "ingest_file",
    "ingest_text",
    "make_rag_tool",
    "add_documents",
    "query",
    "get_vectorstore",
    "delete_collection",
    "delete_by_source",
]
