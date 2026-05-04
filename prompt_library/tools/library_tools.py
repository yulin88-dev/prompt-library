"""MCP tools for tag summaries, export/import, and backup."""
from __future__ import annotations

import logging

from prompt_library.storage import io as storage_io
from prompt_library.storage.connection import get_library

log = logging.getLogger(__name__)


def _error(msg: str, **extra) -> dict:
    return {"error": msg, **extra}


def tag_summary() -> dict:
    """Counts of items per tag across projects and prompts.

    Returns:
        Dict with by_tag (tag → {projects, prompts}), untagged counts,
        and a list of near_duplicates (tags whose alphanumeric-canonical
        forms collide — useful for spotting accidental variants).
    """
    try:
        return get_library().tag_summary()
    except Exception as e:
        log.exception("tag_summary failed")
        return _error(str(e))


def export_library(
    kind: str = "all",
    format: str = "markdown",
    dest: str | None = None,
) -> dict:
    """Export projects, prompts, or both to markdown or JSON.

    Args:
        kind: One of 'projects', 'prompts', 'all'.
        format: One of 'markdown', 'json'.
        dest: Optional output directory (markdown) or file path (json).

    Returns:
        Dict with kind, format, dest, paths (list of files written), counts.
    """
    try:
        return storage_io.export_library(get_library(), kind, format, dest)
    except Exception as e:
        log.exception("export_library failed")
        return _error(str(e))


def import_library(path: str, overwrite: bool = False) -> dict:
    """Import a previously exported markdown tree or JSON file.

    Args:
        path: Path to the export root or .json file.
        overwrite: If True, conflicts overwrite existing items;
            otherwise conflicts are skipped (counted in `skipped`).

    Returns:
        Dict with source, format, imported, skipped, errors.
    """
    try:
        return storage_io.import_library(get_library(), path, overwrite)
    except Exception as e:
        log.exception("import_library failed")
        return _error(str(e))


def backup_library() -> dict:
    """Stub for Prompt 6 — copies the SQLite file to ./backups/."""
    return {"_stub": True, "path": ""}
