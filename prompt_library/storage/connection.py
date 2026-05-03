"""Lazy-initialized shared Library instance for the tool layer.

The MCP tool wrappers reuse a single Library across calls. Tests can swap
in their own Library via `set_library(...)`.
"""
from __future__ import annotations

from prompt_library.storage.library import Library

_library: Library | None = None


def get_library() -> Library:
    global _library
    if _library is None:
        _library = Library()
    return _library


def set_library(library: Library | None) -> None:
    """Override the cached library — used by tests to inject a temp DB."""
    global _library
    if _library is not None and _library is not library:
        _library.close()
    _library = library
