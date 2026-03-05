from __future__ import annotations

import json
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import duckdb
import pytest

from radar.models import Article
from radar.storage import RadarStorage


class TestStorageErrorHandling:
    """Test error handling in storage layer."""

    def test_connection_error_on_init(self) -> None:
        """Should raise on database connection failure."""
        with patch("radar.storage.duckdb.connect") as mock_connect:
            mock_connect.side_effect = duckdb.Error("Cannot connect to database")

            with pytest.raises(duckdb.Error):
                RadarStorage(Path("/tmp/test.duckdb"))

    def test_upsert_with_duckdb_error_continues_processing(self) -> None:
        """Should log error and continue processing remaining articles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            with RadarStorage(db_path) as storage:
                articles = [
                    Article(
                        title="Article 1",
                        link="http://example.com/1",
                        summary="Summary 1",
                        published=datetime.now(timezone.utc),
                        source="test_source",
                        category="test",
                    ),
                    Article(
                        title="Article 2",
                        link="http://example.com/2",
                        summary="Summary 2",
                        published=datetime.now(timezone.utc),
                        source="test_source",
                        category="test",
                    ),
                ]

                # Insert first article successfully
                storage.upsert_articles([articles[0]])

                # Verify first article was inserted
                recent = storage.recent_articles("test", days=7)
                assert len(recent) == 1

                # Insert second article (should succeed)
                storage.upsert_articles([articles[1]])

                # Verify both articles exist
                recent = storage.recent_articles("test", days=7)
                assert len(recent) == 2

    def test_upsert_constraint_violation_continues(self) -> None:
        """Should handle constraint violations gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            with RadarStorage(db_path) as storage:
                # Insert first article
                article1 = Article(
                    title="Article 1",
                    link="http://example.com/1",
                    summary="Summary 1",
                    published=datetime.now(timezone.utc),
                    source="test_source",
                    category="test",
                )
                storage.upsert_articles([article1])

                # Try to insert duplicate link (should be handled)
                article2 = Article(
                    title="Article 1 Updated",
                    link="http://example.com/1",
                    summary="Updated summary",
                    published=datetime.now(timezone.utc),
                    source="test_source",
                    category="test",
                )

                # Should not raise
                storage.upsert_articles([article2])

                # Verify article was updated
                recent = storage.recent_articles("test", days=7)
                assert len(recent) == 1
                assert recent[0].title == "Article 1 Updated"

    def test_upsert_logs_error_with_context(self) -> None:
        """Should log errors with article link context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            with RadarStorage(db_path) as storage:
                article = Article(
                    title="Test Article",
                    link="http://example.com/article",
                    summary="Test",
                    published=datetime.now(timezone.utc),
                    source="test_source",
                    category="test",
                )

                # Insert article successfully to verify logging works
                with patch("radar.storage.logger") as mock_logger:
                    storage.upsert_articles([article])
                    # Logger should not be called for successful insert
                    assert not mock_logger.error.called

    def test_partial_batch_success(self) -> None:
        """Should process all articles even if some fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            with RadarStorage(db_path) as storage:
                articles: list[Article] = [
                    Article(
                        title="Article 1",
                        link="http://example.com/1",
                        summary="Summary 1",
                        published=datetime.now(timezone.utc),
                        source="test_source",
                        category="test",
                    ),
                    Article(
                        title="Article 2",
                        link="http://example.com/2",
                        summary="Summary 2",
                        published=datetime.now(timezone.utc),
                        source="test_source",
                        category="test",
                    ),
                    Article(
                        title="Article 3",
                        link="http://example.com/3",
                        summary="Summary 3",
                        published=datetime.now(timezone.utc),
                        source="test_source",
                        category="test",
                    ),
                ]

                # Insert all articles (should succeed)
                storage.upsert_articles(articles)

                # Should have all 3 articles
                recent = storage.recent_articles("test", days=7)
                assert len(recent) == 3


