# Radar-Template MCP Server Implementation

## Overview
Complete MCP (Model Context Protocol) server implementation for Radar-Template with 5 tools for querying and exporting article data from DuckDB.

## Files Created/Modified

### New Files
1. **radar/mcp_server/__init__.py** - Package initialization
2. **radar/mcp_server/config.py** - MCP server configuration management
3. **radar/mcp_server/tools.py** - 5 MCP tool implementations
4. **radar/mcp_server/server.py** - MCP server with tool handlers
5. **tests/unit/test_mcp_server.py** - Comprehensive unit tests (25 tests)

## 5 MCP Tools Implemented

### 1. query_articles
Query articles with optional filters (source, category, date range).

**Parameters:**
- `source` (str, optional): Filter by source name (partial match)
- `category` (str, optional): Filter by category
- `date_range_days` (int, optional): Filter to articles from last N days
- `limit` (int, default=50): Maximum number of results

**Returns:** Formatted text with article titles, sources, categories, links, and dates

### 2. search_fulltext
Full-text search in article titles and summaries using SQLite FTS5.

**Parameters:**
- `query` (str, required): Search query string
- `limit` (int, default=20): Maximum number of results

**Returns:** Formatted text with search results including snippets

### 3. get_entity_stats
Get entity statistics (type counts and trends) from matched entities.

**Parameters:**
- `date_range_days` (int, optional): Filter to articles from last N days
- `limit` (int, default=20): Maximum number of entity types to return

**Returns:** Formatted text with entity type counts and frequencies

### 4. recent_articles
Get recent articles from the last N days.

**Parameters:**
- `days` (int, default=7): Number of days to look back
- `limit` (int, default=20): Maximum number of articles

**Returns:** Formatted text with recent articles and metadata

### 5. export_data
Export article data in JSON or CSV format.

**Parameters:**
- `format` (str, default="json"): Export format ('json' or 'csv')
- `date_range_days` (int, optional): Filter to articles from last N days
- `limit` (int, default=1000): Maximum number of articles to export

**Returns:** JSON array or CSV text with full article data

## Key Features

✓ **Type Safety**: Full type hints with MyPy strict mode compatibility
✓ **Error Handling**: Graceful handling of empty databases and invalid queries
✓ **Filtering**: Support for source, category, and date range filters
✓ **Export Formats**: JSON and CSV export options
✓ **Search**: Full-text search using SQLite FTS5
✓ **Entity Analysis**: Entity statistics and trend analysis
✓ **Testing**: 25 comprehensive unit tests covering all tools

## Test Coverage

- **TestQueryArticles** (6 tests): All filtering options, limits, empty results
- **TestSearchFulltext** (2 tests): Keyword search, empty query handling
- **TestGetEntityStats** (4 tests): Entity stats, date filtering, empty database
- **TestRecentArticles** (4 tests): Recent articles, custom date ranges, limits
- **TestExportData** (7 tests): JSON/CSV export, filtering, structure validation
- **TestToolIntegration** (2 tests): All tools with populated and empty databases

**Result: 25/25 tests PASSED**

## Architecture

```
radar/mcp_server/
├── __init__.py          # Package initialization
├── config.py            # Configuration management
├── tools.py             # 5 tool implementations
└── server.py            # MCP server with handlers
```

## Database Integration

All tools use `RadarStorage` class from `radar/storage.py`:
- DuckDB for persistent storage
- Articles table with full-text search support
- Entity JSON storage for matched entities
- Efficient batch operations

## Type Checking

All code passes Python type checking:
- Full type hints on all functions
- No `# type: ignore` comments
- Compatible with MyPy strict mode
- Proper handling of Optional types

## Usage

```python
from radar.mcp_server.tools import (
    query_articles,
    search_fulltext,
    get_entity_stats,
    recent_articles,
    export_data,
)
from pathlib import Path

db_path = Path("data/radar_data.duckdb")

# Query articles
result = query_articles(db_path=db_path, category="programming", limit=10)

# Search
result = search_fulltext(db_path=db_path, search_db_path=Path("data/search.db"), query="Python")

# Entity stats
result = get_entity_stats(db_path=db_path, limit=20)

# Recent articles
result = recent_articles(db_path=db_path, days=7, limit=20)

# Export data
result = export_data(db_path=db_path, format="json", limit=100)
```

## Verification

✓ All 25 unit tests pass
✓ Python syntax validation passed
✓ Type hints complete and valid
✓ No external dependencies added
✓ Follows Radar-Template conventions (100 char line length, 4-space indent)
✓ Full documentation with docstrings
