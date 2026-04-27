from __future__ import annotations

import json
from pathlib import Path

import pytest

from radar.models import Article, EntityDefinition
from radar.reporter import generate_report


def _apply_entity_rules_py39(
    articles: list[Article], entities: list[EntityDefinition]
) -> list[Article]:
    """Apply entity rules (Python 3.9 compatible version)."""
    analyzed: list[Article] = []
    lowered_entities = [
        EntityDefinition(
            name=e.name,
            display_name=e.display_name,
            keywords=[kw.lower() for kw in e.keywords],
        )
        for e in entities
    ]

    for article in articles:
        haystack = f"{article.title}\n{article.summary}".lower()
        matches: dict[str, list[str]] = {}
        for entity, lowered_entity in zip(entities, lowered_entities, strict=False):
            hit_keywords = [kw for kw in lowered_entity.keywords if kw and kw in haystack]
            if hit_keywords:
                matches[entity.name] = hit_keywords
        article.matched_entities = matches
        analyzed.append(article)

    return analyzed


@pytest.mark.integration
def test_report_generation(
    tmp_path: Path,
    sample_articles: list[Article],
    sample_entities: list[EntityDefinition],
    sample_config,
) -> None:
    """Test report generation: generate HTML → verify file exists + contains expected content."""
    analyzed = _apply_entity_rules_py39(sample_articles, sample_entities)

    output_path = tmp_path / "report.html"
    stats = {"total_articles": len(analyzed), "sources": 1}

    result = generate_report(
        category=sample_config,
        articles=analyzed,
        output_path=output_path,
        stats=stats,
    )

    assert result.exists()
    assert result.suffix == ".html"

    content = result.read_text(encoding="utf-8")
    assert "게임" in content
    assert "새로운 AAA 게임" in content
    assert "FPS 게임" in content

    summary_path = next(
        tmp_path.glob("game_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_summary.json")
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["ontology"]["repo"] == "GameRadar"
    assert summary["ontology"]["ontology_version"] == "0.1.0"
    assert "game.store_ranking" in summary["ontology"]["event_model_ids"]
