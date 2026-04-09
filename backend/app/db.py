"""
SQLite connection helpers and schema for extraction session persistence.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from app.config import EXTRACTION_DB_PATH

CREATE_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS schema_migrations (
      version INTEGER PRIMARY KEY
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS extraction_sessions (
      id TEXT PRIMARY KEY,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      title TEXT,
      passport_filename TEXT,
      g28_filename TEXT,
      default_form_url TEXT,
      extracted_json TEXT NOT NULL,
      last_fill_json TEXT,
      notes TEXT
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_extraction_sessions_created_at
    ON extraction_sessions (created_at);
    """,
]


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def get_db_path() -> Path:
    return Path(EXTRACTION_DB_PATH)


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Yield a SQLite connection with foreign keys enabled.

    Commits on success, rolls back on exception. Caller should not commit manually
    unless extending this module.
    """
    path = get_db_path()
    _ensure_parent_dir(path)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Apply incremental SQLite migrations; safe to call on every startup."""
    applied = {int(r["version"]) for r in conn.execute("SELECT version FROM schema_migrations").fetchall()}
    if 1 not in applied:
        conn.execute("INSERT INTO schema_migrations (version) VALUES (1)")
    if 2 not in applied:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(extraction_sessions)").fetchall()]
        if "quality_json" not in cols:
            conn.execute("ALTER TABLE extraction_sessions ADD COLUMN quality_json TEXT")
        conn.execute("INSERT INTO schema_migrations (version) VALUES (2)")


def init_db() -> None:
    """Create database file, tables, indexes, and run migrations."""
    with get_connection() as conn:
        for stmt in CREATE_STATEMENTS:
            conn.execute(stmt)
        _run_migrations(conn)
