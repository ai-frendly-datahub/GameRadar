from __future__ import annotations

import asyncio
from importlib import import_module
import os
from pathlib import Path
from typing import Optional, Any, Callable, Protocol, cast

from radar.mcp_server.tools import (
    export_data,
    get_entity_stats,
    query_articles,
    recent_articles,
    search_fulltext,
)

def _db_path() -> Path:
    return Path(os.getenv("RADAR_DB_PATH", "data/radar_data.duckdb"))


def _search_db_path() -> Path:
    return Path(os.getenv("RADAR_SEARCH_DB_PATH", "data/search_index.db"))


def _as_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _as_float(value: object, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _list_tool_specs() -> list[dict[str, object]]:
    return [
        {
            "name": "query_articles",
            "description": "Query articles with optional filters (source, category, date range).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Filter by source name (partial match)"},
                    "category": {"type": "string", "description": "Filter by category"},
                    "date_range_days": {"type": "integer", "minimum": 1, "description": "Filter to last N days"},
                    "limit": {"type": "integer", "minimum": 1, "default": 50},
                },
            },
        },
        {
            "name": "search_fulltext",
            "description": "Full-text search in article titles and summaries.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "minimum": 1, "default": 20},
                },
                "required": ["query"],
            },
        },
        {
            "name": "get_entity_stats",
            "description": "Get entity statistics (type counts and trends).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "date_range_days": {"type": "integer", "minimum": 1, "description": "Filter to last N days"},
                    "limit": {"type": "integer", "minimum": 1, "default": 20},
                },
            },
        },
        {
            "name": "recent_articles",
            "description": "Get recent articles from the last N days.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "minimum": 1, "default": 7},
                    "limit": {"type": "integer", "minimum": 1, "default": 20},
                },
            },
        },
        {
            "name": "export_data",
            "description": "Export article data in JSON or CSV format.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "format": {"type": "string", "enum": ["json", "csv"], "default": "json"},
                    "date_range_days": {"type": "integer", "minimum": 1, "description": "Filter to last N days"},
                    "limit": {"type": "integer", "minimum": 1, "default": 1000},
                },
            },
        },
    ]


def _call_tool_handler(name: str, arguments: object) -> str:
    args = _coerce_args(arguments)
    db_path = _db_path()
    search_db_path = _search_db_path()

    if name == "query_articles":
        source_val = args.get("source")
        source: Optional[str] = str(source_val) if source_val else None
        category_val = args.get("category")
        category: Optional[str] = str(category_val) if category_val else None
        date_range_val = args.get("date_range_days")
        date_range: Optional[int] = _as_int(date_range_val, -1) if date_range_val else None
        return query_articles(
            db_path=db_path,
            source=source,
            category=category,
            date_range_days=date_range if date_range and date_range > 0 else None,
            limit=_as_int(args.get("limit"), 50),
        )
    if name == "search_fulltext":
        return search_fulltext(
            db_path=db_path,
            search_db_path=search_db_path,
            query=str(args.get("query", "")),
            limit=_as_int(args.get("limit"), 20),
        )
    if name == "get_entity_stats":
        date_range_val = args.get("date_range_days")
        date_range: Optional[int] = _as_int(date_range_val, -1) if date_range_val else None
        return get_entity_stats(
            db_path=db_path,
            date_range_days=date_range if date_range and date_range > 0 else None,
            limit=_as_int(args.get("limit"), 20),
        )
    if name == "recent_articles":
        return recent_articles(
            db_path=db_path,
            days=_as_int(args.get("days"), 7),
            limit=_as_int(args.get("limit"), 20),
        )
    if name == "export_data":
        date_range_val = args.get("date_range_days")
        date_range: Optional[int] = _as_int(date_range_val, -1) if date_range_val else None
        return export_data(
            db_path=db_path,
            format=str(args.get("format", "json")),
            date_range_days=date_range if date_range and date_range > 0 else None,
            limit=_as_int(args.get("limit"), 1000),
        )
    return f"Unknown tool: {name}"


class _McpApp(Protocol):
    def list_tools(self) -> Callable[[Callable[..., object]], Callable[..., object]]: ...

    def call_tool(self) -> Callable[[Callable[..., object]], Callable[..., object]]: ...

    async def run(self, read_stream: object, write_stream: object, options: object) -> None: ...

    def create_initialization_options(self) -> object: ...


class _ServerCtor(Protocol):
    def __call__(self, name: str) -> _McpApp: ...


class _ToolCtor(Protocol):
    def __call__(self, **kwargs: object) -> object: ...


class _TextContentCtor(Protocol):
    def __call__(self, *, type: str, text: str) -> object: ...


class _StdioContext(Protocol):
    async def __aenter__(self) -> tuple[object, object]: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: Optional[BaseException],
        traceback: object,
    ) -> object: ...


class _StdioServer(Protocol):
    def __call__(self) -> _StdioContext: ...


def _coerce_args(arguments: object) -> dict[str, object]:
    if not isinstance(arguments, dict):
        return {}

    raw_args = cast(dict[object, object], arguments)
    coerced: dict[str, object] = {}
    for key, value in raw_args.items():
        if isinstance(key, str):
            coerced[key] = value
    return coerced


def create_app() -> _McpApp:
    server_module = import_module("mcp.server")
    types_module = import_module("mcp.types")
    server_ctor = cast(_ServerCtor, getattr(server_module, "Server"))
    tool_ctor = cast(_ToolCtor, getattr(types_module, "Tool"))
    text_content_ctor = cast(_TextContentCtor, getattr(types_module, "TextContent"))

    app = server_ctor("radar-template")

    @app.list_tools()
    async def list_tools() -> list[object]:
        return [tool_ctor(**tool_spec) for tool_spec in _list_tool_specs()]
    _ = list_tools

    @app.call_tool()
    async def call_tool(name: str, arguments: object) -> list[object]:
        result = _call_tool_handler(name, arguments)
        return [text_content_ctor(type="text", text=result)]
    _ = call_tool

    return app


async def main() -> None:
    stdio_module = import_module("mcp.server.stdio")
    stdio_server = cast(_StdioServer, getattr(stdio_module, "stdio_server"))

    app = create_app()
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
