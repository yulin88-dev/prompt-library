"""MCP tool stubs for prompt CRUD + search. Real logic lands in Prompt 4."""
from __future__ import annotations


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
        body: The prompt text itself.
        tags: List of tag strings (will be normalized).
        category: Optional category label.
        notes: Optional notes about when/how to use this prompt.

    Returns:
        Prompt dict with id, title, body, tags, category, notes, timestamps.
    """
    return {
        "_stub": True,
        "id": 0,
        "title": title,
        "body": body,
        "tags": tags or [],
        "category": category,
        "notes": notes,
    }


def update_prompt(
    id: int,
    title: str | None = None,
    body: str | None = None,
    tags: list[str] | None = None,
    category: str | None = None,
    notes: str | None = None,
) -> dict:
    """Partially update a prompt. Only non-None fields are applied."""
    return {
        "_stub": True,
        "id": id,
        "updated_fields": {
            k: v
            for k, v in {
                "title": title,
                "body": body,
                "tags": tags,
                "category": category,
                "notes": notes,
            }.items()
            if v is not None
        },
    }


def list_prompts(
    category: str | None = None,
    tags: list[str] | None = None,
    limit: int = 50,
) -> dict:
    """List prompts, optionally filtered by category and tags."""
    return {
        "_stub": True,
        "prompts": [],
        "count": 0,
        "filter": {"category": category, "tags": tags or [], "limit": limit},
    }


def get_prompt(id: int | str) -> dict:
    """Look up a prompt by numeric id or title (case-insensitive)."""
    return {"_stub": True, "id": id}


def delete_prompt(id: int, confirm: bool = False) -> dict:
    """Hard-delete a prompt. Requires confirm=True."""
    if not confirm:
        return {
            "error": "delete_prompt requires confirm=True to proceed",
            "id": id,
        }
    return {"_stub": True, "deleted": True, "id": id}


def search_prompts(query: str, limit: int = 20) -> dict:
    """Full-text-ranked search across title, body, category, and notes.

    Args:
        query: Search string (FTS5 syntax supported in v1+).
        limit: Max results to return.

    Returns:
        Dict with `hits`: list of {prompt, snippet, rank}.
    """
    return {"_stub": True, "query": query, "limit": limit, "hits": []}
