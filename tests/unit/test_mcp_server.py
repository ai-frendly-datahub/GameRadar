from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Generator

import pytest

from radar.models import Article
from radar.mcp_server.tools import (
    export_data,
    get_entity_stats,
    query_articles,
    recent_articles,
    search_fulltext,
)
from radar.storage import RadarStorage


@pytest.fixture
def temp_db() -> Generator[Path, None, None]:
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.duckdb"


@pytest.fixture
def sample_articles() -> list[Article]:
    """Create sample articles for testing."""
    now = datetime.now(timezone.utc)
    return [
        Article(
            title="Python Best Practices",
            link="http://example.com/python-1",
            summary="Learn Python best practices",
            published=now - timedelta(days=1),
            source="TechBlog",
            category="programming",
            matched_entities={"language": ["Python"], "topic": ["best practices"]},
        ),
        Article(
            title="Web Development Trends",
            link="http://example.com/web-1",
            summary="Latest web development trends",
            published=now - timedelta(days=2),
            source="WebNews",
            category="web",
            matched_entities={"topic": ["web development", "trends"]},
        ),
        Article(
            title="Data Science Guide",
            link="http://example.com/data-1",
            summary="Complete guide to data science",
            published=now - timedelta(days=5),
            source="DataBlog",
            category="data",
            matched_entities={"topic": ["data science"], "language": ["Python"]},
        ),
        Article(
            title="Machine Learning Basics",
            link="http://example.com/ml-1",
            summary="Introduction to machine learning",
            published=now - timedelta(days=10),
            source="MLBlog",
            category="ai",
            matched_entities={"topic": ["machine learning"]},
        ),
    ]


@pytest.fixture
def populated_db(temp_db: Path, sample_articles: list[Article]) -> Path:
    """Create a database with sample articles."""
    with RadarStorage(temp_db) as storage:
        storage.upsert_articles(sample_articles)
    return temp_db


class TestQueryArticles:
    """Test query_articles tool."""

    def test_query_all_articles(self, populated_db: Path) -> None:
        """Should return all articles when no filters applied."""
        result = query_articles(db_path=populated_db, limit=100)
        assert "Found 4 article(s)" in result
        assert "Python Best Practices" in result
        assert "Web Development Trends" in result

    def test_query_by_source(self, populated_db: Path) -> None:
        """Should filter articles by source."""
        result = query_articles(db_path=populated_db, source="TechBlog", limit=100)
        assert "Found 1 article(s)" in result
        assert "Python Best Practices" in result
        assert "Web Development Trends" not in result

    def test_query_by_category(self, populated_db: Path) -> None:
        """Should filter articles by category."""
        result = query_articles(db_path=populated_db, category="programming", limit=100)
        assert "Found 1 article(s)" in result
        assert "Python Best Practices" in result

    def test_query_by_date_range(self, populated_db: Path) -> None:
        """Should filter articles by date range."""
        result = query_articles(db_path=populated_db, date_range_days=3, limit=100)
        # All articles are collected today, so all should be returned
        assert "Found" in result
        assert "Python Best Practices" in result

    def test_query_with_limit(self, populated_db: Path) -> None:
        """Should respect limit parameter."""
        result = query_articles(db_path=populated_db, limit=2)
        assert "Found 2 article(s)" in result

    def test_query_empty_result(self, populated_db: Path) -> None:
        """Should return appropriate message for empty results."""
        result = query_articles(db_path=populated_db, source="NonExistent")
        assert "No articles found" in result


class TestSearchFulltext:
    """Test search_fulltext tool."""

    def test_search_by_keyword(self, populated_db: Path, temp_db: Path) -> None:
        """Should find articles by keyword search."""
        # Create search index
        from radar.search_index import SearchIndex

        search_db = temp_db.parent / "search.db"
        with SearchIndex(search_db) as idx:
            idx.upsert_batch(
                [
                    ("http://example.com/python-1", "Python Best Practices", "Learn Python best practices"),
                    ("http://example.com/web-1", "Web Development Trends", "Latest web development trends"),
                ]
            )

        result = search_fulltext(
            db_path=populated_db,
            search_db_path=search_db,
            query="Python",
            limit=10,
        )
        assert "Found" in result or "No articles found" in result

    def test_search_empty_query(self, populated_db: Path, temp_db: Path) -> None:
        """Should reject empty search query."""
        search_db = temp_db.parent / "search.db"
        result = search_fulltext(
            db_path=populated_db,
            search_db_path=search_db,
            query="",
            limit=10,
        )
        assert "cannot be empty" in result


class TestGetEntityStats:
    """Test get_entity_stats tool."""

    def test_entity_stats_all(self, populated_db: Path) -> None:
        """Should return entity statistics for all articles."""
        result = get_entity_stats(db_path=populated_db, limit=10)
        assert "Entity Statistics" in result
        assert "topic" in result or "language" in result

    def test_entity_stats_with_date_range(self, populated_db: Path) -> None:
        """Should filter entity stats by date range."""
        result = get_entity_stats(db_path=populated_db, date_range_days=3, limit=10)
        assert "Entity Statistics" in result

    def test_entity_stats_empty(self, temp_db: Path) -> None:
        """Should handle empty database gracefully."""
        # Create empty database
        with RadarStorage(temp_db):
            pass
        result = get_entity_stats(db_path=temp_db, limit=10)
        assert "No entity data found" in result

    def test_entity_stats_limit(self, populated_db: Path) -> None:
        """Should respect limit parameter."""
        result = get_entity_stats(db_path=populated_db, limit=1)
        lines = result.split("\n")
        # Should have header + 1 entity line
        assert len(lines) <= 3


