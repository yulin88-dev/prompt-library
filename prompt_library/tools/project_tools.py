"""MCP tools for project CRUD.

Thin wrappers over `Library`. Library raises typed exceptions
(NotFoundError, DuplicateError, ValidationError); these wrappers translate
them into structured `{"error": ..., "id": ...}` dicts so the MCP boundary
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
    except (ValidationError, DuplicateError) as e:
        return _error(str(e), **id_context)
    except NotFoundError as e:
        return _error(str(e), **id_context)
    except LibraryError as e:
        return _error(str(e), **id_context)
    except Exception as e:
        log.exception("unexpected error")
        return _error(str(e), **id_context)


def add_project(
    name: str,
    description: str | None = None,
    status: str = "active",
    tags: list[str] | None = None,
    links: dict[str, str] | None = None,
) -> dict:
    """Create a new project.

    Args:
        name: Unique project name.
        description: Optional free-form description.
        status: One of active, paused, archived, done.
        tags: List of tag strings (will be normalized: trimmed, lowercased, deduped).
        links: Map of label → URL.
    """
    return _handle(
        lambda: get_library().add_project(
            name=name,
            description=description,
            status=status,
            tags=tags,
            links=links,
        ),
        name=name,
    )


def update_project(
    id: int,
    name: str | None = None,
    description: str | None = None,
    status: str | None = None,
    tags: list[str] | None = None,
    links: dict[str, str] | None = None,
) -> dict:
    """Partially update a project. Only non-None fields are applied."""
    return _handle(
        lambda: get_library().update_project(
            id=id,
            name=name,
            description=description,
            status=status,
            tags=tags,
            links=links,
        ),
        id=id,
    )


def list_projects(
    status: str | None = None,
    tags: list[str] | None = None,
    limit: int = 50,
) -> dict:
    """List projects, optionally filtered by status and (all of) tags."""
    try:
        rows = get_library().list_projects(status=status, tags=tags, limit=limit)
        return {"projects": rows, "count": len(rows)}
    except (ValidationError, LibraryError) as e:
        return _error(str(e))


def get_project(id: int | str) -> dict:
    """Look up a project by numeric id or name (case-insensitive)."""
    return _handle(lambda: get_library().get_project(id), id=id)


def archive_project(id: int) -> dict:
    """Set a project's status to 'archived'."""
    return _handle(lambda: get_library().archive_project(id), id=id)


def delete_project(id: int, confirm: bool = False) -> dict:
    """Hard-delete a project. Requires confirm=True."""
    if not confirm:
        return _error("delete_project requires confirm=True to proceed", id=id)

    def _do():
        deleted = get_library().delete_project(id)
        return {"deleted": True, "id": id, "project": deleted}

    return _handle(_do, id=id)
