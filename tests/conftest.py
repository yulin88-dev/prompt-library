"""Shared pytest fixtures: isolated SQLite library per test."""
from __future__ import annotations

from pathlib import Path

import pytest

from prompt_library.storage.library import Library


@pytest.fixture
def library(tmp_path: Path) -> Library:
    """A fresh Library backed by a temp DB; closed automatically after the test."""
    lib = Library(tmp_path / "test.db")
    yield lib
    lib.close()
