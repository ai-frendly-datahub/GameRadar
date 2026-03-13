from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Any, cast

import duckdb

from radar.nl_query import parse_query
from radar.search_index import SearchIndex


_ALLOWED_SQL = re.compile(r"^\s*(SELECT|WITH|EXPLAIN)\b", re.IGNORECASE)


def _format_rows(columns: list[str], rows: list[tuple[object, ...]]) -> str:
    """Format query results as aligned text table."""
    if not rows:
        return "No rows returned."
    text_rows = [tuple("" if value is None else str(value) for value in row) for row in rows]
    widths = [len(name) for name in columns]
    for row in text_rows:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    header = " | ".join(col.ljust(widths[idx]) for idx, col in enumerate(columns))
    divider = "-+-".join("-" * widths[idx] for idx in range(len(columns)))
    body = [
        " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(row)) for row in text_rows
    ]
    return "\n".join([header, divider, *body])


def _filter_links(
    *,
    db_path: Path,
    links: list[str],
    days: int | None = None,
    source: str | None = None,
    category: str | None = None,
) -> set[str]:
    if not links:
        return set()

    where_clauses: list[str] = [f"link IN ({', '.join('?' for _ in links)})"]
    params: list[object] = [*links]

    if days is not None and days > 0:
        where_clauses.append("collected_at >= ?")
        params.append(datetime.now() - timedelta(days=days))

    if source:
        where_clauses.append("LOWER(source) LIKE LOWER(?)")
        params.append(f"%{source}%")

    if category:
        where_clauses.append("LOWER(category) = LOWER(?)")
        params.append(category)

    where_sql = " AND ".join(where_clauses)
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = conn.execute(
            f"SELECT link FROM articles WHERE {where_sql}",
            params,
        ).fetchall()
    finally:
        conn.close()

    return {str(row[0]) for row in rows}


