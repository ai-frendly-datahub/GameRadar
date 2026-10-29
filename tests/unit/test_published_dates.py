"""Published dates stay on the UTC instant when the crawler zone is Asia/Seoul."""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from radar.collector import _extract_datetime, _extract_published
from radar.config_loader import _parse_source
from radar.models import Article, Source
from radar.storage import RadarStorage

# 2026-10-28 is a Wednesday (tm_wday=2), day-of-year 301.
_UTC_1500 = time.struct_time((2026, 10, 28, 15, 0, 0, 2, 301, 0))


@pytest.fixture
def seoul_tz() -> Iterator[None]:
    previous = os.environ.get("TZ")
    os.environ["TZ"] = "Asia/Seoul"
    time.tzset()
    try:
        assert time.timezone == -9 * 60 * 60
        yield
    finally:
        if previous is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = previous
        time.tzset()


def test_feedparser_struct_stores_1500_utc_under_seoul(seoul_tz: None, tmp_path: Path) -> None:
    """time.mktime would store 06:00. timegm must store 15:00 UTC."""
    shifted = datetime.fromtimestamp(time.mktime(_UTC_1500), tz=UTC)
    assert shifted == datetime(2026, 10, 28, 6, 0, tzinfo=UTC)

    published = _extract_datetime({"published_parsed": _UTC_1500})
    assert published == datetime(2026, 10, 28, 15, 0, tzinfo=UTC)

    storage = RadarStorage(tmp_path / "radar.duckdb")
    try:
        storage.upsert_articles(
            [
                Article(
                    title="패치",
                    link="https://store.steampowered.com/news/1",
                    summary="요약",
                    published=published,
                    source="Steam",
                    category="game",
                )
            ]
        )
        row = storage.conn.execute("SELECT published FROM articles").fetchone()
        assert row is not None
        stored = row[0]
        assert isinstance(stored, datetime)
        assert stored.tzinfo is None
        assert stored.replace(tzinfo=UTC) == datetime(2026, 10, 28, 15, 0, tzinfo=UTC)
        loaded = storage.recent_articles("game", days=3650)
        assert loaded[0].published == datetime(2026, 10, 28, 15, 0, tzinfo=UTC)
    finally:
        storage.close()


def test_offset_string_keeps_its_offset(seoul_tz: None) -> None:
    published, raw = _extract_published({"published": "Wed, 28 Oct 2026 15:00:00 +0900"})
    assert raw == "Wed, 28 Oct 2026 15:00:00 +0900"
    assert published is not None
    assert published.utcoffset() == timedelta(hours=9)
    assert published.astimezone(UTC) == datetime(2026, 10, 28, 6, 0, tzinfo=UTC)


def test_zoneless_string_uses_source_or_kr_host() -> None:
    korean = Source(name="인벤", type="rss", url="https://www.inven.co.kr/rss/news.xml")
    published, raw = _extract_published({"published": "2026-10-28 15:00:00"}, korean)
    assert raw == "2026-10-28 15:00:00"
    assert published is not None
    assert published.utcoffset() == timedelta(hours=9)
    assert published.astimezone(UTC) == datetime(2026, 10, 28, 6, 0, tzinfo=UTC)

    explicit = Source(
        name="NY",
        type="rss",
        url="https://example.com/feed",
        default_timezone="America/New_York",
    )
    summer, _ = _extract_published({"published": "2026-07-15 12:00:00"}, explicit)
    assert summer is not None
    assert summer.utcoffset() == timedelta(hours=-4)

    configured = Source(
        name="configured",
        type="rss",
        url="https://news.example.com/rss",
        config={"default_timezone": "Asia/Seoul"},
    )
    zoned, _ = _extract_published({"published": "2026-10-28 15:00:00"}, configured)
    assert zoned is not None
    assert zoned.utcoffset() == timedelta(hours=9)

    other = Source(name="other", type="rss", url="https://example.com/feed")
    utc_value, _ = _extract_published({"published": "2026-10-28 15:00:00"}, other)
    assert utc_value == datetime(2026, 10, 28, 15, 0, tzinfo=UTC)


def test_config_default_timezone_reaches_the_source() -> None:
    source = _parse_source(
        {
            "name": "인벤",
            "type": "rss",
            "url": "https://www.inven.co.kr/rss/news.xml",
            "default_timezone": "Asia/Seoul",
        }
    )
    assert source.default_timezone == "Asia/Seoul"


def test_daily_partition_uses_kst_date_of_collection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from radar import date_storage
    from radar.raw_logger import RawLogger

    # 15:30 UTC is 00:30 the next day in Asia/Seoul.
    moment = datetime(2026, 10, 28, 15, 30, tzinfo=UTC)

    class Fixed(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:
            if tz is None:
                return moment.replace(tzinfo=None)
            return moment

    monkeypatch.setattr(date_storage, "datetime", Fixed)
    monkeypatch.setattr("radar.raw_logger.datetime", Fixed)

    db_file = tmp_path / "radar.duckdb"
    db_file.write_bytes(b"db")
    snapshot = date_storage.snapshot_database(db_file)
    assert snapshot is not None
    assert snapshot.name == "2026-10-29.duckdb"

    output = RawLogger(tmp_path / "raw").log(
        [
            Article(
                title="수집",
                link="https://example.com/a",
                summary="요약",
                published=datetime(2026, 10, 28, 15, 0, tzinfo=UTC),
                source="src",
                category="game",
            )
        ],
        source_name="src",
    )
    assert output.parent.name == "2026-10-29"
    assert '"published": "2026-10-28T15:00:00+00:00"' in output.read_text(encoding="utf-8")
