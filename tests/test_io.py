"""Unit tests for tag_summary + export/import (markdown and JSON)."""
from __future__ import annotations

from pathlib import Path

import pytest

from prompt_library.storage import io as storage_io
from prompt_library.storage.connection import set_library
from prompt_library.storage.library import Library
from prompt_library.tools import library_tools


@pytest.fixture
def lib_in_tools(library: Library):
    set_library(library)
    yield library
    set_library(None)


# --------------------------------------------------------------------- #
# tag_summary                                                           #
# --------------------------------------------------------------------- #


class TestTagSummary:
    def test_empty_library(self, library):
        s = library.tag_summary()
        assert s["by_tag"] == {}
        assert s["untagged"] == {"projects": 0, "prompts": 0}
        assert s["near_duplicates"] == []

    def test_counts_across_kinds(self, library):
        library.add_project(name="p1", tags=["python", "mcp"])
        library.add_project(name="p2", tags=["python"])
        library.add_prompt(title="t1", body="x", tags=["python", "ai"])
        s = library.tag_summary()
        assert s["by_tag"]["python"] == {"projects": 2, "prompts": 1}
        assert s["by_tag"]["mcp"] == {"projects": 1, "prompts": 0}
        assert s["by_tag"]["ai"] == {"projects": 0, "prompts": 1}

    def test_untagged_counts(self, library):
        library.add_project(name="p1")
        library.add_project(name="p2", tags=["x"])
        library.add_prompt(title="t1", body="x")
        library.add_prompt(title="t2", body="x", tags=["x"])
        s = library.tag_summary()
        assert s["untagged"] == {"projects": 1, "prompts": 1}

    def test_near_duplicate_detection(self, library):
        # Punctuation-only variants of the same canonical form.
        library.add_project(name="p1", tags=["machine-learning", "machine_learning"])
        library.add_prompt(title="t1", body="x", tags=["machinelearning"])
        s = library.tag_summary()
        # All three collapse to "machinelearning" canonically
        assert any(
            sorted(group) == ["machine-learning", "machine_learning", "machinelearning"]
            for group in s["near_duplicates"]
        )


# --------------------------------------------------------------------- #
# Markdown render / parse                                               #
# --------------------------------------------------------------------- #


class TestMarkdownFormat:
    def test_round_trip_frontmatter(self):
        fm = {"id": 1, "name": "p1", "tags": ["a", "b"]}
        body = "Some description"
        rendered = storage_io._render_md(fm, body)
        parsed_fm, parsed_body = storage_io._parse_md(rendered)
        assert parsed_fm == fm
        assert parsed_body == body

    def test_parse_rejects_missing_frontmatter(self):
        with pytest.raises(ValueError):
            storage_io._parse_md("just a markdown body")

    def test_slugify(self):
        assert storage_io._slugify("Hello World") == "hello-world"
        assert storage_io._slugify("Brk-B / Tesla!") == "brk-b-tesla"
        assert storage_io._slugify("") == "unnamed"
        assert storage_io._slugify("___") == "unnamed"


# --------------------------------------------------------------------- #
# Export                                                                #
# --------------------------------------------------------------------- #


class TestExport:
    def test_markdown_export_all(self, library, tmp_path):
        library.add_project(
            name="trading-bot",
            description="Buy TSLA",
            tags=["python", "mcp"],
            links={"github": "https://example.com"},
        )
        library.add_prompt(
            title="Code Review",
            body="Review this PR...",
            tags=["dev"],
            category="dev",
        )
        result = storage_io.export_library(library, "all", "markdown", tmp_path)
        assert result["counts"] == {"projects": 1, "prompts": 1}
        assert (tmp_path / "projects" / "trading-bot.md").exists()
        assert (tmp_path / "prompts" / "code-review.md").exists()

    def test_json_export_all(self, library, tmp_path):
        library.add_project(name="p1", tags=["a"])
        library.add_prompt(title="t1", body="b", tags=["x"])
        target = tmp_path / "library.json"
        result = storage_io.export_library(library, "all", "json", target)
        assert target.exists()
        assert result["counts"] == {"projects": 1, "prompts": 1}

    def test_invalid_kind_returns_error(self, library, tmp_path):
        result = storage_io.export_library(library, "robots", "json", tmp_path)
        assert "error" in result

    def test_invalid_format_returns_error(self, library, tmp_path):
        result = storage_io.export_library(library, "all", "yaml", tmp_path)
        assert "error" in result

    def test_export_only_prompts(self, library, tmp_path):
        library.add_project(name="p1")
        library.add_prompt(title="t1", body="b")
        result = storage_io.export_library(library, "prompts", "markdown", tmp_path)
        assert result["counts"] == {"projects": 0, "prompts": 1}
        assert not (tmp_path / "projects").exists()
        assert (tmp_path / "prompts" / "t1.md").exists()


