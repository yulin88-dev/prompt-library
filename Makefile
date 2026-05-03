.PHONY: help install test smoke run register-help clean

PYTHON := python3

help:
	@echo "Prompt Library MCP — make targets"
	@echo ""
	@echo "  make install         Install package + dev deps in editable mode"
	@echo "  make test            Run unit tests"
	@echo "  make smoke           Initialize the DB and call a stub tool"
	@echo "  make run             Launch the MCP server (stdio; for debugging)"
	@echo "  make register-help   Print Claude Desktop config block to paste"
	@echo "  make clean           Remove caches"

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest tests/ -v

smoke:
	$(PYTHON) scripts/smoke_test.py

run:
	$(PYTHON) -m prompt_library.server

register-help:
	@$(PYTHON) scripts/print_claude_config.py

clean:
	rm -rf .pytest_cache .ruff_cache **/__pycache__
