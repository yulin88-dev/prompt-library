"""Library — SQLite-backed CRUD for projects and prompts.

The Library class is the public Python API. The MCP server is a thin facade
over it (so the same code path is exercised whether invoked from Claude
Desktop via stdio or from the Anthropic SDK via direct import).
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prompt_library.config import LIBRARY_PATH
from prompt_library.storage.migrations import migrate

log = logging.getLogger(__name__)

VALID_STATUSES = frozenset({"active", "paused", "archived", "done"})


class LibraryError(Exception):
    """Base class for typed library errors."""


class NotFoundError(LibraryError):
    pass


class DuplicateError(LibraryError):
    pass


class ValidationError(LibraryError):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_tags(tags: list[str] | None) -> list[str]:
    """Lowercase, trim, deduplicate while preserving first-seen order."""
    if not tags:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for t in tags:
        if not isinstance(t, str):
            raise ValidationError(f"tags must be strings; got {type(t).__name__}")
        norm = t.strip().lower()
        if norm and norm not in seen:
            seen.add(norm)
            result.append(norm)
    return result


class Library:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path).expanduser() if path else LIBRARY_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        migrate(self.conn)
        log.info("Library opened at %s", self.path)

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "Library":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------ #
    # Projects                                                           #
    # ------------------------------------------------------------------ #

    def add_project(
        self,
        name: str,
        description: str | None = None,
        status: str = "active",
        tags: list[str] | None = None,
        links: dict[str, str] | None = None,
    ) -> dict:
        name = (name or "").strip()
        if not name:
            raise ValidationError("name is required")
        if status not in VALID_STATUSES:
            raise ValidationError(
                f"invalid status {status!r}; must be one of {sorted(VALID_STATUSES)}"
            )
        norm_tags = _normalize_tags(tags)
        links_json = json.dumps(links or {})
        now = _now_iso()

        try:
            with self.conn:
                cur = self.conn.execute(
                    "INSERT INTO projects (name, description, status, links, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (name, description, status, links_json, now, now),
                )
                project_id = cur.lastrowid
                self._set_project_tags(project_id, norm_tags)
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint" in str(e):
                raise DuplicateError(f"project name {name!r} already exists") from e
            raise

        return self.get_project(project_id)

    def update_project(
        self,
        id: int,
        name: str | None = None,
        description: str | None = None,
        status: str | None = None,
        tags: list[str] | None = None,
        links: dict[str, str] | None = None,
    ) -> dict:
        # Verify exists; raises NotFoundError if not.
        self.get_project(id)

        if status is not None and status not in VALID_STATUSES:
            raise ValidationError(
                f"invalid status {status!r}; must be one of {sorted(VALID_STATUSES)}"
            )
        if name is not None:
            name = name.strip()
            if not name:
                raise ValidationError("name cannot be empty")

        sets: list[str] = []
        params: list[Any] = []
        if name is not None:
            sets.append("name = ?")
            params.append(name)
        if description is not None:
            sets.append("description = ?")
            params.append(description)
        if status is not None:
            sets.append("status = ?")
            params.append(status)
        if links is not None:
            sets.append("links = ?")
            params.append(json.dumps(links))

        try:
            with self.conn:
                if sets:
                    sets.append("updated_at = ?")
                    params.append(_now_iso())
                    params.append(id)
                    self.conn.execute(
                        f"UPDATE projects SET {', '.join(sets)} WHERE id = ?",
                        params,
                    )
                if tags is not None:
                    self._set_project_tags(id, _normalize_tags(tags))
                # Ensure updated_at moves even if only tags changed.
                if not sets and tags is not None:
                    self.conn.execute(
                        "UPDATE projects SET updated_at = ? WHERE id = ?",
                        (_now_iso(), id),
                    )
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint" in str(e):
                raise DuplicateError(f"project name {name!r} already exists") from e
            raise

        return self.get_project(id)

    def list_projects(
        self,
        status: str | None = None,
        tags: list[str] | None = None,
        limit: int = 50,
    ) -> list[dict]:
        if status is not None and status not in VALID_STATUSES:
            raise ValidationError(
                f"invalid status {status!r}; must be one of {sorted(VALID_STATUSES)}"
            )
        norm_tags = _normalize_tags(tags)

        sql = "SELECT p.* FROM projects p"
        params: list[Any] = []
        wheres: list[str] = []

        if norm_tags:
            placeholders = ",".join("?" * len(norm_tags))
            wheres.append(
                f"p.id IN (SELECT pt.project_id FROM project_tags pt "
                f"JOIN tags t ON t.id = pt.tag_id "
                f"WHERE t.name IN ({placeholders}) "
                f"GROUP BY pt.project_id "
                f"HAVING COUNT(DISTINCT t.name) = {len(norm_tags)})"
            )
            params.extend(norm_tags)
        if status:
            wheres.append("p.status = ?")
            params.append(status)
        if wheres:
            sql += " WHERE " + " AND ".join(wheres)
        sql += " ORDER BY p.updated_at DESC LIMIT ?"
        params.append(limit)

        rows = self.conn.execute(sql, params).fetchall()
        return self._rows_to_projects(rows)

    def get_project(self, id_or_name: int | str) -> dict:
        if isinstance(id_or_name, int):
            row = self.conn.execute(
                "SELECT * FROM projects WHERE id = ?", (id_or_name,)
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT * FROM projects WHERE LOWER(name) = LOWER(?)", (id_or_name,)
            ).fetchone()
        if not row:
            raise NotFoundError(f"project not found: {id_or_name!r}")
        return self._rows_to_projects([row])[0]

    def archive_project(self, id: int) -> dict:
        return self.update_project(id, status="archived")

    def delete_project(self, id: int) -> dict:
        existing = self.get_project(id)  # raises NotFoundError if missing
        with self.conn:
            self.conn.execute("DELETE FROM projects WHERE id = ?", (id,))
        return existing

    # ------------------------------------------------------------------ #
    # Internal helpers                                                   #
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    # Prompts                                                            #
    # ------------------------------------------------------------------ #

    def add_prompt(
        self,
        title: str,
        body: str,
        tags: list[str] | None = None,
        category: str | None = None,
        notes: str | None = None,
    ) -> dict:
        title = (title or "").strip()
        if not title:
            raise ValidationError("title is required")
        body = (body or "").rstrip()
        if not body:
            raise ValidationError("body is required and cannot be empty")

        norm_tags = _normalize_tags(tags)
        now = _now_iso()

        try:
            with self.conn:
                cur = self.conn.execute(
                    "INSERT INTO prompts (title, body, category, notes, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (title, body, category, notes, now, now),
                )
                prompt_id = cur.lastrowid
                self._set_prompt_tags(prompt_id, norm_tags)
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint" in str(e):
                raise DuplicateError(f"prompt title {title!r} already exists") from e
            raise

        return self.get_prompt(prompt_id)

    def update_prompt(
        self,
        id: int,
        title: str | None = None,
        body: str | None = None,
        tags: list[str] | None = None,
        category: str | None = None,
        notes: str | None = None,
    ) -> dict:
        self.get_prompt(id)  # raises NotFoundError if missing

        if title is not None:
            title = title.strip()
            if not title:
                raise ValidationError("title cannot be empty")
        if body is not None:
            body = body.rstrip()
            if not body:
                raise ValidationError("body cannot be empty")

        sets: list[str] = []
        params: list[Any] = []
        if title is not None:
            sets.append("title = ?")
            params.append(title)
        if body is not None:
            sets.append("body = ?")
            params.append(body)
        if category is not None:
            sets.append("category = ?")
            params.append(category)
        if notes is not None:
            sets.append("notes = ?")
            params.append(notes)

        try:
            with self.conn:
                if sets:
                    sets.append("updated_at = ?")
                    params.append(_now_iso())
                    params.append(id)
                    self.conn.execute(
                        f"UPDATE prompts SET {', '.join(sets)} WHERE id = ?",
                        params,
                    )
                if tags is not None:
                    self._set_prompt_tags(id, _normalize_tags(tags))
                if not sets and tags is not None:
                    self.conn.execute(
                        "UPDATE prompts SET updated_at = ? WHERE id = ?",
                        (_now_iso(), id),
                    )
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint" in str(e):
                raise DuplicateError(f"prompt title {title!r} already exists") from e
            raise

        return self.get_prompt(id)

    def list_prompts(
        self,
        category: str | None = None,
        tags: list[str] | None = None,
        limit: int = 50,
    ) -> list[dict]:
        norm_tags = _normalize_tags(tags)

        sql = "SELECT p.* FROM prompts p"
        params: list[Any] = []
        wheres: list[str] = []

        if norm_tags:
            placeholders = ",".join("?" * len(norm_tags))
            wheres.append(
                f"p.id IN (SELECT pt.prompt_id FROM prompt_tags pt "
                f"JOIN tags t ON t.id = pt.tag_id "
                f"WHERE t.name IN ({placeholders}) "
                f"GROUP BY pt.prompt_id "
                f"HAVING COUNT(DISTINCT t.name) = {len(norm_tags)})"
            )
            params.extend(norm_tags)
        if category:
            wheres.append("p.category = ?")
            params.append(category)
        if wheres:
            sql += " WHERE " + " AND ".join(wheres)
        sql += " ORDER BY p.updated_at DESC LIMIT ?"
        params.append(limit)

        rows = self.conn.execute(sql, params).fetchall()
        return self._rows_to_prompts(rows)

    def get_prompt(self, id_or_title: int | str) -> dict:
        if isinstance(id_or_title, int):
            row = self.conn.execute(
                "SELECT * FROM prompts WHERE id = ?", (id_or_title,)
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT * FROM prompts WHERE LOWER(title) = LOWER(?)", (id_or_title,)
            ).fetchone()
        if not row:
            raise NotFoundError(f"prompt not found: {id_or_title!r}")
        return self._rows_to_prompts([row])[0]

    def delete_prompt(self, id: int) -> dict:
        existing = self.get_prompt(id)  # raises NotFoundError if missing
        with self.conn:
            self.conn.execute("DELETE FROM prompts WHERE id = ?", (id,))
        return existing

    def search_prompts(self, query: str, limit: int = 20) -> list[dict]:
        """FTS5-ranked search across title, body, category, notes.

        For tag-only filtering, use list_prompts(tags=[...]) instead.
        """
        query = (query or "").strip()
        if not query:
            return []

        # Quote each whitespace-delimited term to neutralize FTS5 operators
        # (AND, OR, NEAR, NOT, parens, etc.). Doubled embedded double-quotes
        # to escape per FTS5 syntax.
        terms = query.split()
        if not terms:
            return []
        fts_query = " ".join('"' + t.replace('"', '""') + '"' for t in terms)

        sql = """
            SELECT p.id,
                   snippet(prompts_fts, -1, '[', ']', '...', 30) AS snip,
                   bm25(prompts_fts) AS rank
            FROM prompts p
            JOIN prompts_fts ON prompts_fts.rowid = p.id
            WHERE prompts_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """
        try:
            rows = self.conn.execute(sql, (fts_query, limit)).fetchall()
        except sqlite3.OperationalError as e:
            raise ValidationError(f"invalid search query: {e}") from e

        if not rows:
            return []

        ids = [r["id"] for r in rows]
        prompts = self._get_prompts_by_ids(ids)
        prompts_by_id = {p["id"]: p for p in prompts}

        return [
            {
                "prompt": prompts_by_id[r["id"]],
                "snippet": r["snip"],
                "rank": float(r["rank"]),
            }
            for r in rows
            if r["id"] in prompts_by_id
        ]

    # ------------------------------------------------------------------ #
    # Internal helpers                                                   #
    # ------------------------------------------------------------------ #

    def _set_prompt_tags(self, prompt_id: int, tags: list[str]) -> None:
        for tag in tags:
            self.conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
        self.conn.execute(
            "DELETE FROM prompt_tags WHERE prompt_id = ?", (prompt_id,)
        )
        for tag in tags:
            self.conn.execute(
                "INSERT INTO prompt_tags (prompt_id, tag_id) "
                "SELECT ?, id FROM tags WHERE name = ?",
                (prompt_id, tag),
            )

    def _get_prompts_by_ids(self, ids: list[int]) -> list[dict]:
        if not ids:
            return []
        placeholders = ",".join("?" * len(ids))
        rows = self.conn.execute(
            f"SELECT * FROM prompts WHERE id IN ({placeholders})", ids
        ).fetchall()
        return self._rows_to_prompts(rows)

    def _rows_to_prompts(self, rows: list[sqlite3.Row]) -> list[dict]:
        if not rows:
            return []
        ids = [r["id"] for r in rows]
        placeholders = ",".join("?" * len(ids))
        tag_rows = self.conn.execute(
            f"SELECT pt.prompt_id, t.name FROM prompt_tags pt "
            f"JOIN tags t ON t.id = pt.tag_id "
            f"WHERE pt.prompt_id IN ({placeholders}) ORDER BY t.name",
            ids,
        ).fetchall()
        tags_by_id: dict[int, list[str]] = {}
        for tr in tag_rows:
            tags_by_id.setdefault(tr["prompt_id"], []).append(tr["name"])
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "body": r["body"],
                "category": r["category"],
                "notes": r["notes"],
                "tags": tags_by_id.get(r["id"], []),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]

    # ------------------------------------------------------------------ #

    def _set_project_tags(self, project_id: int, tags: list[str]) -> None:
        for tag in tags:
            self.conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
        self.conn.execute(
            "DELETE FROM project_tags WHERE project_id = ?", (project_id,)
        )
        for tag in tags:
            self.conn.execute(
                "INSERT INTO project_tags (project_id, tag_id) "
                "SELECT ?, id FROM tags WHERE name = ?",
                (project_id, tag),
            )

    def _rows_to_projects(self, rows: list[sqlite3.Row]) -> list[dict]:
        if not rows:
            return []
        ids = [r["id"] for r in rows]
        placeholders = ",".join("?" * len(ids))
        tag_rows = self.conn.execute(
            f"SELECT pt.project_id, t.name FROM project_tags pt "
            f"JOIN tags t ON t.id = pt.tag_id "
            f"WHERE pt.project_id IN ({placeholders}) ORDER BY t.name",
            ids,
        ).fetchall()
        tags_by_id: dict[int, list[str]] = {}
        for tr in tag_rows:
            tags_by_id.setdefault(tr["project_id"], []).append(tr["name"])
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "status": r["status"],
                "tags": tags_by_id.get(r["id"], []),
                "links": json.loads(r["links"]) if r["links"] else {},
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]
