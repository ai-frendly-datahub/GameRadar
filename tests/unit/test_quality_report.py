from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from radar.models import Article, CategoryConfig, Source
from radar.quality_report import build_quality_report, write_quality_report


def _article(
    *,
    source: str,
    title: str,
    published: datetime | None,
    matched_entities: dict[str, list[str]] | None = None,
) -> Article:
    return Article(
        title=title,
        link=f"https://example.com/{source}/{title}".replace(" ", "-"),
        summary=title,
        published=published,
        source=source,
        category="game",
        matched_entities=matched_entities or {},
    )


def test_build_quality_report_tracks_game_source_statuses() -> None:
    now = datetime(2026, 4, 13, tzinfo=UTC)
    category = CategoryConfig(
        category_name="game",
        display_name="Game",
        sources=[
            Source(
                name="Steam News",
                type="rss",
                url="https://store.steampowered.com/feeds/news.xml",
                content_type="patch_note",
            ),
            Source(
                name="GamesIndustry.biz",
                type="rss",
                url="https://www.gamesindustry.biz/feed",
                content_type="market_report",
                info_purpose=["sales_chart"],
            ),
            Source(
                name="PlayStation Blog",
                type="rss",
                url="https://blog.playstation.com/feed/",
                content_type="platform_update",
                info_purpose=["release_schedule"],
            ),
            Source(name="Dexerto", type="rss", url="https://www.dexerto.com/feed/"),
        ],
        entities=[],
    )
    articles = [
        _article(
            source="Steam News",
            title="Elden Ring patch notes version 1.12",
            published=now - timedelta(days=2),
            matched_entities={
                "GameTitle": ["Elden Ring"],
                "Platform": ["steam"],
                "SourceSignal": ["patch_note"],
            },
        ),
        _article(
            source="GamesIndustry.biz",
            title="EA Sports FC ranks #1 in the weekly sales chart",
            published=now - timedelta(days=4),
            matched_entities={
                "GameTitle": ["EA Sports FC"],
                "Platform": ["steam"],
                "SourceSignal": ["store_ranking"],
            },
        ),
    ]

    report = build_quality_report(
        category=category,
        articles=articles,
        quality_config={
            "data_quality": {
                "quality_outputs": {
                    "tracked_event_models": [
                        "patch_note",
                        "store_ranking",
                        "release_schedule",
                    ]
                },
                "freshness_sla": {
                    "patch_note_days": 7,
                    "store_ranking_days": 3,
                    "release_schedule_days": 7,
                },
            }
        },
        generated_at=now,
    )

    summary = report["summary"]
    assert summary["tracked_sources"] == 3
    assert summary["fresh_sources"] == 1
    assert summary["stale_sources"] == 1
    assert summary["missing_sources"] == 1
    assert summary["not_tracked_sources"] == 1
    assert summary["patch_note_events"] == 1
    assert summary["store_ranking_events"] == 1
    assert summary["actionable_game_event_count"] == 2
    assert summary["canonical_game_key_present_count"] == 2

    first_event = report["events"][0]
    assert first_event["canonical_game_key"] == "elden-ring:steam:base"
    assert first_event["version"] == "1.12"
    assert first_event["required_field_gaps"] == []


def test_build_quality_report_requires_article_level_game_evidence() -> None:
    now = datetime(2026, 4, 13, tzinfo=UTC)
    category = CategoryConfig(
        category_name="game",
        display_name="Game",
        sources=[
            Source(
                name="Ruliweb News",
                type="rss",
                url="https://example.com/rss",
                content_type="news",
                producer_role="community_media",
                info_purpose=["patch", "release"],
            )
        ],
        entities=[],
    )
    articles = [
        _article(
            source="Ruliweb News",
            title="Cloudera partner day 2026 Korea starts today",
            published=now,
            matched_entities={"SourceSignal": ["patch", "release"]},
        )
    ]

    report = build_quality_report(
        category=category,
        articles=articles,
        quality_config={
            "data_quality": {
                "quality_outputs": {
                    "tracked_event_models": ["patch_note", "release_schedule"]
                },
                "freshness_sla": {"patch_note_days": 7, "release_schedule_days": 7},
            }
        },
        generated_at=now,
    )

    summary = report["summary"]
    assert summary["patch_note_events"] == 0
    assert summary["release_schedule_events"] == 0
    assert summary["missing_event_sources"] == 1
    assert report["events"] == []


def test_build_quality_report_marks_missing_canonical_key_for_review() -> None:
    now = datetime(2026, 4, 13, tzinfo=UTC)
    category = CategoryConfig(
        category_name="game",
        display_name="Game",
        sources=[
            Source(
                name="PlayStation Blog",
                type="rss",
                url="https://blog.playstation.com/feed/",
                content_type="platform_update",
                producer_role="platform",
                info_purpose=["release_schedule"],
            )
        ],
        entities=[],
    )
    articles = [
        _article(
            source="PlayStation Blog",
            title="New action RPG launches this season",
            published=now,
            matched_entities={
                "Genre": ["action"],
                "Platform": ["ps5"],
                "Release": ["launch"],
                "SourceSignal": ["release_schedule"],
            },
        )
    ]

    report = build_quality_report(
        category=category,
        articles=articles,
        quality_config={
            "data_quality": {
                "quality_outputs": {"tracked_event_models": ["release_schedule"]},
                "event_models": {
                    "release_schedule": {
                        "required_fields": ["game_title", "platform", "source_url"]
                    }
                },
                "freshness_sla": {"release_schedule_days": 7},
            }
        },
        generated_at=now,
    )

    summary = report["summary"]
    assert summary["release_schedule_events"] == 1
    assert summary["missing_canonical_game_key_count"] == 1
    assert summary["daily_review_item_count"] == 1
    assert report["events"][0]["canonical_game_key_status"] == "missing_game_title"
    assert report["daily_review_items"][0]["reason"] == [
        "missing_game_title",
        "missing_required_fields",
    ]


def test_write_quality_report_writes_latest_and_dated_json(tmp_path) -> None:
    report = {
        "category": "game",
        "generated_at": "2026-04-13T00:00:00+00:00",
        "summary": {},
        "sources": [],
        "events": [],
    }

    paths = write_quality_report(report, output_dir=tmp_path, category_name="game")

    assert paths["latest"].name == "game_quality.json"
    assert paths["dated"].name == "game_20260413_quality.json"
    assert json.loads(paths["latest"].read_text(encoding="utf-8"))["category"] == "game"
