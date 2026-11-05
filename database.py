"""
database.py – SQLite-backed persistent storage for the Research Studio.

Tables
------
reports        – generated research reports
documents      – uploaded document records
conversations  – AI assistant conversation turns
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_DIR = Path(__file__).resolve().parent.parent
_DB_PATH = _PROJECT_DIR / "research_studio.db"


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create tables if they do not already exist."""
    with _get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                topic       TEXT    NOT NULL,
                report_text TEXT    NOT NULL,
                sources_json TEXT   NOT NULL DEFAULT '[]',
                wiki_sources TEXT   NOT NULL DEFAULT '[]',
                academic_sources TEXT NOT NULL DEFAULT '[]',
                created_at  TEXT    NOT NULL,
                word_count  INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS documents (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                filename    TEXT NOT NULL,
                file_type   TEXT NOT NULL,
                char_count  INTEGER NOT NULL DEFAULT 0,
                summary_text TEXT,
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT NOT NULL,
                role        TEXT NOT NULL,
                content     TEXT NOT NULL,
                created_at  TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_reports_created  ON reports(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_docs_created     ON documents(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_conv_session     ON conversations(session_id);
            """
        )
    logger.info("Database initialised at %s", _DB_PATH)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

def save_report(
    topic: str,
    report_text: str,
    sources: list,
    wiki_sources: list | None = None,
    academic_sources: list | None = None,
) -> int:
    """Insert a report row. Returns the new row id."""
    init_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    word_count = len(report_text.split())
    with _get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO reports
                (topic, report_text, sources_json, wiki_sources, academic_sources, created_at, word_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                topic,
                report_text,
                json.dumps(sources or []),
                json.dumps(wiki_sources or []),
                json.dumps(academic_sources or []),
                now,
                word_count,
            ),
        )
        return cur.lastrowid


def list_reports(limit: int = 100) -> list[dict]:
    """Return all reports newest-first."""
    init_db()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, topic, created_at, word_count FROM reports ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_report(report_id: int) -> dict | None:
    """Return a full report row by id, or None if not found."""
    init_db()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM reports WHERE id = ?", (report_id,)
        ).fetchone()
    if row is None:
        return None
    d = dict(row)
    for key in ("sources_json", "wiki_sources", "academic_sources"):
        try:
            d[key] = json.loads(d[key])
        except Exception:
            d[key] = []
    return d


def search_reports(query: str) -> list[dict]:
    """Full-text search on topic and report_text."""
    init_db()
    q = f"%{query.strip()}%"
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, topic, created_at, word_count
            FROM   reports
            WHERE  topic LIKE ? OR report_text LIKE ?
            ORDER  BY created_at DESC
            LIMIT  50
            """,
            (q, q),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_report(report_id: int) -> None:
    init_db()
    with _get_conn() as conn:
        conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

def save_document(
    filename: str,
    file_type: str,
    char_count: int,
    summary_text: str = "",
) -> int:
    """Insert a document record. Returns the new row id."""
    init_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO documents (filename, file_type, char_count, summary_text, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (filename, file_type, char_count, summary_text, now),
        )
        return cur.lastrowid


def list_documents(limit: int = 100) -> list[dict]:
    init_db()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM documents ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_document(doc_id: int) -> None:
    init_db()
    with _get_conn() as conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

def save_message(session_id: str, role: str, content: str) -> None:
    init_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO conversations (session_id, role, content, created_at) VALUES (?,?,?,?)",
            (session_id, role, content, now),
        )


def get_conversation(session_id: str) -> list[dict]:
    init_db()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM conversations WHERE session_id=? ORDER BY id",
            (session_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def clear_conversation(session_id: str) -> None:
    init_db()
    with _get_conn() as conn:
        conn.execute("DELETE FROM conversations WHERE session_id=?", (session_id,))


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def get_stats() -> dict:
    """Return application-wide counts for the dashboard."""
    init_db()
    with _get_conn() as conn:
        total_reports = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        total_docs = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        recent_topics = conn.execute(
            "SELECT topic, created_at FROM reports ORDER BY created_at DESC LIMIT 5"
        ).fetchall()
    return {
        "total_reports": total_reports,
        "total_documents": total_docs,
        "recent_topics": [dict(r) for r in recent_topics],
    }
