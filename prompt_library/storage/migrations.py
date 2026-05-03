"""Schema migrations for the SQLite library DB."""
from __future__ import annotations

import sqlite3
from pathlib import Path

CURRENT_VERSION = 1
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_schema_version(conn: sqlite3.Connection) -> int:
    try:
        row = conn.execute(
            "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return 0  # schema_version table doesn't exist yet


def migrate(conn: sqlite3.Connection) -> None:
    """Bring the DB up to CURRENT_VERSION. Safe to call repeatedly."""
    current = get_schema_version(conn)
    if current >= CURRENT_VERSION:
        return

    if current == 0:
        sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(sql)
        conn.execute("INSERT INTO schema_version(version) VALUES (?)", (1,))
        conn.commit()
    # Future migrations: if current < N, apply v(N-1)→vN here.
