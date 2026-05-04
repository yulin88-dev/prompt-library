"""Library import/export — markdown (with YAML frontmatter) and JSON.

Markdown layout: ./exports/projects/{slug}.md, ./exports/prompts/{slug}.md.
For projects, the markdown body is the project's `description`; for prompts,
it's the prompt's `body`. Frontmatter carries the rest.

JSON layout: a single file `library.json` with `{projects: [...], prompts: [...]}`.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from prompt_library.config import EXPORTS_DIR
from prompt_library.storage.library import (
    DuplicateError,
    Library,
    NotFoundError,
)

VALID_KINDS = ("projects", "prompts", "all")
VALID_FORMATS = ("markdown", "json")


def _slugify(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "unnamed"


def _project_to_md(project: dict) -> str:
    fm = {
        "id": project["id"],
        "name": project["name"],
        "status": project["status"],
        "tags": project["tags"],
        "links": project["links"],
        "created_at": project["created_at"],
        "updated_at": project["updated_at"],
    }
    body = project.get("description") or ""
    return _render_md(fm, body)


def _prompt_to_md(prompt: dict) -> str:
    fm = {
        "id": prompt["id"],
        "title": prompt["title"],
        "category": prompt.get("category"),
        "tags": prompt["tags"],
        "notes": prompt.get("notes"),
        "created_at": prompt["created_at"],
        "updated_at": prompt["updated_at"],
    }
    body = prompt["body"]
    return _render_md(fm, body)


def _render_md(frontmatter: dict, body: str) -> str:
    fm = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{fm}\n---\n\n{body.rstrip()}\n"


def _parse_md(text: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body_text). Raises ValueError on malformed input."""
    if not text.startswith("---"):
        raise ValueError("missing YAML frontmatter")
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        # Try alternate split for files without trailing newline at separator.
        parts = text.split("\n---", 1)
        if len(parts) != 2:
            raise ValueError("frontmatter not terminated")
        head, rest = parts[0], parts[1].lstrip("\n")
    else:
        head, rest = parts
    fm_str = head[len("---") :].lstrip("\n")
    fm = yaml.safe_load(fm_str) or {}
    if not isinstance(fm, dict):
        raise ValueError("frontmatter must be a mapping")
    return fm, rest.strip("\n")


# --------------------------------------------------------------------- #
# Export                                                                #
# --------------------------------------------------------------------- #


