from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path

from radar.models import Article, CategoryConfig
from radar.reporter import _count_entities, generate_report


class TestGenerateReport:
    """Test HTML report generation."""

    def test_generate_report_creates_output_file(self) -> None:
        """Should create HTML report file at specified path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            category = CategoryConfig(
                category_name="test",
                display_name="Test Category",
                sources=[],
                entities=[],
            )
            articles: list[Article] = []
            stats = {"sources": 0, "collected": 0, "matched": 0, "window_days": 7}

            result = generate_report(
                category=category,
                articles=articles,
                output_path=output_path,
                stats=stats,
            )

            assert result == output_path
            assert output_path.exists()
            assert output_path.is_file()

    def test_generate_report_creates_parent_directories(self) -> None:
        """Should create parent directories if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "dirs" / "report.html"
            category = CategoryConfig(
                category_name="test",
                display_name="Test Category",
                sources=[],
                entities=[],
            )
            articles: list[Article] = []
            stats = {"sources": 0, "collected": 0, "matched": 0, "window_days": 7}

            _ = generate_report(
                category=category,
                articles=articles,
                output_path=output_path,
                stats=stats,
            )

            assert output_path.exists()
            assert output_path.parent.exists()

    def test_generate_report_contains_category_name(self) -> None:
        """Should include category display name in HTML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            category = CategoryConfig(
                category_name="tech",
                display_name="Technology News",
                sources=[],
                entities=[],
            )
            articles: list[Article] = []
            stats = {"sources": 0, "collected": 0, "matched": 0, "window_days": 7}

            generate_report(
                category=category,
                articles=articles,
                output_path=output_path,
                stats=stats,
            )

            content = output_path.read_text(encoding="utf-8")
            assert "Technology News" in content

    def test_generate_report_contains_stats(self) -> None:
        """Should include statistics in HTML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            category = CategoryConfig(
                category_name="test",
                display_name="Test",
                sources=[],
                entities=[],
            )
            articles: list[Article] = []
            stats = {"sources": 5, "collected": 42, "matched": 23, "window_days": 7}

            generate_report(
                category=category,
                articles=articles,
                output_path=output_path,
                stats=stats,
            )

            content = output_path.read_text(encoding="utf-8")
            assert "5" in content  # sources
            assert "42" in content  # collected
            assert "23" in content  # matched
            assert "7" in content  # window_days

    def test_generate_report_contains_articles(self) -> None:
        """Should include article titles in HTML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            category = CategoryConfig(
                category_name="test",
                display_name="Test",
                sources=[],
                entities=[],
            )
            articles = [
                Article(
                    title="Breaking News",
                    link="http://example.com/1",
                    summary="Important update",
                    published=datetime.now(UTC),
                    source="test_source",
                    category="test",
                )
            ]
            stats = {"sources": 1, "collected": 1, "matched": 0, "window_days": 7}

            generate_report(
                category=category,
                articles=articles,
                output_path=output_path,
                stats=stats,
            )

            content = output_path.read_text(encoding="utf-8")
            assert "Breaking News" in content

    def test_generate_report_contains_article_links(self) -> None:
        """Should include article links in HTML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            category = CategoryConfig(
                category_name="test",
                display_name="Test",
                sources=[],
                entities=[],
            )
            articles = [
                Article(
                    title="Article",
                    link="http://example.com/article",
                    summary="Summary",
                    published=datetime.now(UTC),
                    source="test_source",
                    category="test",
                )
            ]
            stats = {"sources": 1, "collected": 1, "matched": 0, "window_days": 7}

            generate_report(
                category=category,
                articles=articles,
                output_path=output_path,
                stats=stats,
            )

            content = output_path.read_text(encoding="utf-8")
            assert "http://example.com/article" in content

    def test_generate_report_contains_article_summary(self) -> None:
        """Should include article summary in HTML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            category = CategoryConfig(
                category_name="test",
                display_name="Test",
                sources=[],
                entities=[],
            )
            articles = [
                Article(
                    title="Article",
                    link="http://example.com/1",
                    summary="This is a test summary",
                    published=datetime.now(UTC),
                    source="test_source",
                    category="test",
                )
            ]
            stats = {"sources": 1, "collected": 1, "matched": 0, "window_days": 7}

            generate_report(
                category=category,
                articles=articles,
                output_path=output_path,
                stats=stats,
            )

            content = output_path.read_text(encoding="utf-8")
            assert "This is a test summary" in content

    def test_generate_report_contains_source_name(self) -> None:
        """Should include article source name in HTML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            category = CategoryConfig(
                category_name="test",
                display_name="Test",
                sources=[],
                entities=[],
            )
            articles = [
                Article(
                    title="Article",
                    link="http://example.com/1",
                    summary="Summary",
                    published=datetime.now(UTC),
                    source="BBC News",
                    category="test",
                )
            ]
            stats = {"sources": 1, "collected": 1, "matched": 0, "window_days": 7}

            generate_report(
                category=category,
                articles=articles,
                output_path=output_path,
                stats=stats,
            )

            content = output_path.read_text(encoding="utf-8")
            assert "BBC News" in content

    def test_generate_report_contains_published_date(self) -> None:
        """Should include article published date in HTML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            category = CategoryConfig(
                category_name="test",
                display_name="Test",
                sources=[],
                entities=[],
            )
            pub_date = datetime(2024, 3, 15, 10, 30, 0, tzinfo=UTC)
            articles = [
                Article(
                    title="Article",
                    link="http://example.com/1",
                    summary="Summary",
                    published=pub_date,
                    source="test_source",
                    category="test",
                )
            ]
            stats = {"sources": 1, "collected": 1, "matched": 0, "window_days": 7}

            generate_report(
                category=category,
                articles=articles,
                output_path=output_path,
                stats=stats,
            )

            content = output_path.read_text(encoding="utf-8")
            assert "2024-03-15" in content

    def test_generate_report_with_errors(self) -> None:
        """Should include error messages in HTML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            category = CategoryConfig(
                category_name="test",
                display_name="Test",
                sources=[],
                entities=[],
            )
            articles: list[Article] = []
            stats = {"sources": 0, "collected": 0, "matched": 0, "window_days": 7}
            errors = ["Connection timeout", "Invalid feed format"]

            generate_report(
                category=category,
                articles=articles,
                output_path=output_path,
                stats=stats,
                errors=errors,
            )

            content = output_path.read_text(encoding="utf-8")
            assert "Connection timeout" in content
            assert "Invalid feed format" in content

    def test_generate_report_with_matched_entities(self) -> None:
        """Should display matched entities in HTML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            category = CategoryConfig(
                category_name="test",
                display_name="Test",
                sources=[],
                entities=[],
            )
            articles = [
                Article(
                    title="Python and JavaScript",
                    link="http://example.com/1",
                    summary="Languages",
                    published=datetime.now(UTC),
                    source="test_source",
                    category="test",
                    matched_entities={"languages": ["python", "javascript"]},
                )
            ]
            stats = {"sources": 1, "collected": 1, "matched": 1, "window_days": 7}

            generate_report(
                category=category,
                articles=articles,
                output_path=output_path,
                stats=stats,
            )

            content = output_path.read_text(encoding="utf-8")
            assert "languages" in content
            assert "python" in content
            assert "javascript" in content

    def test_generate_report_empty_articles_list(self) -> None:
        """Should handle empty articles list gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            category = CategoryConfig(
                category_name="test",
                display_name="Test",
                sources=[],
                entities=[],
            )
            articles: list[Article] = []
            stats = {"sources": 0, "collected": 0, "matched": 0, "window_days": 7}

            result = generate_report(
                category=category,
                articles=articles,
                output_path=output_path,
                stats=stats,
            )

            assert result.exists()
            content = output_path.read_text(encoding="utf-8")
            assert "No articles" in content

    def test_generate_report_html_is_valid(self) -> None:
        """Should generate valid HTML structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            category = CategoryConfig(
                category_name="test",
                display_name="Test",
                sources=[],
                entities=[],
            )
            articles: list[Article] = []
            stats = {"sources": 0, "collected": 0, "matched": 0, "window_days": 7}

            generate_report(
                category=category,
                articles=articles,
                output_path=output_path,
                stats=stats,
            )

            content = output_path.read_text(encoding="utf-8")
            assert "<!doctype html>" in content
            assert "<html" in content
            assert "</html>" in content
            assert "<head>" in content
            assert "</head>" in content
            assert "<body>" in content
            assert "</body>" in content

    def test_generate_report_includes_generated_timestamp(self) -> None:
        """Should include generation timestamp in HTML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            category = CategoryConfig(
                category_name="test",
                display_name="Test",
                sources=[],
                entities=[],
            )
            articles: list[Article] = []
            stats = {"sources": 0, "collected": 0, "matched": 0, "window_days": 7}

            generate_report(
                category=category,
                articles=articles,
                output_path=output_path,
                stats=stats,
            )

            content = output_path.read_text(encoding="utf-8")
            assert "Generated at" in content
            assert "UTC" in content


