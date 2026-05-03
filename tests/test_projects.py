"""Unit tests for project CRUD — Library methods + tool wrappers."""
from __future__ import annotations

import pytest

from prompt_library.storage.connection import set_library
from prompt_library.storage.library import (
    DuplicateError,
    Library,
    NotFoundError,
    ValidationError,
)
from prompt_library.tools import project_tools


@pytest.fixture
def lib_in_tools(library: Library):
    """Inject the test Library into the tools layer."""
    set_library(library)
    yield library
    set_library(None)


# ============================================================ #
# Library-level tests                                          #
# ============================================================ #


class TestLibraryAddProject:
    def test_happy_path(self, library):
        p = library.add_project(name="trading-bot", description="Trade TSLA", tags=["python", "MCP"])
        assert p["id"] > 0
        assert p["name"] == "trading-bot"
        assert p["description"] == "Trade TSLA"
        assert p["status"] == "active"
        assert p["tags"] == ["mcp", "python"]
        assert p["links"] == {}
        assert p["created_at"] == p["updated_at"]

    def test_tag_normalization(self, library):
        p = library.add_project(
            name="p1", tags=["  Python  ", "PYTHON", "Mcp", "mcp", "  "]
        )
        # trimmed + lowercased + deduplicated, empty discarded
        assert sorted(p["tags"]) == ["mcp", "python"]

    def test_links_preserved_as_dict(self, library):
        links = {"github": "https://github.com/x/y", "docs": "https://example.com"}
        p = library.add_project(name="p1", links=links)
        assert p["links"] == links

    def test_default_status_active(self, library):
        p = library.add_project(name="p1")
        assert p["status"] == "active"

    def test_blank_name_rejected(self, library):
        with pytest.raises(ValidationError):
            library.add_project(name="   ")

    def test_invalid_status_rejected(self, library):
        with pytest.raises(ValidationError):
            library.add_project(name="p1", status="frozen")

    def test_duplicate_name_rejected(self, library):
        library.add_project(name="dup")
        with pytest.raises(DuplicateError):
            library.add_project(name="dup")


class TestLibraryUpdateProject:
    def test_partial_update(self, library):
        p = library.add_project(name="p1", description="old")
        updated = library.update_project(p["id"], description="new")
        assert updated["description"] == "new"
        assert updated["name"] == "p1"  # untouched
        assert updated["updated_at"] >= updated["created_at"]

    def test_replace_tags(self, library):
        p = library.add_project(name="p1", tags=["a", "b"])
        updated = library.update_project(p["id"], tags=["c"])
        assert updated["tags"] == ["c"]

    def test_invalid_status_rejected(self, library):
        p = library.add_project(name="p1")
        with pytest.raises(ValidationError):
            library.update_project(p["id"], status="frozen")

    def test_not_found(self, library):
        with pytest.raises(NotFoundError):
            library.update_project(9999, description="x")

    def test_duplicate_name_on_update_rejected(self, library):
        library.add_project(name="a")
        b = library.add_project(name="b")
        with pytest.raises(DuplicateError):
            library.update_project(b["id"], name="a")


class TestLibraryListProjects:
    def test_list_all(self, library):
        library.add_project(name="p1")
        library.add_project(name="p2")
        rows = library.list_projects()
        assert len(rows) == 2

    def test_filter_by_status(self, library):
        library.add_project(name="active1", status="active")
        library.add_project(name="paused1", status="paused")
        rows = library.list_projects(status="paused")
        assert [r["name"] for r in rows] == ["paused1"]

    def test_filter_by_tags_AND_semantics(self, library):
        library.add_project(name="a", tags=["x", "y"])
        library.add_project(name="b", tags=["x"])
        library.add_project(name="c", tags=["y"])
        rows = library.list_projects(tags=["x", "y"])
        assert [r["name"] for r in rows] == ["a"]

    def test_invalid_status_filter_rejected(self, library):
        with pytest.raises(ValidationError):
            library.list_projects(status="frozen")


class TestLibraryGetProject:
    def test_by_id(self, library):
        p = library.add_project(name="p1")
        assert library.get_project(p["id"])["name"] == "p1"

    def test_by_name_case_insensitive(self, library):
        library.add_project(name="MyProject")
        assert library.get_project("myproject")["name"] == "MyProject"

    def test_not_found(self, library):
        with pytest.raises(NotFoundError):
            library.get_project(9999)


class TestLibraryArchiveAndDelete:
    def test_archive_sets_status(self, library):
        p = library.add_project(name="p1")
        archived = library.archive_project(p["id"])
        assert archived["status"] == "archived"

    def test_delete_returns_deleted_record(self, library):
        p = library.add_project(name="p1", tags=["x"])
        deleted = library.delete_project(p["id"])
        assert deleted["name"] == "p1"
        with pytest.raises(NotFoundError):
            library.get_project(p["id"])

    def test_delete_cascades_tags(self, library):
        p = library.add_project(name="p1", tags=["x"])
        library.delete_project(p["id"])
        rows = library.conn.execute(
            "SELECT * FROM project_tags WHERE project_id = ?", (p["id"],)
        ).fetchall()
        assert rows == []

    def test_delete_not_found(self, library):
        with pytest.raises(NotFoundError):
            library.delete_project(9999)


# ============================================================ #
# Tool-wrapper tests (exception → error-dict translation)      #
# ============================================================ #


class TestProjectToolsErrorTranslation:
    def test_add_returns_dict(self, lib_in_tools):
        result = project_tools.add_project("p1", tags=["python"])
        assert "error" not in result
        assert result["name"] == "p1"

    def test_add_duplicate_returns_error_dict(self, lib_in_tools):
        project_tools.add_project("dup")
        result = project_tools.add_project("dup")
        assert "error" in result
        assert "already exists" in result["error"]
        assert result["name"] == "dup"

    def test_add_invalid_status_returns_error(self, lib_in_tools):
        result = project_tools.add_project("p1", status="frozen")
        assert "error" in result
        assert "invalid status" in result["error"]

    def test_get_not_found_returns_error(self, lib_in_tools):
        result = project_tools.get_project(9999)
        assert "error" in result
        assert "not found" in result["error"]

    def test_update_not_found_returns_error(self, lib_in_tools):
        result = project_tools.update_project(9999, description="x")
        assert "error" in result

    def test_delete_requires_confirm(self, lib_in_tools):
        result = project_tools.delete_project(1)
        assert "error" in result
        assert "confirm=True" in result["error"]

    def test_delete_with_confirm_works(self, lib_in_tools):
        added = project_tools.add_project("p1")
        result = project_tools.delete_project(added["id"], confirm=True)
        assert result.get("deleted") is True

    def test_list_returns_count(self, lib_in_tools):
        project_tools.add_project("p1")
        project_tools.add_project("p2")
        result = project_tools.list_projects()
        assert result["count"] == 2
        assert len(result["projects"]) == 2

    def test_archive_via_tool(self, lib_in_tools):
        added = project_tools.add_project("p1")
        archived = project_tools.archive_project(added["id"])
        assert archived["status"] == "archived"
