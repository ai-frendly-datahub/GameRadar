from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from radar.models import (
    Article,
    CategoryConfig,
    EntityDefinition,
    RadarSettings,
    Source,
)


class TestSource:
    """Test Source data model."""

    def test_source_creation(self) -> None:
        """Should create Source with required fields."""
        source = Source(
            name="BBC News",
            type="rss",
            url="http://example.com/feed",
        )

        assert source.name == "BBC News"
        assert source.type == "rss"
        assert source.url == "http://example.com/feed"

    def test_source_with_different_types(self) -> None:
        """Should support different source types."""
        rss_source = Source(name="RSS", type="rss", url="http://example.com")
        html_source = Source(name="HTML", type="html", url="http://example.com")
        api_source = Source(name="API", type="api", url="http://example.com")

        assert rss_source.type == "rss"
        assert html_source.type == "html"
        assert api_source.type == "api"

    def test_source_equality(self) -> None:
        """Should compare sources by value."""
        source1 = Source(name="BBC", type="rss", url="http://example.com")
        source2 = Source(name="BBC", type="rss", url="http://example.com")

        assert source1 == source2

    def test_source_inequality(self) -> None:
        """Should distinguish different sources."""
        source1 = Source(name="BBC", type="rss", url="http://example.com")
        source2 = Source(name="CNN", type="rss", url="http://example.com")

        assert source1 != source2


class TestEntityDefinition:
    """Test EntityDefinition data model."""

    def test_entity_definition_creation(self) -> None:
        """Should create EntityDefinition with required fields."""
        entity = EntityDefinition(
            name="python",
            display_name="Python",
            keywords=["python", "py"],
        )

        assert entity.name == "python"
        assert entity.display_name == "Python"
        assert entity.keywords == ["python", "py"]

    def test_entity_definition_empty_keywords(self) -> None:
        """Should support empty keywords list."""
        entity = EntityDefinition(
            name="test",
            display_name="Test",
            keywords=[],
        )

        assert entity.keywords == []

    def test_entity_definition_single_keyword(self) -> None:
        """Should support single keyword."""
        entity = EntityDefinition(
            name="python",
            display_name="Python",
            keywords=["python"],
        )

        assert len(entity.keywords) == 1
        assert entity.keywords[0] == "python"

    def test_entity_definition_many_keywords(self) -> None:
        """Should support many keywords."""
        keywords = ["python", "py", "python3", "python2", "cpython"]
        entity = EntityDefinition(
            name="python",
            display_name="Python",
            keywords=keywords,
        )

        assert entity.keywords == keywords

    def test_entity_definition_equality(self) -> None:
        """Should compare entities by value."""
        entity1 = EntityDefinition(
            name="python",
            display_name="Python",
            keywords=["python"],
        )
        entity2 = EntityDefinition(
            name="python",
            display_name="Python",
            keywords=["python"],
        )

        assert entity1 == entity2

    def test_entity_definition_inequality_name(self) -> None:
        """Should distinguish entities with different names."""
        entity1 = EntityDefinition(
            name="python",
            display_name="Python",
            keywords=["python"],
        )
        entity2 = EntityDefinition(
            name="javascript",
            display_name="JavaScript",
            keywords=["javascript"],
        )

        assert entity1 != entity2

    def test_entity_definition_inequality_keywords(self) -> None:
        """Should distinguish entities with different keywords."""
        entity1 = EntityDefinition(
            name="python",
            display_name="Python",
            keywords=["python"],
        )
        entity2 = EntityDefinition(
            name="python",
            display_name="Python",
            keywords=["python", "py"],
        )

        assert entity1 != entity2


