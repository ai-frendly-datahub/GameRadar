from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from radar.models import Article, CategoryConfig, EntityDefinition, Source
from radar.storage import RadarStorage


@pytest.fixture
def tmp_storage(tmp_path: Path) -> RadarStorage:
    """Create a temporary RadarStorage instance for testing."""
    db_path = tmp_path / "test.duckdb"
    storage = RadarStorage(db_path)
    yield storage
    storage.close()


@pytest.fixture
def sample_articles() -> list[Article]:
    """Create sample articles with realistic game domain data."""
    now = datetime.now(UTC)
    return [
        Article(
            title="새로운 AAA 게임 출시 예정",
            link="https://game.example.com/aaa-game-2024",
            summary="올해 가장 기대되는 AAA 게임이 출시될 예정입니다. RPG 장르의 대작입니다.",
            published=now,
            source="game_news",
            category="game",
            matched_entities={},
        ),
        Article(
            title="인기 FPS 게임 대규모 업데이트",
            link="https://game.example.com/fps-update-2024",
            summary="인기 FPS 게임이 대규모 업데이트를 진행합니다. 새로운 맵과 무기가 추가됩니다.",
            published=now,
            source="game_news",
            category="game",
            matched_entities={},
        ),
        Article(
            title="모바일 게임 시장 성장 분석",
            link="https://game.example.com/mobile-market-2024",
            summary="모바일 게임 시장이 계속 성장하고 있습니다. 인디 게임도 인기를 얻고 있습니다.",
            published=now,
            source="game_news",
            category="game",
            matched_entities={},
        ),
        Article(
            title="e스포츠 대회 개최 안내",
            link="https://game.example.com/esports-tournament-2024",
            summary="올해 e스포츠 대회가 개최됩니다. 상금 규모가 역대 최대입니다.",
            published=now,
            source="game_news",
            category="game",
            matched_entities={},
        ),
        Article(
            title="스팀 플랫폼 신작 게임 추천",
            link="https://game.example.com/steam-new-games-2024",
            summary="스팀 플랫폼에 새로운 게임들이 출시되었습니다. 인디 게임부터 대작까지 다양합니다.",
            published=now,
            source="game_news",
            category="game",
            matched_entities={},
        ),
    ]


@pytest.fixture
def sample_entities() -> list[EntityDefinition]:
    """Create sample entities with game domain keywords."""
    return [
        EntityDefinition(
            name="rpg_genre",
            display_name="RPG 장르",
            keywords=["RPG", "롤플레잉", "게임", "판타지", "모험"],
        ),
        EntityDefinition(
            name="fps_genre",
            display_name="FPS 장르",
            keywords=["FPS", "슈팅", "총", "전투", "액션"],
        ),
        EntityDefinition(
            name="mobile_games",
            display_name="모바일 게임",
            keywords=["모바일", "앱", "스마트폰", "태블릿", "모바일 게임"],
        ),
        EntityDefinition(
            name="esports",
            display_name="e스포츠",
            keywords=["e스포츠", "대회", "토너먼트", "경기", "프로게이머"],
        ),
        EntityDefinition(
            name="steam_platform",
            display_name="스팀 플랫폼",
            keywords=["스팀", "Steam", "PC", "플랫폼", "인디"],
        ),
    ]


@pytest.fixture
def sample_config(tmp_path: Path, sample_entities: list[EntityDefinition]) -> CategoryConfig:
    """Create a sample CategoryConfig for testing."""
    sources = [
        Source(
            name="game_news",
            type="rss",
            url="https://game.example.com/feed",
        ),
    ]
    return CategoryConfig(
        category_name="game",
        display_name="게임",
        sources=sources,
        entities=sample_entities,
    )
