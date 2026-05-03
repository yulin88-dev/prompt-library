"""MCP server entry point — initializes storage, registers tools, runs over stdio."""
from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from prompt_library.config import LIBRARY_PATH, LOG_LEVEL
from prompt_library.logging_setup import log_tool, setup_logging
from prompt_library.storage.library import Library
from prompt_library.tools import library_tools, project_tools, prompt_tools

mcp = FastMCP("prompt-library-mcp")

# Each tool is wrapped with log_tool to capture args, duration, and status.

# Project tools
mcp.tool()(log_tool(project_tools.add_project))
mcp.tool()(log_tool(project_tools.update_project))
mcp.tool()(log_tool(project_tools.list_projects))
mcp.tool()(log_tool(project_tools.get_project))
mcp.tool()(log_tool(project_tools.archive_project))
mcp.tool()(log_tool(project_tools.delete_project))

# Prompt tools
mcp.tool()(log_tool(prompt_tools.add_prompt))
mcp.tool()(log_tool(prompt_tools.update_prompt))
mcp.tool()(log_tool(prompt_tools.list_prompts))
mcp.tool()(log_tool(prompt_tools.get_prompt))
mcp.tool()(log_tool(prompt_tools.delete_prompt))
mcp.tool()(log_tool(prompt_tools.search_prompts))

# Library helpers
mcp.tool()(log_tool(library_tools.tag_summary))
mcp.tool()(log_tool(library_tools.export_library))
mcp.tool()(log_tool(library_tools.import_library))
mcp.tool()(log_tool(library_tools.backup_library))


def main() -> None:
    setup_logging(LOG_LEVEL)
    log = logging.getLogger("prompt_library.server")
    # Open the DB once at startup to apply migrations and surface errors early.
    with Library(LIBRARY_PATH):
        log.info("Storage initialized; starting MCP stdio loop.")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
