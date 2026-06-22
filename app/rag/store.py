"""ChromaDB-backed per-project vector store.

Each project gets its own isolated Chroma collection so business data never
leaks across projects. Embeddings use the same OpenAI-compatible provider the
rest of the app is configured with (falls back to a local model if unavailable).
"""

from pathlib import Path
from typing import Optional

CHROMA_DIRNAME = "chroma_store"
CHROMA_DIR = Path(CHROMA_DIRNAME)


def _collection_name(project_id: int) -> str:
    return f"project_{project_id}"


def get_embeddings():
    """Return an embeddings object.

    Prefers OpenAI embeddings when an OpenAI key is available; otherwise falls
    back to a local sentence-transformers model so the app works offline / on
    free tiers without an embeddings-capable provider.
    """
    import os

    from app.db import load_setting

    openai_key = (load_setting("openai_api_key") or os.getenv("OPENAI_API_KEY") or "").strip()
    if openai_key and not openai_key.startswith("sk-proj-your_"):
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model="text-embedding-3-small", api_key=openai_key)

    # Local fallback — no API key needed.
    from langchain_community.embeddings import FastEmbedEmbeddings
    return FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")


def get_vectorstore(project_id: int):
    """Return a Chroma vectorstore scoped to a single project."""
    from langchain_chroma import Chroma

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=_collection_name(project_id),
        embedding_function=get_embeddings(),
        persist_directory=str(CHROMA_DIR),
    )


def add_documents(project_id: int, documents: list) -> int:
    """Add LangChain Document objects to a project's collection. Returns count."""
    if not documents:
        return 0
    store = get_vectorstore(project_id)
    store.add_documents(documents)
    return len(documents)


def query(project_id: int, question: str, k: int = 4) -> list:
    """Return the top-k most relevant document chunks for a question."""
    store = get_vectorstore(project_id)
    return store.similarity_search(question, k=k)


def delete_collection(project_id: int):
    """Drop the entire collection for a project (used when deleting a project)."""
    try:
        store = get_vectorstore(project_id)
        store.delete_collection()
    except Exception:
        pass


def delete_by_source(project_id: int, source: str):
    """Delete all chunks that originated from a given source file/URL."""
    try:
        store = get_vectorstore(project_id)
        store.delete(where={"source": source})
    except Exception:
        pass