class TestArticle:
    """Test Article data model."""

    def test_article_creation(self) -> None:
        """Should create Article with required fields."""
        pub_date = datetime.now(timezone.utc)
        article = Article(
            title="Breaking News",
            link="http://example.com/article",
            summary="Important update",
            published=pub_date,
            source="BBC News",
            category="tech",
        )

        assert article.title == "Breaking News"
        assert article.link == "http://example.com/article"
        assert article.summary == "Important update"
        assert article.published == pub_date
        assert article.source == "BBC News"
        assert article.category == "tech"

    def test_article_default_matched_entities(self) -> None:
        """Should initialize matched_entities as empty dict."""
        article = Article(
            title="Test",
            link="http://example.com",
            summary="Test",
            published=datetime.now(timezone.utc),
            source="test",
            category="test",
        )

        assert article.matched_entities == {}

    def test_article_with_matched_entities(self) -> None:
        """Should support matched_entities initialization."""
        matched = {"python": ["python"], "javascript": ["javascript"]}
        article = Article(
            title="Test",
            link="http://example.com",
            summary="Test",
            published=datetime.now(timezone.utc),
            source="test",
            category="test",
            matched_entities=matched,
        )

        assert article.matched_entities == matched

    def test_article_with_none_published(self) -> None:
        """Should support None published date."""
        article = Article(
            title="Test",
            link="http://example.com",
            summary="Test",
            published=None,
            source="test",
            category="test",
        )

        assert article.published is None

    def test_article_equality(self) -> None:
        """Should compare articles by value."""
        pub_date = datetime(2024, 3, 15, 10, 30, 0, tzinfo=timezone.utc)
        article1 = Article(
            title="Test",
            link="http://example.com",
            summary="Test",
            published=pub_date,
            source="test",
            category="test",
        )
        article2 = Article(
            title="Test",
            link="http://example.com",
            summary="Test",
            published=pub_date,
            source="test",
            category="test",
        )

        assert article1 == article2

    def test_article_inequality_title(self) -> None:
        """Should distinguish articles with different titles."""
        pub_date = datetime.now(timezone.utc)
        article1 = Article(
            title="Title 1",
            link="http://example.com",
            summary="Test",
            published=pub_date,
            source="test",
            category="test",
        )
        article2 = Article(
            title="Title 2",
            link="http://example.com",
            summary="Test",
            published=pub_date,
            source="test",
            category="test",
        )

        assert article1 != article2

    def test_article_inequality_link(self) -> None:
        """Should distinguish articles with different links."""
        pub_date = datetime.now(timezone.utc)
        article1 = Article(
            title="Test",
            link="http://example.com/1",
            summary="Test",
            published=pub_date,
            source="test",
            category="test",
        )
        article2 = Article(
            title="Test",
            link="http://example.com/2",
            summary="Test",
            published=pub_date,
            source="test",
            category="test",
        )

        assert article1 != article2

    def test_article_with_long_summary(self) -> None:
        """Should support long summaries."""
        long_summary = "x" * 10000
        article = Article(
            title="Test",
            link="http://example.com",
            summary=long_summary,
            published=datetime.now(timezone.utc),
            source="test",
            category="test",
        )

        assert len(article.summary) == 10000

    def test_article_with_special_characters(self) -> None:
        """Should support special characters in fields."""
        article = Article(
            title="Test: 한글 & Special <chars>",
            link="http://example.com?param=value&other=123",
            summary="Summary with émojis 🎉 and symbols @#$%",
            published=datetime.now(timezone.utc),
            source="Test/Source",
            category="test",
        )

        assert "한글" in article.title
        assert "🎉" in article.summary
        assert "?" in article.link


