"""Knowledge Base page — manage per-project RAG knowledge bases.

Users create named projects, upload files or pull from external sources
(Notion, Google Drive), and query each project's isolated vector store.
"""

import streamlit as st

from app.db import (
    create_project,
    delete_project,
    delete_rag_document,
    load_projects,
    load_rag_documents,
    row_to_dict,
)


def _rows_to_dicts(rows):
    return [row_to_dict(r) if not isinstance(r, dict) else r for r in rows]


def render_knowledge_page():
    st.markdown("# 📚 Knowledge Base")
    st.caption(
        "Create isolated projects, ingest your business data, and let the agent "
        "answer queries grounded in each project's private knowledge (RAG)."
    )

    projects = _rows_to_dicts(load_projects())

    # ── Create a project ──────────────────────────────────
    with st.expander("➕ New Project", expanded=not projects):
        with st.form("create_project", clear_on_submit=True):
            name = st.text_input("Project name", placeholder="Acme Sales Q1")
            description = st.text_area("Description", placeholder="What this knowledge base is for")
            if st.form_submit_button("Create project", use_container_width=True):
                if name.strip():
                    try:
                        create_project(name, description)
                        st.success(f"Created project '{name.strip()}'.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not create project: {e}")
                else:
                    st.error("Project name is required.")

    if not projects:
        st.info("Create your first project to start building a knowledge base.")
        return

    # ── Select active project ─────────────────────────────
    project_map = {p["name"]: p for p in projects}
    selected_name = st.selectbox("Active project", options=list(project_map.keys()))
    project = project_map[selected_name]
    project_id = project["id"]

    if project.get("description"):
        st.caption(project["description"])

    tab_files, tab_connectors, tab_query, tab_manage = st.tabs(
        ["📄 Files", "🔗 Connectors", "💬 Query", "⚙️ Manage"]
    )

    # ── Files tab ─────────────────────────────────────────
    with tab_files:
        uploaded = st.file_uploader(
            "Upload documents (PDF, DOCX, CSV, TXT, MD)",
            type=["pdf", "docx", "csv", "txt", "md"],
            accept_multiple_files=True,
        )
        if uploaded and st.button("Ingest uploaded files", use_container_width=True):
            from app.rag.ingest import ingest_file

            progress = st.progress(0.0)
            for i, f in enumerate(uploaded, 1):
                try:
                    chunks = ingest_file(project_id, f.name, f.getvalue())
                    st.success(f"{f.name}: {chunks} chunks ingested.")
                except Exception as e:
                    st.error(f"{f.name}: {e}")
                progress.progress(i / len(uploaded))
            st.rerun()

        st.divider()
        st.markdown("#### Ingested documents")
        docs = _rows_to_dicts(load_rag_documents(project_id))
        if not docs:
            st.caption("No documents ingested yet.")
        for d in docs:
            c1, c2 = st.columns([6, 1])
            with c1:
                st.markdown(
                    f"**{d['filename']}** · `{d['source_type']}` · "
                    f"{d['chunk_count']} chunks · {d['created_at']}"
                )
            with c2:
                if st.button("🗑", key=f"doc_del_{d['id']}"):
                    from app.rag.store import delete_by_source

                    delete_by_source(project_id, d["filename"])
                    delete_rag_document(d["id"])
                    st.rerun()

    # ── Connectors tab ────────────────────────────────────
    with tab_connectors:
        st.markdown("#### Notion")
        st.caption("Requires NOTION_API_KEY (env or settings). Share the page with your integration.")
        notion_page = st.text_input("Notion page ID or URL", key="notion_page")
        if st.button("Import from Notion", use_container_width=True):
            from app.rag.connectors import notion

            page_id = notion_page.strip().rstrip("/").split("/")[-1].split("?")[0].split("-")[-1]
            try:
                chunks = notion.import_page(project_id, page_id or notion_page.strip())
                st.success(f"Imported {chunks} chunks from Notion.")
                st.rerun()
            except Exception as e:
                st.error(f"Notion import failed: {e}")

        st.divider()
        st.markdown("#### Google Drive")
        st.caption("Requires GOOGLE_APPLICATION_CREDENTIALS (service-account JSON path).")
        gdrive_id = st.text_input("Google Drive file ID", key="gdrive_id")
        if st.button("Import from Google Drive", use_container_width=True):
            from app.rag.connectors import gdrive

            try:
                chunks = gdrive.import_file(project_id, gdrive_id.strip())
                st.success(f"Imported {chunks} chunks from Google Drive.")
                st.rerun()
            except Exception as e:
                st.error(f"Google Drive import failed: {e}")

    # ── Query tab ─────────────────────────────────────────
    with tab_query:
        st.caption("Search this project's knowledge base directly (semantic retrieval).")
        question = st.text_input("Question", key="rag_question")
        if st.button("Search knowledge base", use_container_width=True) and question.strip():
            from app.rag.store import query

            try:
                results = query(project_id, question.strip(), k=4)
                if not results:
                    st.info("No relevant content found.")
                for i, doc in enumerate(results, 1):
                    src = doc.metadata.get("source", "unknown")
                    with st.expander(f"[{i}] {src}"):
                        st.write(doc.page_content)
            except Exception as e:
                st.error(f"Search failed: {e}")

    # ── Manage tab ────────────────────────────────────────
    with tab_manage:
        st.warning("Deleting a project removes its knowledge base and all ingested data.")
        if st.button("🗑 Delete this project", type="primary", use_container_width=True):
            from app.rag.store import delete_collection

            delete_collection(project_id)
            delete_project(project_id)
            st.success(f"Deleted project '{selected_name}'.")
            st.rerun()
