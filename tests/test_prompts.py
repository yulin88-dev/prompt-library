"""Unit tests for prompt CRUD + FTS5 search — Library methods + tool wrappers."""
from __future__ import annotations

import pytest

from prompt_library.storage.connection import set_library
from prompt_library.storage.library import (
    DuplicateError,
    Library,
    NotFoundError,
    ValidationError,
)
from prompt_library.tools import prompt_tools


@pytest.fixture
def lib_in_tools(library: Library):
    set_library(library)
    yield library
    set_library(None)


# ============================================================ #
# Library — add / update / list / get / delete                 #
# ============================================================ #


class TestLibraryAddPrompt:
    def test_happy_path(self, library):
        p = library.add_prompt(title="code-review", body="Review PR #X for bugs")
        assert p["id"] > 0
        assert p["title"] == "code-review"
        assert p["body"] == "Review PR #X for bugs"
        assert p["tags"] == []
        assert p["created_at"] == p["updated_at"]

    def test_with_tags_and_category(self, library):
        p = library.add_prompt(
            title="t1",
            body="Body",
            tags=["  Python ", "PYTHON", "mcp"],
            category="dev",
            notes="note",
        )
        assert sorted(p["tags"]) == ["mcp", "python"]
        assert p["category"] == "dev"
        assert p["notes"] == "note"

    def test_blank_title_rejected(self, library):
        with pytest.raises(ValidationError):
            library.add_prompt(title="   ", body="x")

    def test_blank_body_rejected(self, library):
        with pytest.raises(ValidationError):
            library.add_prompt(title="t", body="")
        with pytest.raises(ValidationError):
            library.add_prompt(title="t", body="   \n\n")

    def test_trailing_whitespace_trimmed(self, library):
        p = library.add_prompt(title="t1", body="  body text  \n\n")
        # trailing whitespace removed; leading preserved
        assert p["body"] == "  body text"

    def test_duplicate_title_rejected(self, library):
        library.add_prompt(title="dup", body="x")
        with pytest.raises(DuplicateError):
            library.add_prompt(title="dup", body="y")


class TestLibraryUpdatePrompt:
    def test_partial_update(self, library):
        p = library.add_prompt(title="t1", body="old body")
        updated = library.update_prompt(p["id"], body="new body")
        assert updated["body"] == "new body"
        assert updated["title"] == "t1"
        assert updated["updated_at"] >= updated["created_at"]

    def test_replace_tags(self, library):
        p = library.add_prompt(title="t1", body="body", tags=["a", "b"])
        updated = library.update_prompt(p["id"], tags=["c"])
        assert updated["tags"] == ["c"]

    def test_blank_body_on_update_rejected(self, library):
        p = library.add_prompt(title="t1", body="body")
        with pytest.raises(ValidationError):
            library.update_prompt(p["id"], body="   ")

    def test_not_found(self, library):
        with pytest.raises(NotFoundError):
            library.update_prompt(9999, body="x")

    def test_duplicate_title_on_update_rejected(self, library):
        library.add_prompt(title="a", body="x")
        b = library.add_prompt(title="b", body="x")
        with pytest.raises(DuplicateError):
            library.update_prompt(b["id"], title="a")


class TestLibraryListPrompts:
    def test_list_all(self, library):
        library.add_prompt(title="t1", body="b1")
        library.add_prompt(title="t2", body="b2")
        rows = library.list_prompts()
        assert len(rows) == 2

    def test_filter_by_category(self, library):
        library.add_prompt(title="dev1", body="x", category="dev")
        library.add_prompt(title="ops1", body="x", category="ops")
        rows = library.list_prompts(category="ops")
        assert [r["title"] for r in rows] == ["ops1"]

    def test_filter_by_tags_AND_semantics(self, library):
        library.add_prompt(title="a", body="x", tags=["python", "mcp"])
        library.add_prompt(title="b", body="x", tags=["python"])
        library.add_prompt(title="c", body="x", tags=["mcp"])
        rows = library.list_prompts(tags=["python", "mcp"])
        assert [r["title"] for r in rows] == ["a"]


class TestLibraryGetPrompt:
    def test_by_id(self, library):
        p = library.add_prompt(title="t1", body="x")
        assert library.get_prompt(p["id"])["title"] == "t1"

    def test_by_title_case_insensitive(self, library):
        library.add_prompt(title="MyPrompt", body="x")
        assert library.get_prompt("myprompt")["title"] == "MyPrompt"

    def test_not_found(self, library):
        with pytest.raises(NotFoundError):
            library.get_prompt(9999)


class TestLibraryDeletePrompt:
    def test_delete_returns_record(self, library):
        p = library.add_prompt(title="t1", body="x", tags=["a"])
        deleted = library.delete_prompt(p["id"])
        assert deleted["title"] == "t1"
        with pytest.raises(NotFoundError):
            library.get_prompt(p["id"])

    def test_delete_cascades_tags(self, library):
        p = library.add_prompt(title="t1", body="x", tags=["a"])
        library.delete_prompt(p["id"])
        rows = library.conn.execute(
            "SELECT * FROM prompt_tags WHERE prompt_id = ?", (p["id"],)
        ).fetchall()
        assert rows == []

    def test_delete_not_found(self, library):
        with pytest.raises(NotFoundError):
            library.delete_prompt(9999)


