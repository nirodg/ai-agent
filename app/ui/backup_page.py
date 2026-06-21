"""DB Backup & Restore page."""

from datetime import datetime

import streamlit as st

from app.db import DB_PATH
from app.services.backup import create_backup, list_backups, restore_backup


def render_backup_page():
    st.title("🗄 DB Backup & Restore")

    st.markdown("### ⬇️ Create Backup")
    if st.button("Create backup now", use_container_width=False):
        dst = create_backup()
        st.success(f"Backup saved: `{dst}`")

    st.markdown("### 📦 Download Backup")
    if DB_PATH.exists():
        st.download_button(
            "⬇️ Download current DB",
            data=DB_PATH.read_bytes(),
            file_name=f"enrichment_profiles_{datetime.now().strftime('%Y%m%d_%H%M')}.db",
            mime="application/octet-stream",
            use_container_width=False,
        )

    backups = list_backups()
    if backups:
        st.markdown("### 🕐 Local Backups")
        for bp in backups[:10]:
            col_name, col_dl = st.columns([5, 1])
            with col_name:
                st.caption(str(bp.name))
            with col_dl:
                st.download_button(
                    "⬇️", data=bp.read_bytes(),
                    file_name=bp.name,
                    mime="application/octet-stream",
                    key=f"dl_{bp.name}",
                )

    st.divider()
    st.markdown("### ⬆️ Restore from File")
    st.warning("⚠️ Restoring will **replace** the current database. This cannot be undone.")
    uploaded = st.file_uploader("Upload a .db backup file", type=["db"])
    if uploaded:
        if st.button("🔁 Restore this backup", type="primary"):
            create_backup()   # auto-backup before restore
            restore_backup(uploaded.read())
            st.success("Database restored. Please restart the app.")
