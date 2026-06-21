"""Database backup and restore helpers."""

import shutil
from datetime import datetime
from pathlib import Path

from app.db import BACKUP_DIR, DB_PATH


def create_backup() -> Path:
    BACKUP_DIR.mkdir(exist_ok=True)
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = BACKUP_DIR / f"enrichment_profiles_{ts}.db"
    shutil.copy2(DB_PATH, dst)
    return dst


def restore_backup(uploaded_bytes: bytes):
    DB_PATH.write_bytes(uploaded_bytes)


def list_backups() -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(BACKUP_DIR.glob("*.db"), reverse=True)
