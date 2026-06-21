"""SQLite connection + schema bootstrap."""

import json
import sqlite3
from pathlib import Path

from app.config import (
    BACKUP_DIRNAME,
    DB_FILENAME,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_MODEL,
    DEFAULT_PROVIDER_MODEL_MAP,
    DEFAULT_SYSTEM_PROMPT,
)

DB_PATH = Path(DB_FILENAME)
BACKUP_DIR = Path(BACKUP_DIRNAME)


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name  TEXT NOT NULL,
                core_product  TEXT,
                recent_news   TEXT,
                pain_points   TEXT,
                pitch_angle   TEXT,
                confidence    TEXT,
                funding_info  TEXT,
                competitors   TEXT,
                chat_history  TEXT,
                search_depth  TEXT,
                job_signals   TEXT,
                tech_stack    TEXT,
                intent_score  TEXT,
                created_at    TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.execute("""
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('system_prompt', ?)
        """, (DEFAULT_SYSTEM_PROMPT,))
        conn.execute("""
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('llm_model_prompt_map', '{}')
        """)
        conn.execute("""
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('llm_model_persona_preset_map', '{}')
        """)
        conn.execute("""
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('ai_model', ?)
        """, (DEFAULT_MODEL,))
        conn.execute("""
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('llm_provider', ?)
        """, (DEFAULT_LLM_PROVIDER,))
        conn.execute("""
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('llm_provider_model_map', ?)
        """, (json.dumps(DEFAULT_PROVIDER_MODEL_MAP),))
        conn.execute("""
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('openrouter_api_key', '')
        """)
        conn.execute("""
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('openrouter_base_url', 'https://openrouter.ai/api/v1')
        """)
        conn.execute("""
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('pplx_api_key', '')
        """)
        conn.execute("""
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('pplx_base_url', 'https://api.perplexity.ai')
        """)
        conn.execute("""
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('ollama_api_key', '')
        """)
        conn.execute("""
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('ollama_base_url', 'https://ollama.com')
        """)
        conn.execute("""
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('ollama_insecure_ssl', 'true')
        """)
        conn.execute("""
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('llm_timeout', '30')
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS email_drafts (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name  TEXT NOT NULL,
                subject       TEXT,
                body          TEXT NOT NULL,
                tone          TEXT,
                is_enhanced   INTEGER DEFAULT 0,
                base_draft_id INTEGER,
                created_at    TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name  TEXT NOT NULL,
                note          TEXT NOT NULL,
                created_at    TEXT NOT NULL
            )
        """)
        # Migrations — safe to run on existing DBs
        for col in ("confidence", "funding_info", "competitors", "search_depth",
                    "job_signals", "tech_stack", "intent_score"):
            try:
                conn.execute(f"ALTER TABLE profiles ADD COLUMN {col} TEXT")
            except Exception:
                pass
        conn.commit()