# --------------------------------------------------------------------- #
# Round-trip: seed → export → wipe → import → assert state matches      #
# --------------------------------------------------------------------- #


def _wipe(library: Library) -> None:
    """Remove every project + prompt + tag relation from the library."""
    library.conn.execute("DELETE FROM projects")
    library.conn.execute("DELETE FROM prompts")
    library.conn.execute("DELETE FROM tags")
    library.conn.commit()


def _by_name(items: list[dict], key: str) -> dict[str, dict]:
    return {item[key]: item for item in items}


class TestRoundTrip:
    def test_json_round_trip(self, library, tmp_path):
        library.add_project(
            name="trading-bot",
            description="Buy TSLA",
            tags=["python", "mcp"],
            links={"gh": "https://example.com"},
            status="active",
        )
        library.add_project(name="defunct", status="archived")
        library.add_prompt(
            title="Code Review",
            body="Review the PR thoroughly",
            tags=["dev", "review"],
            category="dev",
            notes="Use after submission",
        )
        library.add_prompt(title="One-Liner", body="give me a one-liner")

        before_projects = _by_name(library.list_projects(limit=100), "name")
        before_prompts = _by_name(library.list_prompts(limit=100), "title")

        target = tmp_path / "library.json"
        storage_io.export_library(library, "all", "json", target)

        _wipe(library)
        assert library.list_projects() == []
        assert library.list_prompts() == []

        result = storage_io.import_library(library, target)
        assert result["imported"] == 4
        assert result["skipped"] == 0
        assert result["errors"] == []

        after_projects = _by_name(library.list_projects(limit=100), "name")
        after_prompts = _by_name(library.list_prompts(limit=100), "title")

        assert set(before_projects) == set(after_projects)
        assert set(before_prompts) == set(after_prompts)

        for name, before in before_projects.items():
            after = after_projects[name]
            assert before["description"] == after["description"]
            assert before["status"] == after["status"]
            assert sorted(before["tags"]) == sorted(after["tags"])
            assert before["links"] == after["links"]

        for title, before in before_prompts.items():
            after = after_prompts[title]
            assert before["body"] == after["body"]
            assert before["category"] == after["category"]
            assert before["notes"] == after["notes"]
            assert sorted(before["tags"]) == sorted(after["tags"])

    def test_markdown_round_trip(self, library, tmp_path):
        library.add_project(
            name="alpha",
            description="multi\nline\ndescription",
            tags=["x"],
        )
        library.add_prompt(
            title="Beta",
            body="multi\nline\nbody",
            tags=["y"],
            category="cat",
        )

        before_projects = _by_name(library.list_projects(), "name")
        before_prompts = _by_name(library.list_prompts(), "title")

        storage_io.export_library(library, "all", "markdown", tmp_path)
        _wipe(library)
        result = storage_io.import_library(library, tmp_path)
        assert result["imported"] == 2

        after_projects = _by_name(library.list_projects(), "name")
        after_prompts = _by_name(library.list_prompts(), "title")
        assert before_projects["alpha"]["description"] == after_projects["alpha"]["description"]
        assert before_prompts["Beta"]["body"] == after_prompts["Beta"]["body"]


# --------------------------------------------------------------------- #
# Import conflicts and overwrite                                        #
# --------------------------------------------------------------------- #


