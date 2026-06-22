"""DB CRUD helpers for profiles, settings, email drafts, and notes."""

import json
from datetime import datetime
from typing import Optional

from .models import get_db


# ---------------------------------------------------------
# PROFILES
# ---------------------------------------------------------

def save_profile(profile_dict: dict, confidence: dict, funding_info: dict,
                 competitors: list, chat_history: list, search_depth: str,
                 job_signals: dict = None, tech_stack: dict = None) -> int:
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO profiles
                (company_name, core_product, recent_news, pain_points, pitch_angle,
                 confidence, funding_info, competitors, chat_history, search_depth,
                 job_signals, tech_stack, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile_dict["company_name"],
            profile_dict["core_product"],
            profile_dict["recent_news"],
            json.dumps(profile_dict["pain_points"]),
            profile_dict["pitch_angle"],
            json.dumps(confidence),
            json.dumps(funding_info),
            json.dumps(competitors),
            json.dumps(chat_history),
            search_depth,
            json.dumps(job_signals or {}),
            json.dumps(tech_stack  or {}),
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ))
        conn.commit()
        return cur.lastrowid


def load_all_profiles() -> list:
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM profiles ORDER BY created_at DESC"
        ).fetchall()


def delete_profile(profile_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        conn.commit()


def row_to_dict(row) -> dict:
    d = dict(row)
    d["pain_points"]  = json.loads(d["pain_points"]   or "[]")
    d["chat_history"] = json.loads(d["chat_history"]  or "[]")
    d["confidence"]   = json.loads(d["confidence"]    or "{}")
    d["funding_info"] = json.loads(d["funding_info"]  or "{}")
    d["competitors"]  = json.loads(d["competitors"]   or "[]")
    d["job_signals"]  = json.loads(d["job_signals"]   or "{}")
    d["tech_stack"]   = json.loads(d["tech_stack"]    or "{}")
    d["intent_score"] = json.loads(d["intent_score"]  or "null") if d.get("intent_score") else None
    return d


def save_intent_score(profile_id: int, score_dict: dict):
    with get_db() as conn:
        conn.execute(
            "UPDATE profiles SET intent_score = ? WHERE id = ?",
            (json.dumps(score_dict), profile_id),
        )
        conn.commit()


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

def load_setting(key: str) -> str:
    with get_db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else ""


def save_setting(key: str, value: str):
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()


# ---------------------------------------------------------
# EMAIL DRAFTS
# ---------------------------------------------------------

def save_email_draft(company_name: str, subject: str, body: str,
                     tone: str, is_enhanced: bool = False,
                     base_draft_id: Optional[int] = None) -> int:
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO email_drafts
                (company_name, subject, body, tone, is_enhanced, base_draft_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            company_name, subject, body, tone,
            1 if is_enhanced else 0,
            base_draft_id,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ))
        conn.commit()
        return cur.lastrowid


def load_drafts_for_company(company_name: str) -> list:
    with get_db() as conn:
        return conn.execute("""
            SELECT * FROM email_drafts WHERE company_name = ?
            ORDER BY created_at DESC
        """, (company_name,)).fetchall()


def delete_email_draft(draft_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM email_drafts WHERE id = ?", (draft_id,))
        conn.commit()


# ---------------------------------------------------------
# NOTES
# ---------------------------------------------------------

def save_note(company_name: str, note: str) -> int:
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO notes (company_name, note, created_at)
            VALUES (?, ?, ?)
        """, (company_name, note, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        return cur.lastrowid


def load_notes(company_name: str) -> list:
    with get_db() as conn:
        return conn.execute("""
            SELECT * FROM notes WHERE company_name = ?
            ORDER BY created_at DESC
        """, (company_name,)).fetchall()


def delete_note(note_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()


# ---------------------------------------------------------
# PROJECTS (RAG knowledge bases)
# ---------------------------------------------------------

def create_project(name: str, description: str = "") -> int:
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO projects (name, description, created_at)
            VALUES (?, ?, ?)
        """, (name.strip(), description.strip(), datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        return cur.lastrowid


def load_projects() -> list:
    with get_db() as conn:
        return conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()


def get_project(project_id: int):
    with get_db() as conn:
        return conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()


def delete_project(project_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM rag_documents WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()


def add_rag_document(project_id: int, filename: str, source_type: str, chunk_count: int) -> int:
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO rag_documents (project_id, filename, source_type, chunk_count, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (project_id, filename, source_type, chunk_count,
              datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        return cur.lastrowid


def load_rag_documents(project_id: int) -> list:
    with get_db() as conn:
        return conn.execute("""
            SELECT * FROM rag_documents WHERE project_id = ?
            ORDER BY created_at DESC
        """, (project_id,)).fetchall()


def delete_rag_document(document_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM rag_documents WHERE id = ?", (document_id,))
        conn.commit()


# ---------------------------------------------------------
# MCP SERVERS (external tool sources)
# ---------------------------------------------------------

def add_mcp_server(name: str, transport: str, command: str = "", url: str = "") -> int:
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO mcp_servers (name, transport, command, url, enabled, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
        """, (name.strip(), transport, command.strip(), url.strip(),
              datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        return cur.lastrowid


def load_mcp_servers(enabled_only: bool = False) -> list:
    with get_db() as conn:
        query = "SELECT * FROM mcp_servers"
        if enabled_only:
            query += " WHERE enabled = 1"
        query += " ORDER BY created_at DESC"
        return conn.execute(query).fetchall()


def set_mcp_server_enabled(server_id: int, enabled: bool):
    with get_db() as conn:
        conn.execute("UPDATE mcp_servers SET enabled = ? WHERE id = ?",
                     (1 if enabled else 0, server_id))
        conn.commit()


def delete_mcp_server(server_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM mcp_servers WHERE id = ?", (server_id,))
        conn.commit()