def query_articles(
    *,
    db_path: Path,
    source: str | None = None,
    category: str | None = None,
    date_range_days: int | None = None,
    limit: int = 50,
) -> str:
    """Query articles with optional filters.

    Args:
        db_path: Path to DuckDB database
        source: Filter by source name (partial match)
        category: Filter by category
        date_range_days: Filter to articles from last N days
        limit: Maximum number of results

    Returns:
        Formatted text results
    """
    where_clauses: list[str] = []
    params: list[object] = []

    if source is not None:
        where_clauses.append("LOWER(source) LIKE LOWER(?)")
        params.append(f"%{source}%")

    if category is not None:
        where_clauses.append("category = ?")
        params.append(category)

    if date_range_days is not None and date_range_days > 0:
        cutoff = datetime.now() - timedelta(days=date_range_days)
        where_clauses.append("collected_at >= ?")
        params.append(cutoff)

    where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        query = f"""
            SELECT title, source, category, link, published, collected_at
            FROM articles
            {where_clause}
            ORDER BY collected_at DESC
            LIMIT ?
        """
        cursor = conn.execute(query, params + [limit])
        rows = cast(list[tuple[str, str, str, str, datetime | None, datetime]], cursor.fetchall())
    finally:
        conn.close()

    if not rows:
        return "No articles found."

    lines = [f"Found {len(rows)} article(s):"]
    for idx, (title, source_name, cat, link, published, collected) in enumerate(rows, 1):
        pub_str = published.strftime("%Y-%m-%d") if published else "N/A"
        lines.append(f"\n{idx}. {title}")
        lines.append(f"   Source: {source_name} | Category: {cat}")
        lines.append(f"   Published: {pub_str} | Collected: {collected.strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"   Link: {link}")

    return "\n".join(lines)


def search_fulltext(
    *,
    db_path: Path,
    search_db_path: Path,
    query: str,
    limit: int = 20,
) -> str:
    """Full-text search in article titles and summaries.

    Args:
        db_path: Path to DuckDB database
        search_db_path: Path to search index database
        query: Search query string
        limit: Maximum number of results

    Returns:
        Formatted text results
    """
    if not query.strip():
        return "Search query cannot be empty."

    try:
        with SearchIndex(search_db_path) as idx:
            results = idx.search(query, limit=limit)
    except Exception as exc:
        return f"Search error: {exc}"

    if not results:
        return f"No articles found matching '{query}'."

    lines = [f"Found {len(results)} result(s) for '{query}':"]
    for idx, result in enumerate(results, 1):
        lines.append(f"\n{idx}. {result.title}")
        lines.append(f"   Link: {result.link}")
        lines.append(f"   Snippet: {result.snippet}")

    return "\n".join(lines)


def get_entity_stats(
    *,
    db_path: Path,
    date_range_days: int | None = None,
    limit: int = 20,
) -> str:
    """Get entity statistics (type counts and trends).

    Args:
        db_path: Path to DuckDB database
        date_range_days: Filter to articles from last N days
        limit: Maximum number of entity types to return

    Returns:
        Formatted text results
    """
    where_clause = ""
    params: list[object] = []

    if date_range_days is not None and date_range_days > 0:
        cutoff = datetime.now() - timedelta(days=date_range_days)
        where_clause = "WHERE collected_at >= ?"
        params.append(cutoff)

    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        query = f"""
            SELECT entities_json
            FROM articles
            {where_clause}
        """
        cursor = conn.execute(query, params)
        rows = cast(list[tuple[str | None]], cursor.fetchall())
    finally:
        conn.close()

    entity_counts: Counter[str] = Counter()
    for row in rows:
        raw_entities = row[0]
        if not raw_entities:
            continue
        try:
            entities = cast(dict[str, list[str]], json.loads(raw_entities))
            for entity_type, values in entities.items():
                if isinstance(values, list):
                    entity_counts[entity_type] += len(values)
        except json.JSONDecodeError:
            continue

    if not entity_counts:
        return "No entity data found."

    lines = ["Entity Statistics:"]
    for entity_type, count in entity_counts.most_common(limit):
        lines.append(f"- {entity_type}: {count} matches")

    return "\n".join(lines)


def recent_articles(
    *,
    db_path: Path,
    days: int = 7,
    limit: int = 20,
) -> str:
    """Get recent articles from the last N days.

    Args:
        db_path: Path to DuckDB database
        days: Number of days to look back
        limit: Maximum number of articles

    Returns:
        Formatted text results
    """
    cutoff = datetime.now() - timedelta(days=days)

    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        cursor = conn.execute(
            """
            SELECT title, source, category, link, collected_at
            FROM articles
            WHERE collected_at >= ?
            ORDER BY collected_at DESC
            LIMIT ?
            """,
            [cutoff, limit],
        )
        rows = cast(list[tuple[str, str, str, str, datetime]], cursor.fetchall())
    finally:
        conn.close()

    if not rows:
        return f"No articles found in the last {days} days."

    lines = [f"Recent articles (last {days} days) - {len(rows)} found:"]
    for idx, (title, source_name, cat, link, collected) in enumerate(rows, 1):
        lines.append(f"\n{idx}. {title}")
        lines.append(f"   Source: {source_name} | Category: {cat}")
        lines.append(f"   Collected: {collected.strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"   Link: {link}")

    return "\n".join(lines)


def export_data(
    *,
    db_path: Path,
    format: str = "json",
    date_range_days: int | None = None,
    limit: int = 1000,
) -> str:
    """Export article data in JSON or CSV format.

    Args:
        db_path: Path to DuckDB database
        format: Export format ('json' or 'csv')
        date_range_days: Filter to articles from last N days
        limit: Maximum number of articles to export

    Returns:
        Formatted export data or error message
    """
    where_clause = ""
    params: list[object] = []

    if date_range_days is not None and date_range_days > 0:
        cutoff = datetime.now() - timedelta(days=date_range_days)
        where_clause = "WHERE collected_at >= ?"
        params.append(cutoff)

    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        query = f"""
            SELECT title, source, category, link, summary, published, collected_at, entities_json
            FROM articles
            {where_clause}
            ORDER BY collected_at DESC
            LIMIT ?
        """
        cursor = conn.execute(query, params + [limit])
        rows = cast(
            list[tuple[str, str, str, str, str | None, datetime | None, datetime, str | None]],
            cursor.fetchall(),
        )
    finally:
        conn.close()

    if not rows:
        return "No data to export."

    if format.lower() == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            ["Title", "Source", "Category", "Link", "Summary", "Published", "Collected", "Entities"]
        )
        for title, source_name, cat, link, summary, published, collected, entities_json in rows:
            pub_str = published.strftime("%Y-%m-%d") if published else ""
            writer.writerow(
                [
                    title,
                    source_name,
                    cat,
                    link,
                    summary or "",
                    pub_str,
                    collected.isoformat(),
                    entities_json or "",
                ]
            )
        return output.getvalue()
    else:  # json
        data: list[dict[str, Any]] = []
        for title, source_name, cat, link, summary, published, collected, entities_json in rows:
            entities: dict[str, Any] = {}
            if entities_json:
                try:
                    entities = cast(dict[str, Any], json.loads(entities_json))
                except json.JSONDecodeError:
                    pass
            data.append(
                {
                    "title": title,
                    "source": source_name,
                    "category": cat,
                    "link": link,
                    "summary": summary,
                    "published": published.isoformat() if published else None,
                    "collected_at": collected.isoformat(),
                    "entities": entities,
                }
            )
        return json.dumps(data, ensure_ascii=False, indent=2)


def handle_search(*, search_db_path: Path, db_path: Path, query: str, limit: int = 20) -> str:
    parsed = parse_query(query)
    effective_limit = parsed.limit if parsed.limit is not None else limit
    if effective_limit <= 0:
        return "No results found."

    search_text = parsed.search_text.strip()
    if not search_text:
        return query_articles(
            db_path=db_path,
            source=parsed.source,
            category=parsed.category,
            date_range_days=parsed.days,
            limit=effective_limit,
        )

    with SearchIndex(search_db_path) as idx:
        results = idx.search(search_text, limit=effective_limit)

    allowed_links = _filter_links(
        db_path=db_path,
        links=[result.link for result in results],
        days=parsed.days,
        source=parsed.source,
        category=parsed.category,
    )
    if parsed.days is not None or parsed.source is not None or parsed.category is not None:
        results = [result for result in results if result.link in allowed_links]

    if not results:
        return "No results found."

    lines = [f"Found {len(results)} result(s):"]
    for result in results:
        lines.append(f"- {result.title}")
        lines.append(f"  Link: {result.link}")
        lines.append(f"  Snippet: {result.snippet}")
    return "\n".join(lines)


def handle_recent_updates(*, db_path: Path, days: int = 7, limit: int = 20) -> str:
    return recent_articles(db_path=db_path, days=days, limit=limit)


def handle_sql(*, db_path: Path, query: str) -> str:
    if not _ALLOWED_SQL.match(query):
        return "Error: Only SELECT/WITH/EXPLAIN queries are allowed."

    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        cursor = conn.execute(query)
        rows = cursor.fetchall()
        description = cursor.description
        columns = [str(desc[0]) for desc in description] if description else ["result"]
        return _format_rows(columns, rows)
    except Exception as exc:  # noqa: BLE001
        return f"Error: {exc}"
    finally:
        conn.close()


def handle_top_trends(*, db_path: Path, days: int = 7, limit: int = 10) -> str:
    return get_entity_stats(db_path=db_path, date_range_days=days, limit=limit)


def handle_price_watch(*, threshold: float = 0.0) -> str:
    _ = threshold
    return "Not available in template project"
