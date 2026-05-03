# prompt-library-mcp

An MCP server that maintains a personal library of **projects** and
**reusable chat prompts**. Backed by SQLite + FTS5; reachable from Claude
Desktop or directly from the Anthropic SDK.

See [DESIGN.md](DESIGN.md) for the full design and
[MCP_SERVER_PROMPTS.md](MCP_SERVER_PROMPTS.md) for the prompts driving the
incremental build.

## Requirements

- Python 3.10+
- SQLite ≥ 3.9 (FTS5 support — bundled with macOS and standard Python builds)
- macOS for Claude Desktop integration (optional)

## Quickstart

```bash
make install         # installs the package + dev deps in editable mode
make test            # smoke tests (4 pass; CRUD tests come in later prompts)
make smoke           # opens a temp DB, runs migrations, calls a stub from each tool module
```

## Make targets

| Target | What it does |
|---|---|
| `make install` | `pip install -e ".[dev]"` |
| `make test` | Run pytest |
| `make smoke` | Open a temp DB, apply migrations, exercise stub tools |
| `make run` | Launch the MCP server over stdio (for debugging) |
| `make register-help` | Print a paste-ready Claude Desktop config block |
| `make clean` | Remove caches |

## Environment variables

Configured via a local `.env` file (gitignored). Copy from `.env.example`.

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `LIBRARY_PATH` | no | `~/.config/prompt-library/library.db` | Path to the SQLite library file |
| `LOG_LEVEL` | no | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

## Status

The skeleton is **scaffolded with stubs only** — every tool returns a
placeholder `{"_stub": True, ...}` payload. The DB opens and migrations
apply (verified by `make smoke` and `make test`). Real CRUD lands in
subsequent prompts:

- **Prompt 3**: project CRUD (add/update/list/get/archive/delete)
- **Prompt 4**: prompt CRUD + FTS5-ranked search
- **Prompt 5**: `tag_summary`, `export_library`, `import_library`
- **Prompt 6**: `backup_library` + Claude Desktop polish

## Registering with Claude Desktop

```bash
make register-help
```

Then merge the printed block into:
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

Quit Claude Desktop completely (Cmd+Q) and reopen — the **prompt-library**
tools will appear.

## Project layout

```
prompt-library/
├── DESIGN.md
├── MCP_SERVER_PROMPTS.md
├── Makefile
├── pyproject.toml
├── claude_desktop_config.example.json
├── .env.example
├── exports/                         # gitignored
├── backups/                         # gitignored
├── scripts/
│   ├── print_claude_config.py
│   └── smoke_test.py
├── tests/
│   ├── conftest.py
│   └── test_skeleton.py
└── prompt_library/
    ├── server.py                    # entry point (stdio)
    ├── config.py                    # env vars + paths
    ├── logging_setup.py             # stderr logging + log_tool decorator
    ├── storage/
    │   ├── library.py               # Library class — public Python API
    │   ├── schema.sql               # DDL
    │   ├── migrations.py            # version-tracked schema upgrades
    │   └── models.py                # TypedDicts
    └── tools/
        ├── project_tools.py         # 6 project tools (stubs)
        ├── prompt_tools.py          # 6 prompt tools (stubs)
        └── library_tools.py         # 4 library helpers (stubs)
```