def export_library(
    library: Library,
    kind: str = "all",
    format: str = "markdown",
    dest: str | Path | None = None,
) -> dict:
    if kind not in VALID_KINDS:
        return {"error": f"invalid kind {kind!r}; must be one of {list(VALID_KINDS)}"}
    if format not in VALID_FORMATS:
        return {
            "error": f"invalid format {format!r}; must be one of {list(VALID_FORMATS)}"
        }

    base_dest = Path(dest).expanduser() if dest else EXPORTS_DIR
    # For markdown export base_dest is a directory; for json it can be either
    # a directory (we'll write library.json inside) or an explicit .json path.
    if format == "markdown" or base_dest.suffix != ".json":
        base_dest.mkdir(parents=True, exist_ok=True)
    else:
        base_dest.parent.mkdir(parents=True, exist_ok=True)

    paths: list[str] = []

    projects = library.list_projects(limit=10_000) if kind in ("projects", "all") else []
    prompts = library.list_prompts(limit=10_000) if kind in ("prompts", "all") else []

    if format == "markdown":
        if projects:
            proj_dir = base_dest / "projects"
            proj_dir.mkdir(parents=True, exist_ok=True)
            for p in projects:
                path = proj_dir / f"{_slugify(p['name'])}.md"
                path.write_text(_project_to_md(p), encoding="utf-8")
                paths.append(str(path.resolve()))
        if prompts:
            prompt_dir = base_dest / "prompts"
            prompt_dir.mkdir(parents=True, exist_ok=True)
            for p in prompts:
                path = prompt_dir / f"{_slugify(p['title'])}.md"
                path.write_text(_prompt_to_md(p), encoding="utf-8")
                paths.append(str(path.resolve()))
    else:  # json
        target = (
            base_dest
            if base_dest.suffix == ".json"
            else base_dest / "library.json"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        if kind in ("projects", "all"):
            payload["projects"] = projects
        if kind in ("prompts", "all"):
            payload["prompts"] = prompts
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        paths.append(str(target.resolve()))

    return {
        "kind": kind,
        "format": format,
        "dest": str(base_dest.resolve()),
        "paths": paths,
        "counts": {"projects": len(projects), "prompts": len(prompts)},
    }


# --------------------------------------------------------------------- #
# Import                                                                #
# --------------------------------------------------------------------- #


def import_library(
    library: Library,
    path: str | Path,
    overwrite: bool = False,
) -> dict:
    src = Path(path).expanduser()
    if not src.exists():
        return {"error": f"path does not exist: {src}"}

    if src.is_file() and src.suffix == ".json":
        return _import_json(library, src, overwrite)
    if src.is_dir():
        return _import_markdown(library, src, overwrite)
    return {"error": f"unsupported import source: {src} (need .json file or directory)"}


def _import_json(library: Library, path: Path, overwrite: bool) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {"error": f"invalid JSON: {e}"}

    imported = 0
    skipped = 0
    errors: list[str] = []

    for proj in payload.get("projects", []):
        result = _upsert_project(library, proj, overwrite)
        if result == "imported":
            imported += 1
        elif result == "skipped":
            skipped += 1
        else:
            errors.append(result)

    for prompt in payload.get("prompts", []):
        result = _upsert_prompt(library, prompt, overwrite)
        if result == "imported":
            imported += 1
        elif result == "skipped":
            skipped += 1
        else:
            errors.append(result)

    return {
        "source": str(path.resolve()),
        "format": "json",
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
    }


def _import_markdown(library: Library, root: Path, overwrite: bool) -> dict:
    imported = 0
    skipped = 0
    errors: list[str] = []

    proj_dir = root / "projects"
    if proj_dir.is_dir():
        for md in sorted(proj_dir.glob("*.md")):
            try:
                fm, body = _parse_md(md.read_text(encoding="utf-8"))
            except ValueError as e:
                errors.append(f"{md.name}: {e}")
                continue
            data = {
                "name": fm.get("name"),
                "description": body or None,
                "status": fm.get("status", "active"),
                "tags": fm.get("tags") or [],
                "links": fm.get("links") or {},
            }
            result = _upsert_project(library, data, overwrite)
            if result == "imported":
                imported += 1
            elif result == "skipped":
                skipped += 1
            else:
                errors.append(f"{md.name}: {result}")

    prompt_dir = root / "prompts"
    if prompt_dir.is_dir():
        for md in sorted(prompt_dir.glob("*.md")):
            try:
                fm, body = _parse_md(md.read_text(encoding="utf-8"))
            except ValueError as e:
                errors.append(f"{md.name}: {e}")
                continue
            data = {
                "title": fm.get("title"),
                "body": body,
                "tags": fm.get("tags") or [],
                "category": fm.get("category"),
                "notes": fm.get("notes"),
            }
            result = _upsert_prompt(library, data, overwrite)
            if result == "imported":
                imported += 1
            elif result == "skipped":
                skipped += 1
            else:
                errors.append(f"{md.name}: {result}")

    return {
        "source": str(root.resolve()),
        "format": "markdown",
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
    }


def _upsert_project(library: Library, data: dict, overwrite: bool) -> str:
    name = data.get("name")
    if not name:
        return "missing 'name'"
    try:
        existing = library.get_project(name)
    except NotFoundError:
        existing = None

    if existing is None:
        try:
            library.add_project(
                name=name,
                description=data.get("description"),
                status=data.get("status", "active"),
                tags=data.get("tags") or [],
                links=data.get("links") or {},
            )
            return "imported"
        except (DuplicateError, Exception) as e:
            return f"add failed for {name!r}: {e}"

    if not overwrite:
        return "skipped"

    try:
        library.update_project(
            existing["id"],
            name=name,
            description=data.get("description"),
            status=data.get("status"),
            tags=data.get("tags") or [],
            links=data.get("links") or {},
        )
        return "imported"
    except Exception as e:
        return f"update failed for {name!r}: {e}"


def _upsert_prompt(library: Library, data: dict, overwrite: bool) -> str:
    title = data.get("title")
    body = data.get("body")
    if not title:
        return "missing 'title'"
    if not body or not body.strip():
        return f"missing 'body' for {title!r}"
    try:
        existing = library.get_prompt(title)
    except NotFoundError:
        existing = None

    if existing is None:
        try:
            library.add_prompt(
                title=title,
                body=body,
                tags=data.get("tags") or [],
                category=data.get("category"),
                notes=data.get("notes"),
            )
            return "imported"
        except Exception as e:
            return f"add failed for {title!r}: {e}"

    if not overwrite:
        return "skipped"

    try:
        library.update_prompt(
            existing["id"],
            title=title,
            body=body,
            tags=data.get("tags") or [],
            category=data.get("category"),
            notes=data.get("notes"),
        )
        return "imported"
    except Exception as e:
        return f"update failed for {title!r}: {e}"
