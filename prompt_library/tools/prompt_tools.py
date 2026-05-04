"""MCP tools for prompt CRUD + FTS5-ranked search.

Thin wrappers over `Library`. Library raises typed exceptions
(NotFoundError, DuplicateError, ValidationError); these wrappers translate
them into structured `{"error": ..., ...}` dicts so the MCP boundary
never raises.
"""
from __future__ import annotations

import logging

from prompt_library.storage.connection import get_library
from prompt_library.storage.library import (
    DuplicateError,
    LibraryError,
    NotFoundError,
    ValidationError,
)

log = logging.getLogger(__name__)


def _error(msg: str, **extra) -> dict:
    return {"error": msg, **extra}


def _handle(fn, **id_context):
    try:
        return fn()
    except (ValidationError, DuplicateError, NotFoundError, LibraryError) as e:
        return _error(str(e), **id_context)
    except Exception as e:
        log.exception("unexpected error")
        return _error(str(e), **id_context)


def add_prompt(
    title: str,
    body: str,
    tags: list[str] | None = None,
    category: str | None = None,
    notes: str | None = None,
) -> dict:
    """Create a new reusable prompt.

    Args:
        title: Unique prompt title.
        body: The prompt text itself (trailing whitespace trimmed on save).
        tags: List of tag strings (will be normalized: trimmed, lowercased, deduped).
        category: Optional category label.
        notes: Optional notes about when/how to use this prompt.
    """
    return _handle(
        lambda: get_library().add_prompt(
            title=title,
            body=body,
            tags=tags,
            category=category,
            notes=notes,
        ),
        title=title,
    )


def update_prompt(
    id: int,
    title: str | None = None,
    body: str | None = None,
    tags: list[str] | None = None,
    category: str | None = None,
    notes: str | None = None,
) -> dict:
    """Partially update a prompt. Only non-None fields are applied."""
    return _handle(
        lambda: get_library().update_prompt(
            id=id,
            title=title,
            body=body,
            tags=tags,
            category=category,
            notes=notes,
        ),
        id=id,
    )


def list_prompts(
    category: str | None = None,
    tags: list[str] | None = None,
    limit: int = 50,
) -> dict:
    """List prompts, optionally filtered by category and (all of) tags."""
    try:
        rows = get_library().list_prompts(category=category, tags=tags, limit=limit)
        return {"prompts": rows, "count": len(rows)}
    except (ValidationError, LibraryError) as e:
        return _error(str(e))


def get_prompt(id: int | str) -> dict:
    """Look up a prompt by numeric id or title (case-insensitive)."""
    return _handle(lambda: get_library().get_prompt(id), id=id)


def delete_prompt(id: int, confirm: bool = False) -> dict:
    """Hard-delete a prompt. Requires confirm=True."""
    if not confirm:
        return _error("delete_prompt requires confirm=True to proceed", id=id)

    def _do():
        deleted = get_library().delete_prompt(id)
        return {"deleted": True, "id": id, "prompt": deleted}

    return _handle(_do, id=id)


def search_prompts(query: str, limit: int = 20) -> dict:
    """FTS5-ranked search across title, body, category, and notes.

    Args:
        query: Search string. Whitespace-separated terms are matched as phrases;
            FTS5 operators are not exposed (each term is quoted internally).
        limit: Max results to return.

    Returns:
        Dict with `query`, `count`, and `hits`: list of {prompt, snippet, rank}.
        Lower rank values indicate better matches (BM25 convention).
    """
    try:
        hits = get_library().search_prompts(query=query, limit=limit)
        return {"query": query, "count": len(hits), "hits": hits}
    except (ValidationError, LibraryError) as e:
        return _error(str(e), query=query)
