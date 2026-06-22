"""Google Drive connector — import exported document text into a project.

Uses a service-account JSON (GOOGLE_APPLICATION_CREDENTIALS) when available.
Google client libraries are imported lazily so the dependency stays optional.
"""

import io
import os

from app.db import load_setting
from app.rag.ingest import ingest_file


def _service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds_path = (
        load_setting("google_credentials_path")
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        or ""
    ).strip()
    if not creds_path or not os.path.exists(creds_path):
        raise ValueError(
            "Google credentials not configured. Set GOOGLE_APPLICATION_CREDENTIALS "
            "to a service-account JSON path."
        )
    creds = service_account.Credentials.from_service_account_file(
        creds_path, scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build("drive", "v3", credentials=creds)


# Google Docs/Sheets/Slides need exporting to a downloadable format.
_EXPORT = {
    "application/vnd.google-apps.document": ("application/pdf", ".pdf"),
    "application/vnd.google-apps.spreadsheet": ("text/csv", ".csv"),
    "application/vnd.google-apps.presentation": ("application/pdf", ".pdf"),
}


def import_file(project_id: int, file_id: str) -> int:
    """Import a single Google Drive file into the project. Returns chunk count."""
    from googleapiclient.http import MediaIoBaseDownload

    service = _service()
    meta = service.files().get(fileId=file_id, fields="name, mimeType").execute()
    name = meta.get("name", file_id)
    mime = meta.get("mimeType", "")

    if mime in _EXPORT:
        export_mime, ext = _EXPORT[mime]
        request = service.files().export_media(fileId=file_id, mimeType=export_mime)
        if not name.endswith(ext):
            name += ext
    else:
        request = service.files().get_media(fileId=file_id)

    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    return ingest_file(project_id, name, buf.getvalue())
