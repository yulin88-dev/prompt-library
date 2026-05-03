"""Configuration: env vars and default paths."""
from __future__ import annotations

import logging
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_LIBRARY_PATH = Path.home() / ".config" / "prompt-library" / "library.db"
LIBRARY_PATH = Path(os.environ.get("LIBRARY_PATH") or DEFAULT_LIBRARY_PATH).expanduser()

LOG_LEVEL = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)

EXPORTS_DIR = PROJECT_ROOT / "exports"
BACKUPS_DIR = PROJECT_ROOT / "backups"
