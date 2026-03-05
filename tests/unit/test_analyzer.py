from __future__ import annotations

from datetime import datetime, timezone

import pytest

from radar.analyzer import apply_entity_rules
from radar.models import Article, EntityDefinition


class TestApplyEntityRules:
    """Test entity matching logic in analyzer."""

    def test_apply_entity_rules_matches_single_keyword_in_title(self) -> None:
        """Should match keyword found in article title."""
        articles = [
            Article(
                title="Python programming guide",
                link="http://example.com/1",
                summary="Learn Python basics",
                published=datetime.now(timezone.utc),
                source="test_source",
                category="tech",
            )
        ]
        entities = [
            EntityDefinition(
                name="python",
                display_name="Python",
                keywords=["python"],
            )
        ]

        result = apply_entity_rules(articles, entities)

        assert len(result) == 1
        assert "python" in result[0].matched_entities
        assert result[0].matched_entities["python"] == ["python"]

    def test_apply_entity_rules_matches_keyword_in_summary(self) -> None:
        """Should match keyword found in article summary."""
        articles = [
            Article(
                title="Web Development",
                link="http://example.com/1",
                summary="JavaScript is essential for web development",
                published=datetime.now(timezone.utc),
                source="test_source",
                category="tech",
            )
        ]
        entities = [
            EntityDefinition(
                name="javascript",
                display_name="JavaScript",
                keywords=["javascript"],
            )
        ]

        result = apply_entity_rules(articles, entities)

        assert len(result) == 1
        assert "javascript" in result[0].matched_entities
        assert result[0].matched_entities["javascript"] == ["javascript"]

    def test_apply_entity_rules_case_insensitive_matching(self) -> None:
        """Should match keywords case-insensitively."""
        articles = [
            Article(
                title="PYTHON Programming",
                link="http://example.com/1",
                summary="Learn Python basics",
                published=datetime.now(timezone.utc),
                source="test_source",
                category="tech",
            )
        ]
        entities = [
            EntityDefinition(
                name="python",
                display_name="Python",
                keywords=["python"],
            )
        ]

        result = apply_entity_rules(articles, entities)

        assert len(result) == 1
        assert "python" in result[0].matched_entities
        assert result[0].matched_entities["python"] == ["python"]

    def test_apply_entity_rules_multiple_keywords_same_entity(self) -> None:
        """Should match multiple keywords for same entity."""
        articles = [
            Article(
                title="Python and JavaScript guide",
                link="http://example.com/1",
                summary="Learn web development",
                published=datetime.now(timezone.utc),
                source="test_source",
                category="tech",
            )
        ]
        entities = [
            EntityDefinition(
                name="languages",
                display_name="Languages",
                keywords=["python", "javascript"],
            )
        ]

        result = apply_entity_rules(articles, entities)

        assert len(result) == 1
        assert "languages" in result[0].matched_entities
        assert set(result[0].matched_entities["languages"]) == {"python", "javascript"}

    def test_apply_entity_rules_multiple_entities(self) -> None:
        """Should match multiple different entities."""
        articles = [
            Article(
                title="Python and JavaScript",
                link="http://example.com/1",
                summary="Web development languages",
                published=datetime.now(timezone.utc),
                source="test_source",
                category="tech",
            )
        ]
        entities = [
            EntityDefinition(
                name="python",
                display_name="Python",
                keywords=["python"],
            ),
            EntityDefinition(
                name="javascript",
                display_name="JavaScript",
                keywords=["javascript"],
            ),
        ]

        result = apply_entity_rules(articles, entities)

        assert len(result) == 1
        assert "python" in result[0].matched_entities
        assert "javascript" in result[0].matched_entities

    def test_apply_entity_rules_no_matches(self) -> None:
        """Should return empty matched_entities when no keywords match."""
        articles = [
            Article(
                title="Cooking guide",
                link="http://example.com/1",
                summary="Learn to cook",
                published=datetime.now(timezone.utc),
                source="test_source",
                category="food",
            )
        ]
        entities = [
            EntityDefinition(
                name="python",
                display_name="Python",
                keywords=["python"],
            )
        ]

        result = apply_entity_rules(articles, entities)

        assert len(result) == 1
        assert result[0].matched_entities == {}

    def test_apply_entity_rules_empty_articles(self) -> None:
        """Should handle empty article list."""
        articles: list[Article] = []
        entities = [
            EntityDefinition(
                name="python",
                display_name="Python",
                keywords=["python"],
            )
        ]

        result = apply_entity_rules(articles, entities)

        assert result == []

    def test_apply_entity_rules_empty_entities(self) -> None:
        """Should handle empty entity list."""
        articles = [
            Article(
                title="Python guide",
                link="http://example.com/1",
                summary="Learn Python",
                published=datetime.now(timezone.utc),
                source="test_source",
                category="tech",
            )
        ]
        entities: list[EntityDefinition] = []

        result = apply_entity_rules(articles, entities)

        assert len(result) == 1
        assert result[0].matched_entities == {}

    def test_apply_entity_rules_empty_keywords_in_entity(self) -> None:
        """Should skip entities with empty keywords."""
        articles = [
            Article(
                title="Python guide",
                link="http://example.com/1",
                summary="Learn Python",
                published=datetime.now(timezone.utc),
                source="test_source",
                category="tech",
            )
        ]
        entities = [
            EntityDefinition(
                name="empty",
                display_name="Empty",
                keywords=[],
            )
        ]

        result = apply_entity_rules(articles, entities)

        assert len(result) == 1
        assert result[0].matched_entities == {}

    def test_apply_entity_rules_keyword_substring_match(self) -> None:
        """Should match keywords as substrings."""
        articles = [
            Article(
                title="Pythonic code",
                link="http://example.com/1",
                summary="Write pythonic code",
                published=datetime.now(timezone.utc),
                source="test_source",
                category="tech",
            )
        ]
        entities = [
            EntityDefinition(
                name="python",
                display_name="Python",
                keywords=["python"],
            )
        ]

        result = apply_entity_rules(articles, entities)

        assert len(result) == 1
        assert "python" in result[0].matched_entities
        assert result[0].matched_entities["python"] == ["python"]

    def test_apply_entity_rules_multiple_articles(self) -> None:
        """Should process multiple articles independently."""
        articles = [
            Article(
                title="Python guide",
                link="http://example.com/1",
                summary="Learn Python",
                published=datetime.now(timezone.utc),
                source="test_source",
                category="tech",
            ),
            Article(
                title="JavaScript tutorial",
                link="http://example.com/2",
                summary="Learn JavaScript",
                published=datetime.now(timezone.utc),
                source="test_source",
                category="tech",
            ),
        ]
        entities = [
            EntityDefinition(
                name="python",
                display_name="Python",
                keywords=["python"],
            ),
            EntityDefinition(
                name="javascript",
                display_name="JavaScript",
                keywords=["javascript"],
            ),
        ]

        result = apply_entity_rules(articles, entities)

        assert len(result) == 2
        assert "python" in result[0].matched_entities
        assert "javascript" in result[1].matched_entities
        assert "javascript" not in result[0].matched_entities
        assert "python" not in result[1].matched_entities

    def test_apply_entity_rules_whitespace_keywords(self) -> None:
        """Should skip empty/whitespace-only keywords."""
        articles = [
            Article(
                title="Python guide",
                link="http://example.com/1",
                summary="Learn Python",
                published=datetime.now(timezone.utc),
                source="test_source",
                category="tech",
            )
        ]
        entities = [
            EntityDefinition(
                name="test",
                display_name="Test",
                keywords=["", "   ", "python"],
            )
        ]

        result = apply_entity_rules(articles, entities)

        assert len(result) == 1
        assert "test" in result[0].matched_entities
        assert result[0].matched_entities["test"] == ["python"]

    def test_apply_entity_rules_preserves_article_data(self) -> None:
        """Should preserve original article data after analysis."""
        original_article = Article(
            title="Python guide",
            link="http://example.com/1",
            summary="Learn Python",
            published=datetime.now(timezone.utc),
            source="test_source",
            category="tech",
        )
        articles = [original_article]
        entities = [
            EntityDefinition(
                name="python",
                display_name="Python",
                keywords=["python"],
            )
        ]

        result = apply_entity_rules(articles, entities)

        assert result[0].title == original_article.title
        assert result[0].link == original_article.link
        assert result[0].summary == original_article.summary
        assert result[0].source == original_article.source
        assert result[0].category == original_article.category

    def test_apply_entity_rules_duplicate_keywords_in_entity(self) -> None:
        """Should handle duplicate keywords in entity definition."""
        articles = [
            Article(
                title="Python Python guide",
                link="http://example.com/1",
                summary="Learn Python",
                published=datetime.now(timezone.utc),
                source="test_source",
                category="tech",
            )
        ]
        entities = [
            EntityDefinition(
                name="python",
                display_name="Python",
                keywords=["python", "python"],
            )
        ]

        result = apply_entity_rules(articles, entities)

        assert len(result) == 1
        assert "python" in result[0].matched_entities
        # Both occurrences should be counted
        assert result[0].matched_entities["python"].count("python") == 2