class TestCategoryConfig:
    """Test CategoryConfig data model."""

    def test_category_config_creation(self) -> None:
        """Should create CategoryConfig with required fields."""
        sources = [Source(name="BBC", type="rss", url="http://example.com")]
        entities = [
            EntityDefinition(name="python", display_name="Python", keywords=["python"])
        ]
        config = CategoryConfig(
            category_name="tech",
            display_name="Technology",
            sources=sources,
            entities=entities,
        )

        assert config.category_name == "tech"
        assert config.display_name == "Technology"
        assert config.sources == sources
        assert config.entities == entities

    def test_category_config_empty_sources(self) -> None:
        """Should support empty sources list."""
        config = CategoryConfig(
            category_name="tech",
            display_name="Technology",
            sources=[],
            entities=[],
        )

        assert config.sources == []

    def test_category_config_empty_entities(self) -> None:
        """Should support empty entities list."""
        config = CategoryConfig(
            category_name="tech",
            display_name="Technology",
            sources=[],
            entities=[],
        )

        assert config.entities == []

    def test_category_config_multiple_sources(self) -> None:
        """Should support multiple sources."""
        sources = [
            Source(name="BBC", type="rss", url="http://bbc.com"),
            Source(name="CNN", type="rss", url="http://cnn.com"),
            Source(name="Reuters", type="rss", url="http://reuters.com"),
        ]
        config = CategoryConfig(
            category_name="news",
            display_name="News",
            sources=sources,
            entities=[],
        )

        assert len(config.sources) == 3

    def test_category_config_multiple_entities(self) -> None:
        """Should support multiple entities."""
        entities = [
            EntityDefinition(name="python", display_name="Python", keywords=["python"]),
            EntityDefinition(
                name="javascript", display_name="JavaScript", keywords=["javascript"]
            ),
            EntityDefinition(name="rust", display_name="Rust", keywords=["rust"]),
        ]
        config = CategoryConfig(
            category_name="languages",
            display_name="Programming Languages",
            sources=[],
            entities=entities,
        )

        assert len(config.entities) == 3

    def test_category_config_equality(self) -> None:
        """Should compare configs by value."""
        sources = [Source(name="BBC", type="rss", url="http://example.com")]
        entities = [
            EntityDefinition(name="python", display_name="Python", keywords=["python"])
        ]
        config1 = CategoryConfig(
            category_name="tech",
            display_name="Technology",
            sources=sources,
            entities=entities,
        )
        config2 = CategoryConfig(
            category_name="tech",
            display_name="Technology",
            sources=sources,
            entities=entities,
        )

        assert config1 == config2


class TestRadarSettings:
    """Test RadarSettings data model."""

    def test_radar_settings_creation(self) -> None:
        """Should create RadarSettings with required fields."""
        db_path = Path("/tmp/test.duckdb")
        report_dir = Path("/tmp/reports")
        raw_data_dir = Path("/tmp/raw")
        search_db_path = Path("/tmp/search.db")

        settings = RadarSettings(
            database_path=db_path,
            report_dir=report_dir,
            raw_data_dir=raw_data_dir,
            search_db_path=search_db_path,
        )

        assert settings.database_path == db_path
        assert settings.report_dir == report_dir
        assert settings.raw_data_dir == raw_data_dir
        assert settings.search_db_path == search_db_path

    def test_radar_settings_with_relative_paths(self) -> None:
        """Should support relative paths."""
        settings = RadarSettings(
            database_path=Path("data/test.duckdb"),
            report_dir=Path("reports"),
            raw_data_dir=Path("data/raw"),
            search_db_path=Path("data/search.db"),
        )

        assert not settings.database_path.is_absolute()
        assert not settings.report_dir.is_absolute()

    def test_radar_settings_equality(self) -> None:
        """Should compare settings by value."""
        db_path = Path("/tmp/test.duckdb")
        report_dir = Path("/tmp/reports")
        raw_data_dir = Path("/tmp/raw")
        search_db_path = Path("/tmp/search.db")

        settings1 = RadarSettings(
            database_path=db_path,
            report_dir=report_dir,
            raw_data_dir=raw_data_dir,
            search_db_path=search_db_path,
        )
        settings2 = RadarSettings(
            database_path=db_path,
            report_dir=report_dir,
            raw_data_dir=raw_data_dir,
            search_db_path=search_db_path,
        )

        assert settings1 == settings2

    def test_radar_settings_inequality(self) -> None:
        """Should distinguish different settings."""
        settings1 = RadarSettings(
            database_path=Path("/tmp/test1.duckdb"),
            report_dir=Path("/tmp/reports"),
            raw_data_dir=Path("/tmp/raw"),
            search_db_path=Path("/tmp/search.db"),
        )
        settings2 = RadarSettings(
            database_path=Path("/tmp/test2.duckdb"),
            report_dir=Path("/tmp/reports"),
            raw_data_dir=Path("/tmp/raw"),
            search_db_path=Path("/tmp/search.db"),
        )

        assert settings1 != settings2
