from __future__ import annotations

from collections.abc import Iterable

from .models import Article, Source

OPERATIONAL_EVENT_MODELS = {
    "patch_note",
    "release_schedule",
    "steam_chart",
    "store_ranking",
}
OPERATIONAL_CONTENT_TYPES = {
    "market_report",
    "patch_note",
    "platform_update",
    "release_schedule",
    "store_ranking",
}
OPERATIONAL_PURPOSES = {
    "community_reaction",
    "game_pass",
    "market_analysis",
    "patch",
    "platform_update",
    "release",
    "release_schedule",
    "sale",
    "sales_chart",
    "top_seller",
}
DEDICATED_GAME_SOURCES = {
    "4Gamer",
    "Destructoid",
    "Dot Esports",
    "Esports Insider",
    "Eurogamer",
    "Famitsu",
    "Game Developer",
    "GameSpot",
    "GamesIndustry.biz",
    "IndieGames.com",
    "Nintendo Life",
    "Pocket Gamer",
    "Pure Xbox",
    "Push Square",
    "Rock Paper Shotgun",
    "Steam News",
    "The Esports Observer",
    "VGC",
    "VentureBeat Gaming",
    "Xbox Wire",
    "게임동아",
    "게임메카",
    "게임조선",
    "게임톡",
    "게임포커스",
    "디스이즈게임",
    "루리웹 뉴스",
    "인벤 게임뉴스",
    "인벤 뉴스",
}
BROAD_SOURCE_NAMES = {"Dexerto", "GamesRadar", "Kotaku", "PC Gamer"}
STRONG_ENTITY_NAMES = {
    "BusinessSignal",
    "Esports",
    "GameTitle",
    "Genre",
    "Platform",
    "Release",
    "Studio",
}
GAME_GENERAL_STRONG_TERMS = {
    "achievement",
    "battle royale",
    "boss",
    "character build",
    "co-op",
    "console",
    "controller",
    "dlc",
    "e스포츠",
    "esports",
    "game",
    "game pass",
    "gameplay",
    "games",
    "gaming",
    "gamer",
    "level",
    "loot",
    "mmorpg",
    "multiplayer",
    "patch",
    "pc gaming",
    "player",
    "quest",
    "roblox",
    "steam",
    "video game",
    "warzone",
    "xbox",
    "게임",
    "게임패스",
    "업데이트",
    "출시",
    "패치",
}
GAME_URL_TERMS = {
    "/call-of-duty/",
    "/cyberpunk-2077/",
    "/destiny/",
    "/games/",
    "/gaming/",
    "/magic-the-gathering/",
    "/minecraft/",
    "/pokemon/",
    "/rpg/",
    "/roblox/",
    "/warframe/",
}
NON_GAME_URL_TERMS = {
    "/anime/",
    "/entertainment/",
    "/food/",
    "/hardware/",
    "/movies/",
    "/software/",
    "/streaming-services/",
    "/superhero-shows/",
    "/tv-movies/",
    "/tv-shows/",
    "/youtube/",
}
INVALID_PAGE_TERMS = {
    "404",
    "access denied",
    "not found",
    "page not found",
    "request blocked",
    "service unavailable",
    "페이지를 찾을 수 없습니다",
}


def apply_source_context_entities(
    articles: Iterable[Article],
    sources: Iterable[Source],
) -> list[Article]:
    source_map = {source.name: source for source in sources if source.enabled}
    classified: list[Article] = []
    for article in articles:
        source = source_map.get(article.source)
        if source is not None:
            tags = _source_context_tags(source)
            if (
                article.category == "game"
                and source.name in BROAD_SOURCE_NAMES
                and _has_game_url_signal(article)
                and not _has_non_game_url_signal(article)
            ):
                tags.append("game_url_context")
            if tags:
                existing = article.matched_entities.get("SourceSignal", [])
                existing_values = existing if isinstance(existing, list) else [existing]
                merged = sorted({str(value) for value in existing_values} | set(tags))
                article.matched_entities["SourceSignal"] = merged
        classified.append(article)
    return classified


def filter_relevant_articles(
    articles: Iterable[Article],
    sources: Iterable[Source],
) -> list[Article]:
    source_map = {source.name: source for source in sources if source.enabled}
    filtered: list[Article] = []
    for article in articles:
        if article.category != "game":
            filtered.append(article)
            continue

        source = source_map.get(article.source)
        if source is None or _is_invalid_page(article):
            continue

        if source.name in BROAD_SOURCE_NAMES:
            if _has_strong_game_signal(article) and not _has_non_game_url_signal(article):
                filtered.append(article)
            elif _has_game_url_signal(article):
                filtered.append(article)
            continue

        if _source_context_tags(source) or _has_strong_game_signal(article):
            filtered.append(article)
    return filtered


def _has_strong_game_signal(article: Article) -> bool:
    entities = set(article.matched_entities)
    if entities & STRONG_ENTITY_NAMES:
        return True
    if "GameGeneral" not in entities:
        return False

    matched = article.matched_entities.get("GameGeneral", [])
    matched_terms = {str(term).lower() for term in matched if str(term).strip()}
    if matched_terms & GAME_GENERAL_STRONG_TERMS:
        return True

    haystack = f"{article.title} {article.summary}".lower()
    return any(term in haystack for term in GAME_GENERAL_STRONG_TERMS)


def _has_game_url_signal(article: Article) -> bool:
    link = (article.link or "").lower()
    return any(term in link for term in GAME_URL_TERMS)


def _has_non_game_url_signal(article: Article) -> bool:
    link = (article.link or "").lower()
    return any(term in link for term in NON_GAME_URL_TERMS)


def _is_invalid_page(article: Article) -> bool:
    title = (article.title or "").strip().lower()
    summary = (article.summary or "").strip().lower()
    return any(term in title or term in summary for term in INVALID_PAGE_TERMS)


def _source_context_tags(source: Source) -> list[str]:
    tags = {tag for tag in source.info_purpose if tag in OPERATIONAL_PURPOSES}
    content_type = source.content_type.lower()
    raw_event_model = source.config.get("event_model")
    event_model = raw_event_model.strip() if isinstance(raw_event_model, str) else ""

    if event_model in OPERATIONAL_EVENT_MODELS:
        tags.add(event_model)
    if content_type in OPERATIONAL_CONTENT_TYPES:
        tags.add(content_type)
    if source.type.lower() == "reddit" and source.name.startswith("r/"):
        tags.add("community_reaction")
    if source.name in DEDICATED_GAME_SOURCES:
        tags.add("game_media_context")
    return sorted(tags)
