from __future__ import annotations

import os
from pathlib import Path


class MCPServerConfig:
    """Configuration for MCP server."""

    def __init__(self) -> None:
        """Initialize MCP server configuration from environment variables."""
        self.db_path = Path(os.getenv("RADAR_DB_PATH", "data/radar_data.duckdb"))
        self.search_db_path = Path(os.getenv("RADAR_SEARCH_DB_PATH", "data/search_index.db"))

    def ensure_paths_exist(self) -> None:
        """Ensure database paths exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.search_db_path.parent.mkdir(parents=True, exist_ok=True)
