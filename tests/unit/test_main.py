from __future__ import annotations

from types import SimpleNamespace

from main import _select_quality_articles
from radar.models import Article, Source


class _Storage:
    def __init__(self, article: Article) -> None:
        self.article = article
        self.calls: list[dict[str, int | str]] = []

    def recent_articles(self, category: str, *, days: int = 7, limit: int = 200):
        self.calls.append({"category": category, "days": days, "limit": limit})
        return [self.article] if days >= 14 and limit >= 1000 else []


def test_select_quality_articles_uses_wider_quality_window() -> None:
    source = Source(
        name="Xbox Wire",
        type="rss",
        url="https://news.xbox.com/en-us/feed/",
        content_type="platform_update",
        info_purpose=["release_schedule"],
    )
    article = Article(
        title="Xbox game pass schedule update",
        link="https://news.xbox.com/en-us/example",
        summary="Game Pass release schedule for Xbox players.",
        published=None,
        source=source.name,
        category="game",
        matched_entities={"Platform": ["xbox"]},
    )
    storage = _Storage(article)
    category_cfg = SimpleNamespace(category_name="game", sources=[source])

    selected = _select_quality_articles(
        storage,
        category_cfg=category_cfg,
        recent_days=1,
        per_source_limit=1,
    )

    assert selected == [article]
    assert storage.calls == [{"category": "game", "days": 14, "limit": 1000}]
