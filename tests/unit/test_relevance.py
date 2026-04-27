from __future__ import annotations

from radar.models import Article, Source
from radar.relevance import apply_source_context_entities, filter_relevant_articles


def _article(
    *,
    title: str,
    source: str = "GamesRadar",
    category: str = "game",
    link: str | None = None,
    matched_entities: dict[str, list[str]] | None = None,
) -> Article:
    return Article(
        title=title,
        link=link or f"https://example.com/{title.replace(' ', '-')}",
        summary=title,
        published=None,
        source=source,
        category=category,
        matched_entities=matched_entities or {},
    )


def test_apply_source_context_entities_adds_platform_signal() -> None:
    article = _article(title="Patch notes", source="Steam News", matched_entities={})
    source = Source(
        name="Steam News",
        type="rss",
        url="https://store.steampowered.com/feeds/news.xml",
        content_type="patch_note",
        producer_role="platform",
        info_purpose=["patch", "release"],
    )

    classified = apply_source_context_entities([article], [source])

    assert classified[0].matched_entities["SourceSignal"] == [
        "game_media_context",
        "patch",
        "patch_note",
        "release",
    ]


def test_filter_relevant_articles_excludes_broad_non_game_and_invalid_pages() -> None:
    sources = [
        Source(name="GamesRadar", type="rss", url="https://www.gamesradar.com/rss/"),
        Source(name="Dexerto", type="rss", url="https://www.dexerto.com/feed/"),
        Source(name="Steam News", type="rss", url="https://store.steampowered.com/feeds/news.xml"),
        Source(name="r/PS5", type="reddit", url="https://www.reddit.com/r/PS5/"),
    ]
    articles = [
        _article(
            title="Pokemon Champions launch tips",
            link="https://www.gamesradar.com/games/pokemon/pokemon-champions/",
            matched_entities={"GameTitle": ["pokemon"], "Release": ["launch"]},
        ),
        _article(
            title="New Netflix shows to stream",
            link="https://www.gamesradar.com/entertainment/streaming-services/new-shows/",
            matched_entities={"GameGeneral": ["story"]},
        ),
        _article(
            title="Tech company launches AI Jesus",
            source="Dexerto",
            link="https://www.dexerto.com/entertainment/ai-jesus/",
            matched_entities={},
        ),
        _article(title="Patch notes for Steam", source="Steam News", matched_entities={}),
        _article(title="Is this build viable?", source="r/PS5", matched_entities={}),
        _article(title="404 Not Found", source="Steam News", matched_entities={}),
    ]

    classified = apply_source_context_entities(articles, sources)
    filtered = filter_relevant_articles(classified, sources)

    assert [article.title for article in filtered] == [
        "Pokemon Champions launch tips",
        "Patch notes for Steam",
        "Is this build viable?",
    ]
