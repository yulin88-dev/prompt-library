"""Typed dicts for storage-layer return shapes."""
from __future__ import annotations

from typing import TypedDict


class Project(TypedDict):
    id: int
    name: str
    description: str | None
    status: str
    tags: list[str]
    links: dict[str, str]
    created_at: str
    updated_at: str


class Prompt(TypedDict):
    id: int
    title: str
    body: str
    category: str | None
    notes: str | None
    tags: list[str]
    created_at: str
    updated_at: str


class SearchHit(TypedDict):
    prompt: Prompt
    snippet: str
    rank: float