class TestCountEntities:
    """Test entity counting logic."""

    def test_count_entities_single_article_single_entity(self) -> None:
        """Should count single entity in single article."""
        articles = [
            Article(
                title="Test",
                link="http://example.com/1",
                summary="Test",
                published=datetime.now(UTC),
                source="test",
                category="test",
                matched_entities={"python": ["python"]},
            )
        ]

        result = _count_entities(articles)

        assert result["python"] == 1

    def test_count_entities_multiple_keywords_same_entity(self) -> None:
        """Should count multiple keywords for same entity."""
        articles = [
            Article(
                title="Test",
                link="http://example.com/1",
                summary="Test",
                published=datetime.now(UTC),
                source="test",
                category="test",
                matched_entities={"languages": ["python", "javascript"]},
            )
        ]

        result = _count_entities(articles)

        assert result["languages"] == 2

    def test_count_entities_multiple_articles(self) -> None:
        """Should aggregate counts across articles."""
        articles = [
            Article(
                title="Test 1",
                link="http://example.com/1",
                summary="Test",
                published=datetime.now(UTC),
                source="test",
                category="test",
                matched_entities={"python": ["python"]},
            ),
            Article(
                title="Test 2",
                link="http://example.com/2",
                summary="Test",
                published=datetime.now(UTC),
                source="test",
                category="test",
                matched_entities={"python": ["python"]},
            ),
        ]

        result = _count_entities(articles)

        assert result["python"] == 2

    def test_count_entities_multiple_entities(self) -> None:
        """Should count multiple different entities."""
        articles = [
            Article(
                title="Test",
                link="http://example.com/1",
                summary="Test",
                published=datetime.now(UTC),
                source="test",
                category="test",
                matched_entities={"python": ["python"], "javascript": ["javascript"]},
            )
        ]

        result = _count_entities(articles)

        assert result["python"] == 1
        assert result["javascript"] == 1

    def test_count_entities_empty_articles(self) -> None:
        """Should return empty counter for empty articles."""
        articles: list[Article] = []

        result = _count_entities(articles)

        assert len(result) == 0

    def test_count_entities_no_matched_entities(self) -> None:
        """Should handle articles with no matched entities."""
        articles = [
            Article(
                title="Test",
                link="http://example.com/1",
                summary="Test",
                published=datetime.now(UTC),
                source="test",
                category="test",
                matched_entities={},
            )
        ]

        result = _count_entities(articles)

        assert len(result) == 0

    def test_count_entities_none_matched_entities(self) -> None:
        """Should handle articles with None matched_entities."""
        article = Article(
            title="Test",
            link="http://example.com/1",
            summary="Test",
            published=datetime.now(UTC),
            source="test",
            category="test",
        )
        article.matched_entities = None  # type: ignore
        articles = [article]

        result = _count_entities(articles)

        assert len(result) == 0