class TestImportConflicts:
    def test_conflict_skipped_without_overwrite(self, library, tmp_path):
        library.add_project(name="dup", description="original")
        target = tmp_path / "library.json"
        storage_io.export_library(library, "all", "json", target)

        # Modify the file to change the description
        import json

        payload = json.loads(target.read_text())
        payload["projects"][0]["description"] = "changed"
        target.write_text(json.dumps(payload))

        result = storage_io.import_library(library, target, overwrite=False)
        assert result["skipped"] == 1
        assert result["imported"] == 0
        # State unchanged
        assert library.get_project("dup")["description"] == "original"

    def test_conflict_overwritten(self, library, tmp_path):
        library.add_project(name="dup", description="original")
        target = tmp_path / "library.json"
        storage_io.export_library(library, "all", "json", target)

        import json

        payload = json.loads(target.read_text())
        payload["projects"][0]["description"] = "changed"
        target.write_text(json.dumps(payload))

        result = storage_io.import_library(library, target, overwrite=True)
        assert result["imported"] == 1
        assert library.get_project("dup")["description"] == "changed"

    def test_import_nonexistent_path(self, library):
        result = storage_io.import_library(library, "/no/such/path")
        assert "error" in result


# --------------------------------------------------------------------- #
# Tool wrappers                                                         #
# --------------------------------------------------------------------- #


class TestLibraryToolWrappers:
    def test_tag_summary_via_tool(self, lib_in_tools):
        lib_in_tools.add_project(name="p1", tags=["python"])
        result = library_tools.tag_summary()
        assert result["by_tag"]["python"]["projects"] == 1

    def test_export_via_tool(self, lib_in_tools, tmp_path):
        lib_in_tools.add_project(name="p1")
        result = library_tools.export_library(
            kind="all", format="markdown", dest=str(tmp_path)
        )
        assert "error" not in result

    def test_import_via_tool(self, lib_in_tools, tmp_path):
        lib_in_tools.add_project(name="p1", description="hello")
        target = tmp_path / "library.json"
        library_tools.export_library(kind="all", format="json", dest=str(target))
        _wipe(lib_in_tools)
        result = library_tools.import_library(str(target))
        assert result["imported"] == 1


# --------------------------------------------------------------------- #
# Backup                                                                #
# --------------------------------------------------------------------- #


class TestBackup:
    def test_library_backup_to(self, library, tmp_path):
        library.add_project(name="p1")
        dest = tmp_path / "snapshot.db"
        path = library.backup_to(dest)
        assert path.exists()
        assert path.stat().st_size > 0

    def test_backup_is_independent_snapshot(self, library, tmp_path):
        library.add_project(name="before-backup")
        dest = tmp_path / "snap.db"
        library.backup_to(dest)
        # Mutate source after backup completes.
        library.add_project(name="after-backup")
        # The snapshot should still only contain the pre-backup state.
        snap = Library(dest)
        try:
            names = {p["name"] for p in snap.list_projects()}
        finally:
            snap.close()
        assert names == {"before-backup"}

    def test_backup_tool_writes_to_backups_dir(
        self, lib_in_tools, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(
            "prompt_library.tools.library_tools.BACKUPS_DIR", tmp_path
        )
        lib_in_tools.add_project(name="p1")
        result = library_tools.backup_library()
        assert "error" not in result
        path = Path(result["path"])
        assert path.exists()
        assert path.parent == tmp_path.resolve()
        assert path.name.startswith("library_") and path.name.endswith(".db")
        assert result["size_bytes"] > 0

    def test_backup_filename_uses_timestamp(
        self, lib_in_tools, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(
            "prompt_library.tools.library_tools.BACKUPS_DIR", tmp_path
        )
        result = library_tools.backup_library()
        # YYYY-MM-DD-HHMM → 15 chars (e.g. 2026-05-04-1230)
        assert len(result["timestamp"]) == 15
        assert result["timestamp"][4] == "-"
        assert result["timestamp"][7] == "-"
        assert result["timestamp"][10] == "-"
