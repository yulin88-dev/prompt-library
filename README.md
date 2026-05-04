# prompt-library-mcp

An MCP server that maintains a personal library of **projects** and
**reusable chat prompts**. Backed by SQLite + FTS5; reachable from Claude
Desktop or directly from the Anthropic SDK.

See [DESIGN.md](DESIGN.md) for the full design and
[MCP_SERVER_PROMPTS.md](MCP_SERVER_PROMPTS.md) for the prompts driving the
incremental build.

## Status

Feature-complete for v1. **101 tests passing.**

| Capability | Where |
|---|---|
| Project CRUD (add/update/list/get/archive/delete) | [project_tools.py](prompt_library/tools/project_tools.py) |
| Prompt CRUD + FTS5-ranked search | [prompt_tools.py](prompt_library/tools/prompt_tools.py) |
| Tag summary, export/import, backup | [library_tools.py](prompt_library/tools/library_tools.py) |
| SQLite storage + migrations | [storage/](prompt_library/storage/) |
| Stderr logging with per-tool tracing | [logging_setup.py](prompt_library/logging_setup.py) |

## Requirements

- Python 3.10+
- SQLite ≥ 3.9 (FTS5 support — bundled with macOS and standard Python builds)
- macOS for Claude Desktop integration (optional)

## Quickstart

```bash
make install         # installs the package + dev deps in editable mode
make test            # runs the full test suite (101 tests)
make smoke           # opens a temp DB, runs migrations, calls a stub from each module
make run             # launches the MCP server over stdio (for debugging)
```

## Make targets

| Target | What it does |
|---|---|
| `make install` | `pip install -e ".[dev]"` |
| `make test` | Run the full pytest suite |
| `make smoke` | Open a temp DB, apply migrations, exercise stub tools |
| `make run` | Launch the MCP server over stdio (for debugging) |
| `make register-help` | Print a paste-ready Claude Desktop config block with absolute paths |
| `make clean` | Remove caches |

## Environment variables

Configured via a local `.env` file (gitignored). Copy from `.env.example`.

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `LIBRARY_PATH` | no | `~/.config/prompt-library/library.db` | Path to the SQLite library file. The directory is created on first use. |
| `LOG_LEVEL` | no | `INFO` | One of `DEBUG`, `INFO`, `WARNING`, `ERROR`. |

## Logging

All logs go to **stderr** (stdout is reserved for the MCP protocol). Every
tool invocation emits structured lines on the `prompt_library.tools` logger:

```
2026-05-04 12:30:01 [INFO] prompt_library.tools: call add_project('trading-bot', tags=['python', 'mcp'])
2026-05-04 12:30:01 [INFO] prompt_library.tools: done add_project status=ok duration_ms=4
```

Successful calls log `status=ok`; tools that return `{"error": ...}` log
`status=error`; uncaught exceptions log `fail` with a stack trace.

## Registering with Claude Desktop

```bash
make register-help
```

This prints a JSON block tailored to your machine. Merge the printed
`mcpServers.prompt-library` entry into:

```
~/Library/Application Support/Claude/claude_desktop_config.json
```

Then quit Claude Desktop completely (Cmd+Q) and reopen — the
**prompt-library** tools will appear in the tools menu.

For reference, the block (with placeholder paths) is also in
[claude_desktop_config.example.json](claude_desktop_config.example.json):

```json
{
  "mcpServers": {
    "prompt-library": {
      "command": "/Library/Frameworks/Python.framework/Versions/3.10/bin/python3",
      "args": ["-m", "prompt_library.server"],
      "cwd": "/Users/yulin/projects/prompt-library",
      "env": {
        "LIBRARY_PATH": "",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

> Setting `LIBRARY_PATH` to an empty string falls back to the default
> (`~/.config/prompt-library/library.db`). To use a different file, put
> the absolute path there.

## Sample Claude Desktop prompts

Five prompts that exercise the server end-to-end. Paste any of them into a
fresh Claude Desktop chat once the server is registered.

1. **Add a project**
   > Use the prompt-library tools to add a project called "trading-bot"
   > with tags python and mcp, status active, and the description
   > "MCP server for weekly market analysis".

2. **Find a prompt by topic**
   > Find my prompt for code review and show me its body.

3. **List by status**
   > Show me all my paused projects, sorted by most recently updated.

4. **Search across both kinds**
   > What do I have related to MCP servers? Search my prompts and list any
   > matching projects too.

5. **Run a backup**
   > Back up my library and tell me the file path. Then summarize how many
   > projects and prompts are currently stored.

## Project layout

```
prompt-library/
├── DESIGN.md
├── MCP_SERVER_PROMPTS.md
├── Makefile
├── pyproject.toml
├── claude_desktop_config.example.json
├── .env.example
├── exports/                         # gitignored, runtime
├── backups/                         # gitignored, runtime
├── scripts/
│   ├── print_claude_config.py
│   └── smoke_test.py
├── tests/
│   ├── conftest.py
│   ├── test_skeleton.py             # schema + migrations
│   ├── test_projects.py             # 32 tests
│   ├── test_prompts.py              # 39 tests
│   └── test_io.py                   # 24 tests (tag summary + export/import + backup)
└── prompt_library/
    ├── server.py                    # entry point (stdio)
    ├── config.py                    # env vars + paths
    ├── logging_setup.py             # stderr logging + log_tool decorator
    ├── storage/
    │   ├── library.py               # Library class — public Python API
    │   ├── connection.py            # lazy-init shared Library for tools
    │   ├── schema.sql               # DDL
    │   ├── migrations.py            # version-tracked schema upgrades
    │   ├── models.py                # TypedDicts
    │   └── io.py                    # markdown/JSON export + import
    └── tools/
        ├── project_tools.py         # 6 project tools
        ├── prompt_tools.py          # 6 prompt tools (incl. FTS5 search)
        └── library_tools.py         # 4 library helpers (tag summary, export, import, backup)
```
