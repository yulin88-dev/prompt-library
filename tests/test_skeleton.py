"""Smoke tests for the skeleton: DB opens, migrations run, schema is correct."""
from __future__ import annotations


def test_library_opens_and_migrates(library):
    """The Library fixture should open the DB and apply schema v1."""
    row = library.conn.execute(
        "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
    ).fetchone()
    assert row is not None
    assert row[0] == 1


def test_expected_tables_exist(library):
    rows = library.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    names = {r[0] for r in rows}
    for expected in {
        "projects",
        "prompts",
        "tags",
        "project_tags",
        "prompt_tags",
        "schema_version",
    }:
        assert expected in names, f"missing table: {expected}"


def test_fts_table_exists(library):
    rows = library.conn.execute(
        "SELECT name FROM sqlite_master WHERE name='prompts_fts'"
    ).fetchall()
    assert rows, "prompts_fts virtual table missing"


def test_migrate_is_idempotent(library):
    """Calling migrate again should be a no-op."""
    from prompt_library.storage.migrations import migrate

    migrate(library.conn)
    migrate(library.conn)
    rows = library.conn.execute("SELECT version FROM schema_version").fetchall()
    assert len(rows) == 1


def test_stub_tools_return_dicts():
    from prompt_library.tools import library_tools, project_tools, prompt_tools

    assert isinstance(project_tools.add_project("p1"), dict)
    assert isinstance(prompt_tools.add_prompt("t1", "body"), dict)
    assert isinstance(library_tools.tag_summary(), dict)


def test_delete_requires_confirm():
    from prompt_library.tools import project_tools, prompt_tools

    assert "error" in project_tools.delete_project(1)
    assert "error" in prompt_tools.delete_prompt(1)
    assert project_tools.delete_project(1, confirm=True).get("deleted") is True
    assert prompt_tools.delete_prompt(1, confirm=True).get("deleted") is True
