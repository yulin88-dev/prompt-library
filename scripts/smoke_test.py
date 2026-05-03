"""Smoke test: open the DB, run migrations, call one tool stub from each module."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from prompt_library.storage.library import Library
from prompt_library.tools import library_tools, project_tools, prompt_tools


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "smoke.db"
        with Library(db_path) as lib:
            print(f"DB opened at {lib.path}")
            version = lib.conn.execute(
                "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
            ).fetchone()
            print(f"Schema version: {version[0]}")

            tables = [
                row[0]
                for row in lib.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()
            ]
            print(f"Tables: {tables}")

    print("\n--- Tool stub samples ---")
    print(json.dumps(project_tools.add_project("demo", tags=["mcp"]), indent=2))
    print(json.dumps(prompt_tools.add_prompt("demo", "Body text"), indent=2))
    print(json.dumps(library_tools.tag_summary(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