# ============================================================ #
# FTS5 search                                                  #
# ============================================================ #


class TestLibrarySearchPrompts:
    def test_search_ranking(self, library):
        # Title+body match should outrank body-only match.
        library.add_prompt(title="MCP Server", body="A primer on MCP servers.")
        library.add_prompt(title="Random Notes", body="Nothing relevant.")
        library.add_prompt(title="Other", body="Briefly mentions MCP somewhere.")

        hits = library.search_prompts("MCP")
        titles = [h["prompt"]["title"] for h in hits]
        assert "MCP Server" in titles
        assert "Random Notes" not in titles
        assert titles[0] == "MCP Server"  # highest-ranked match
        # Lower (more negative) bm25 = better — confirm ordering.
        assert hits[0]["rank"] <= hits[-1]["rank"]

    def test_search_returns_snippet(self, library):
        library.add_prompt(
            title="t1",
            body="The quick brown fox jumps over the lazy dog every Tuesday.",
        )
        hits = library.search_prompts("fox")
        assert len(hits) == 1
        # FTS5 snippet should contain the highlighted match
        assert "[fox]" in hits[0]["snippet"]

    def test_search_multi_term(self, library):
        library.add_prompt(title="a", body="apple banana cherry")
        library.add_prompt(title="b", body="apple only")
        library.add_prompt(title="c", body="cherry only")
        hits = library.search_prompts("apple banana")
        # Both terms required → only "a" qualifies
        assert {h["prompt"]["title"] for h in hits} == {"a"}

    def test_search_empty_query(self, library):
        library.add_prompt(title="t1", body="body")
        assert library.search_prompts("") == []
        assert library.search_prompts("   ") == []

    def test_search_empty_corpus(self, library):
        assert library.search_prompts("anything") == []

    def test_search_no_matches(self, library):
        library.add_prompt(title="t1", body="apple banana")
        assert library.search_prompts("xyz") == []

    def test_search_special_characters_safe(self, library):
        # FTS5 operators inside the query should not crash; they get quoted.
        library.add_prompt(title="t1", body="contains AND OR NOT operators")
        # Should NOT raise even though AND/OR/NOT are FTS5 operators.
        hits = library.search_prompts("AND OR")
        assert isinstance(hits, list)

    def test_search_matches_category_and_notes(self, library):
        library.add_prompt(
            title="t1", body="generic body", category="dev", notes="bash scripting"
        )
        # match on category
        assert any(h["prompt"]["title"] == "t1" for h in library.search_prompts("dev"))
        # match on notes
        assert any(h["prompt"]["title"] == "t1" for h in library.search_prompts("bash"))

    def test_search_respects_limit(self, library):
        for i in range(10):
            library.add_prompt(title=f"p{i}", body=f"contains keyword {i}")
        hits = library.search_prompts("keyword", limit=3)
        assert len(hits) == 3


# ============================================================ #
# Tool-wrapper tests (exception → error-dict translation)      #
# ============================================================ #


class TestPromptToolsErrorTranslation:
    def test_add_returns_dict(self, lib_in_tools):
        result = prompt_tools.add_prompt("t1", "body", tags=["python"])
        assert "error" not in result
        assert result["title"] == "t1"

    def test_add_duplicate_returns_error(self, lib_in_tools):
        prompt_tools.add_prompt("dup", "x")
        result = prompt_tools.add_prompt("dup", "y")
        assert "error" in result
        assert result["title"] == "dup"

    def test_add_blank_body_returns_error(self, lib_in_tools):
        result = prompt_tools.add_prompt("t1", "   ")
        assert "error" in result

    def test_get_not_found_returns_error(self, lib_in_tools):
        result = prompt_tools.get_prompt(9999)
        assert "error" in result

    def test_update_not_found_returns_error(self, lib_in_tools):
        result = prompt_tools.update_prompt(9999, body="x")
        assert "error" in result

    def test_delete_requires_confirm(self, lib_in_tools):
        result = prompt_tools.delete_prompt(1)
        assert "error" in result
        assert "confirm=True" in result["error"]

    def test_delete_with_confirm_works(self, lib_in_tools):
        added = prompt_tools.add_prompt("t1", "body")
        result = prompt_tools.delete_prompt(added["id"], confirm=True)
        assert result.get("deleted") is True

    def test_list_returns_count(self, lib_in_tools):
        prompt_tools.add_prompt("t1", "x")
        prompt_tools.add_prompt("t2", "y")
        result = prompt_tools.list_prompts()
        assert result["count"] == 2

    def test_search_via_tool(self, lib_in_tools):
        prompt_tools.add_prompt("MCP Guide", "All about MCP")
        prompt_tools.add_prompt("Other", "irrelevant")
        result = prompt_tools.search_prompts("MCP")
        assert result["query"] == "MCP"
        assert result["count"] == 1
        assert result["hits"][0]["prompt"]["title"] == "MCP Guide"

    def test_search_empty_query_via_tool(self, lib_in_tools):
        prompt_tools.add_prompt("t1", "body")
        result = prompt_tools.search_prompts("")
        assert result["count"] == 0
        assert result["hits"] == []
