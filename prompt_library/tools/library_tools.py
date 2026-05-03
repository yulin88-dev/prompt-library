"""MCP tool stubs for tag summaries, export/import, and backup.

Real logic lands in Prompt 5 (export/import + tag_summary) and Prompt 6 (backup).
"""
from __future__ import annotations


def tag_summary() -> dict:
    """Counts of items per tag across projects and prompts.

    Returns:
        Dict with by_tag (tag → {projects, prompts}), untagged counts,
        and a list of near_duplicates (case/punctuation variants).
    """
    return {
        "_stub": True,
        "by_tag": {},
        "untagged": {"projects": 0, "prompts": 0},
        "near_duplicates": [],
    }


def export_library(
    kind: str = "all",
    format: str = "markdown",
    dest: str | None = None,
) -> dict:
    """Export projects, prompts, or both to markdown or JSON.

    Args:
        kind: One of 'projects', 'prompts', 'all'.
        format: One of 'markdown', 'json'.
        dest: Optional override for the output directory or file.

    Returns:
        Dict with the list of paths written.
    """
    return {
        "_stub": True,
        "kind": kind,
        "format": format,
        "dest": dest,
        "paths": [],
    }


def import_library(path: str, overwrite: bool = False) -> dict:
    """Import a previously exported markdown tree or JSON file.

    Args:
        path: Path to the export root or JSON file.
        overwrite: If True, conflicts overwrite existing items;
            otherwise conflicts raise an error.

    Returns:
        Dict with imported and skipped counts.
    """
    return {
        "_stub": True,
        "path": path,
        "overwrite": overwrite,
        "imported": 0,
        "skipped": 0,
    }


def backup_library() -> dict:
    """Copy the SQLite library file to ./backups/library_YYYY-MM-DD-HHMM.db.

    Returns:
        Dict with the absolute path of the backup file.
    """
    return {"_stub": True, "path": ""}
