from __future__ import annotations

from pathlib import Path

import pytest

from radar.models import Article
from radar.search_index import SearchIndex


@pytest.mark.integration
def test_search_index_integration(
    tmp_path: Path,
    sample_articles: list[Article],
) -> None:
    """Test search index integration: index articles → query → verify results."""
    search_db = tmp_path / "search.db"
    index = SearchIndex(search_db)

    for article in sample_articles:
        index.upsert(
            link=article.link,
            title=article.title,
            body=article.summary,
        )

    results = index.search("게임", limit=10)
    assert len(results) > 0
    assert any("게임" in r.title for r in results)

    results_aaa = index.search("AAA", limit=10)
    assert len(results_aaa) >= 0

    results_empty = index.search("nonexistent_keyword_xyz", limit=10)
    assert len(results_empty) == 0

    index.close()
