"""MCP tool stubs for project CRUD. Real logic lands in Prompt 3."""
from __future__ import annotations


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
        tags: List of tag strings (will be normalized).
        links: Map of label → URL.

    Returns:
        Project dict with id, name, status, tags, links, timestamps.
    """
    return {
        "_stub": True,
        "id": 0,
        "name": name,
        "description": description,
        "status": status,
        "tags": tags or [],
        "links": links or {},
    }


def update_project(
    id: int,
    name: str | None = None,
    description: str | None = None,
    status: str | None = None,
    tags: list[str] | None = None,
    links: dict[str, str] | None = None,
) -> dict:
    """Partially update a project. Only non-None fields are applied."""
    return {
        "_stub": True,
        "id": id,
        "updated_fields": {
            k: v
            for k, v in {
                "name": name,
                "description": description,
                "status": status,
                "tags": tags,
                "links": links,
            }.items()
            if v is not None
        },
    }


def list_projects(
    status: str | None = None,
    tags: list[str] | None = None,
    limit: int = 50,
) -> dict:
    """List projects, optionally filtered by status and tags."""
    return {
        "_stub": True,
        "projects": [],
        "count": 0,
        "filter": {"status": status, "tags": tags or [], "limit": limit},
    }


def get_project(id: int | str) -> dict:
    """Look up a project by numeric id or name (case-insensitive)."""
    return {"_stub": True, "id": id}


def archive_project(id: int) -> dict:
    """Set a project's status to 'archived'."""
    return {"_stub": True, "id": id, "status": "archived"}


def delete_project(id: int, confirm: bool = False) -> dict:
    """Hard-delete a project. Requires confirm=True."""
    if not confirm:
        return {
            "error": "delete_project requires confirm=True to proceed",
            "id": id,
        }
    return {"_stub": True, "deleted": True, "id": id}