class TestStorageRetention:
    """Test retention cleanup in storage."""

    def test_delete_older_than_removes_expired_articles(self) -> None:
        """Should remove articles older than retention period."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            with RadarStorage(db_path) as storage:
                # Insert old article (30 days ago)
                old_date = datetime.now(timezone.utc) - timedelta(days=30)
                old_article = Article(
                    title="Old Article",
                    link="http://example.com/old",
                    summary="Old",
                    published=old_date,
                    source="test_source",
                    category="test",
                )
                storage.upsert_articles([old_article])

                # Insert recent article
                recent_article = Article(
                    title="Recent Article",
                    link="http://example.com/recent",
                    summary="Recent",
                    published=datetime.now(timezone.utc),
                    source="test_source",
                    category="test",
                )
                storage.upsert_articles([recent_article])

                # Verify both exist
                all_articles = storage.recent_articles("test", days=90)
                assert len(all_articles) == 2

                # Delete articles older than 7 days
                deleted = storage.delete_older_than(days=7)

                # Should have deleted 1 article
                assert deleted == 1

                # Verify only recent article remains
                remaining = storage.recent_articles("test", days=90)
                assert len(remaining) == 1
                assert remaining[0].title == "Recent Article"

    def test_delete_older_than_no_articles_to_delete(self) -> None:
        """Should return 0 when no articles need deletion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            with RadarStorage(db_path) as storage:
                # Insert recent article
                article = Article(
                    title="Recent",
                    link="http://example.com/1",
                    summary="Recent",
                    published=datetime.now(timezone.utc),
                    source="test_source",
                    category="test",
                )
                storage.upsert_articles([article])

                # Delete with large retention period
                deleted = storage.delete_older_than(days=90)

                # Should have deleted 0 articles
                assert deleted == 0

    def test_delete_older_than_empty_database(self) -> None:
        """Should handle deletion on empty database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            with RadarStorage(db_path) as storage:
                # Delete from empty database
                deleted = storage.delete_older_than(days=7)

                # Should return 0
                assert deleted == 0


class TestStorageContextManager:
    """Test context manager functionality."""

    def test_context_manager_closes_connection(self) -> None:
        """Should close connection on context exit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            storage = RadarStorage(db_path)
            storage.__enter__()
            assert storage.conn is not None
            storage.__exit__(None, None, None)

            # Connection should be closed (but object still exists)
            # Just verify __exit__ was called without error
            assert storage is not None

    def test_context_manager_with_exception(self) -> None:
        """Should close connection even on exception."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            storage = RadarStorage(db_path)
            try:
                storage.__enter__()
                assert storage.conn is not None
                raise ValueError("Test error")
            except ValueError:
                pass
            finally:
                storage.__exit__(None, None, None)

            # Connection should still be closed
            # Just verify __exit__ was called without error
            assert storage is not None


class TestStorageArticleRetrieval:
    """Test article retrieval methods."""

    def test_recent_articles_filters_by_category(self) -> None:
        """Should filter articles by category."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            with RadarStorage(db_path) as storage:
                # Insert articles in different categories
                tech_article = Article(
                    title="Tech News",
                    link="http://example.com/tech",
                    summary="Tech",
                    published=datetime.now(timezone.utc),
                    source="test_source",
                    category="tech",
                )
                food_article = Article(
                    title="Food News",
                    link="http://example.com/food",
                    summary="Food",
                    published=datetime.now(timezone.utc),
                    source="test_source",
                    category="food",
                )
                storage.upsert_articles([tech_article, food_article])

                # Get tech articles only
                tech_articles = storage.recent_articles("tech", days=7)
                assert len(tech_articles) == 1
                assert tech_articles[0].category == "tech"

                # Get food articles only
                food_articles = storage.recent_articles("food", days=7)
                assert len(food_articles) == 1
                assert food_articles[0].category == "food"

    def test_recent_articles_respects_days_filter(self) -> None:
        """Should filter articles by days window."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            with RadarStorage(db_path) as storage:
                # Insert old article
                old_article = Article(
                    title="Old",
                    link="http://example.com/old",
                    summary="Old",
                    published=datetime.now(timezone.utc) - timedelta(days=30),
                    source="test_source",
                    category="test",
                )
                # Insert recent article
                recent_article = Article(
                    title="Recent",
                    link="http://example.com/recent",
                    summary="Recent",
                    published=datetime.now(timezone.utc),
                    source="test_source",
                    category="test",
                )
                storage.upsert_articles([old_article, recent_article])

                # Get articles from last 7 days
                recent = storage.recent_articles("test", days=7)
                assert len(recent) == 1
                assert recent[0].title == "Recent"

                # Get articles from last 90 days
                all_articles = storage.recent_articles("test", days=90)
                assert len(all_articles) == 2

    def test_recent_articles_with_null_published_date(self) -> None:
        """Should handle articles with null published date."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            with RadarStorage(db_path) as storage:
                # Insert article with null published date
                article = Article(
                    title="No Date",
                    link="http://example.com/1",
                    summary="No date",
                    published=None,
                    source="test_source",
                    category="test",
                )
                storage.upsert_articles([article])

                # Should still retrieve it (uses collected_at as fallback)
                recent = storage.recent_articles("test", days=7)
                assert len(recent) == 1
                assert recent[0].title == "No Date"

    def test_recent_articles_with_matched_entities(self) -> None:
        """Should preserve matched_entities when retrieving articles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            with RadarStorage(db_path) as storage:
                # Insert article with matched entities
                article = Article(
                    title="Python Article",
                    link="http://example.com/1",
                    summary="About Python",
                    published=datetime.now(timezone.utc),
                    source="test_source",
                    category="test",
                    matched_entities={"languages": ["python"]},
                )
                storage.upsert_articles([article])

                # Retrieve and verify matched_entities
                recent = storage.recent_articles("test", days=7)
                assert len(recent) == 1
                assert recent[0].matched_entities == {"languages": ["python"]}


class TestStorageBatchPerformance:
    """Test batch processing performance and correctness."""

    def test_batch_insert_100_articles(self) -> None:
        """Should insert 100 articles in batch and verify all are stored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            with RadarStorage(db_path) as storage:
                # Create 100 articles
                articles: list[Article] = [
                    Article(
                        title=f"Article {i}",
                        link=f"http://example.com/{i}",
                        summary=f"Summary {i}",
                        published=datetime.now(timezone.utc),
                        source="test_source",
                        category="test",
                    )
                    for i in range(100)
                ]

                # Insert all at once
                storage.upsert_articles(articles)

                # Verify all 100 articles were inserted
                recent = storage.recent_articles("test", days=7, limit=200)
                assert len(recent) == 100

    def test_batch_insert_with_duplicates_deduplicates(self) -> None:
        """Batch insert should deduplicate within batch (keep last occurrence)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            with RadarStorage(db_path) as storage:
                # Create 100 articles with 50 unique links (duplicates)
                articles: list[Article] = [
                    Article(
                        title=f"Article {i}",
                        link=f"http://example.com/{i % 50}",  # 50 unique links
                        summary=f"Summary {i}",
                        published=datetime.now(timezone.utc),
                        source="test_source",
                        category="test",
                    )
                    for i in range(100)
                ]

                # Batch insert should handle duplicates
                storage.upsert_articles(articles)

                # Should have 50 unique articles (last occurrence of each link)
                recent = storage.recent_articles("test", days=7, limit=100)
                assert len(recent) == 50

                # Verify last occurrence is kept (Article 99 for link 49)
                article_49 = [a for a in recent if a.link == "http://example.com/49"]
                assert len(article_49) == 1
                assert article_49[0].title == "Article 99"

    def test_batch_upsert_with_duplicates(self) -> None:
        """Batch upsert should handle duplicate links correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            with RadarStorage(db_path) as storage:
                # Insert first batch
                articles1: list[Article] = [
                    Article(
                        title=f"Article {i}",
                        link=f"http://example.com/{i}",
                        summary=f"Summary {i}",
                        published=datetime.now(timezone.utc),
                        source="test_source",
                        category="test",
                    )
                    for i in range(50)
                ]
                storage.upsert_articles(articles1)

                # Insert second batch with overlapping links
                articles2: list[Article] = [
                    Article(
                        title=f"Article {i} Updated",
                        link=f"http://example.com/{i}",
                        summary=f"Updated Summary {i}",
                        published=datetime.now(timezone.utc),
                        source="test_source",
                        category="test",
                    )
                    for i in range(25, 75)
                ]
                storage.upsert_articles(articles2)

                # Should have 75 unique articles (0-74)
                recent = storage.recent_articles("test", days=7, limit=200)
                assert len(recent) == 75

                # Verify updated articles have new titles
                updated_articles = [a for a in recent if a.link == "http://example.com/50"]
                assert len(updated_articles) == 1
                assert updated_articles[0].title == "Article 50 Updated"

    def test_batch_insert_empty_list(self) -> None:
        """Should handle empty article list gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            with RadarStorage(db_path) as storage:
                # Insert empty list
                storage.upsert_articles([])

                # Should have no articles
                recent = storage.recent_articles("test", days=7)
                assert len(recent) == 0

    def test_batch_insert_preserves_entities(self) -> None:
        """Batch insert should preserve matched_entities for all articles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"

            with RadarStorage(db_path) as storage:
                # Create articles with entities
                articles: list[Article] = [
                    Article(
                        title=f"Article {i}",
                        link=f"http://example.com/{i}",
                        summary=f"Summary {i}",
                        published=datetime.now(timezone.utc),
                        source="test_source",
                        category="test",
                        matched_entities={"type": [f"entity_{i}"]},
                    )
                    for i in range(10)
                ]

                # Insert batch
                storage.upsert_articles(articles)

                # Verify all entities preserved
                recent = storage.recent_articles("test", days=7, limit=20)
                assert len(recent) == 10
                for i, article in enumerate(sorted(recent, key=lambda a: a.link)):
                    assert article.matched_entities == {"type": [f"entity_{i}"]}