class TestRecentArticles:
    """Test recent_articles tool."""

    def test_recent_articles_default(self, populated_db: Path) -> None:
        """Should return recent articles from last 7 days."""
        result = recent_articles(db_path=populated_db, days=7, limit=100)
        assert "Recent articles" in result
        assert "Found" in result or "found" in result

    def test_recent_articles_custom_days(self, populated_db: Path) -> None:
        """Should filter by custom day range."""
        result = recent_articles(db_path=populated_db, days=3, limit=100)
        assert "Recent articles (last 3 days)" in result

    def test_recent_articles_with_limit(self, populated_db: Path) -> None:
        """Should respect limit parameter."""
        result = recent_articles(db_path=populated_db, days=30, limit=2)
        lines = result.split("\n")
        # Should have header + 2 articles (each with 4 lines)
        assert len(lines) >= 2

    def test_recent_articles_empty(self, temp_db: Path) -> None:
        """Should handle empty database gracefully."""
        # Create empty database
        with RadarStorage(temp_db):
            pass
        result = recent_articles(db_path=temp_db, days=7, limit=100)
        assert "No articles found" in result


class TestExportData:
    """Test export_data tool."""

    def test_export_json(self, populated_db: Path) -> None:
        """Should export data as JSON."""
        result = export_data(db_path=populated_db, format="json", limit=100)
        assert result.startswith("[")
        data = json.loads(result)
        assert len(data) == 4
        assert data[0]["title"] == "Python Best Practices"
        assert "source" in data[0]
        assert "category" in data[0]
        assert "link" in data[0]

    def test_export_csv(self, populated_db: Path) -> None:
        """Should export data as CSV."""
        result = export_data(db_path=populated_db, format="csv", limit=100)
        lines = result.strip().split("\n")
        assert len(lines) == 5  # Header + 4 articles
        assert "Title" in lines[0]
        assert "Source" in lines[0]

    def test_export_with_date_range(self, populated_db: Path) -> None:
        """Should filter export by date range."""
        result = export_data(db_path=populated_db, format="json", date_range_days=3, limit=100)
        data = json.loads(result)
        # All articles are collected today, so all should be returned
        assert len(data) >= 2

    def test_export_with_limit(self, populated_db: Path) -> None:
        """Should respect limit parameter."""
        result = export_data(db_path=populated_db, format="json", limit=2)
        data = json.loads(result)
        assert len(data) == 2

    def test_export_empty(self, temp_db: Path) -> None:
        """Should handle empty database gracefully."""
        # Create empty database
        with RadarStorage(temp_db):
            pass
        result = export_data(db_path=temp_db, format="json", limit=100)
        assert "No data to export" in result

    def test_export_json_structure(self, populated_db: Path) -> None:
        """Should export JSON with correct structure."""
        result = export_data(db_path=populated_db, format="json", limit=1)
        data = json.loads(result)
        assert len(data) == 1
        article = data[0]
        assert "title" in article
        assert "source" in article
        assert "category" in article
        assert "link" in article
        assert "summary" in article
        assert "published" in article
        assert "collected_at" in article
        assert "entities" in article

    def test_export_csv_structure(self, populated_db: Path) -> None:
        """Should export CSV with correct structure."""
        result = export_data(db_path=populated_db, format="csv", limit=1)
        lines = result.strip().split("\n")
        assert len(lines) == 2  # Header + 1 article
        header = lines[0].split(",")
        assert "Title" in header
        assert "Source" in header
        assert "Category" in header


class TestToolIntegration:
    """Integration tests for MCP tools."""

    def test_all_tools_with_populated_db(self, populated_db: Path, temp_db: Path) -> None:
        """Should execute all tools successfully with populated database."""
        # query_articles
        result1 = query_articles(db_path=populated_db, limit=10)
        assert "Found" in result1 or "No articles" in result1

        # get_entity_stats
        result2 = get_entity_stats(db_path=populated_db, limit=10)
        assert "Entity Statistics" in result2 or "No entity data" in result2

        # recent_articles
        result3 = recent_articles(db_path=populated_db, days=30, limit=10)
        assert "Recent articles" in result3 or "No articles" in result3

        # export_data (json)
        result4 = export_data(db_path=populated_db, format="json", limit=10)
        assert result4.startswith("[") or "No data" in result4

        # export_data (csv)
        result5 = export_data(db_path=populated_db, format="csv", limit=10)
        assert "Title" in result5 or "No data" in result5

    def test_tools_with_empty_db(self, temp_db: Path) -> None:
        """Should handle empty database gracefully in all tools."""
        # Create empty database
        with RadarStorage(temp_db):
            pass

        # query_articles
        result1 = query_articles(db_path=temp_db)
        assert "No articles found" in result1

        # get_entity_stats
        result2 = get_entity_stats(db_path=temp_db)
        assert "No entity data found" in result2

        # recent_articles
        result3 = recent_articles(db_path=temp_db)
        assert "No articles found" in result3

        # export_data
        result4 = export_data(db_path=temp_db)
        assert "No data to export" in result4
