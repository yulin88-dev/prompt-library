"""Print a ready-to-paste Claude Desktop config block with absolute paths."""
from __future__ import annotations

import json
import os
import shutil
import sys


def main() -> None:
    python_path = shutil.which("python3") or sys.executable
    project_dir = os.path.abspath(os.getcwd())
    cfg = {
        "mcpServers": {
            "prompt-library": {
                "command": python_path,
                "args": ["-m", "prompt_library.server"],
                "cwd": project_dir,
                "env": {
                    "LIBRARY_PATH": "",
                    "LOG_LEVEL": "INFO",
                },
            }
        }
    }
    print("# Add the 'prompt-library' entry below to your Claude Desktop config at:")
    print("# ~/Library/Application Support/Claude/claude_desktop_config.json")
    print()
    print(json.dumps(cfg, indent=2))


if __name__ == "__main__":
    main()
