"""Library — SQLite-backed CRUD for projects and prompts.

The Library class is the public Python API. The MCP server is a thin facade
over it (so the same code path is exercised whether invoked from Claude
Desktop via stdio or from the Anthropic SDK via direct import).

Real CRUD methods land in Prompt 3 / Prompt 4. For now this module only
opens the DB and runs migrations.
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from prompt_library.config import LIBRARY_PATH
from prompt_library.storage.migrations import migrate

log = logging.getLogger(__name__)


class Library:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path).expanduser() if path else LIBRARY_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        migrate(self.conn)
        log.info("Library opened at %s", self.path)

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "Library":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
