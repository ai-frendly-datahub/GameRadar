from __future__ import annotations

import importlib
from datetime import UTC, datetime, timedelta, tzinfo
from pathlib import Path

import pytest
import structlog

import radar.collector as collector_module
from tests.reference_dates import REFERENCE_NOW

_ORIGINAL_ROBOTS_PERMITS = collector_module._robots_permits


class FrozenDateTime(datetime):
    """datetime.now() in date-stamping modules returns REFERENCE_NOW."""

    @classmethod
    def now(cls, tz: tzinfo | None = None) -> datetime:
        if tz is None:
            return REFERENCE_NOW.replace(tzinfo=None)
        return REFERENCE_NOW


@pytest.fixture(autouse=True)
def freeze_reference_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    for module_name in ("radar.date_storage", "radar.raw_logger"):
        module = importlib.import_module(module_name)
        monkeypatch.setattr(module, "datetime", FrozenDateTime)


@pytest.fixture(autouse=True)
def reset_structlog() -> object:
    structlog.reset_defaults()
    yield
    structlog.reset_defaults()


@pytest.fixture(autouse=True)
def isolate_crawl_health_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("RADAR_CRAWL_HEALTH_DB_PATH", str(tmp_path / "crawl_health.duckdb"))


def _allow_robots(*_args: object, **_kwargs: object) -> bool:
    return True


@pytest.fixture(autouse=True)
def permit_robots_txt(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    """Unit tests use feed fixtures. Robots checks have their own fixture tests."""
    if "real_robots_permits" in request.fixturenames:
        return
    monkeypatch.setattr(collector_module, "_robots_permits", _allow_robots)


@pytest.fixture
def real_robots_permits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(collector_module, "_robots_permits", _ORIGINAL_ROBOTS_PERMITS)


@pytest.fixture
def sample_source() -> object:
    from radar.models import Source

    return Source(name="Example RSS", type="rss", url="https://example.com/feed.xml")


@pytest.fixture
def sample_entity() -> object:
    from radar.models import EntityDefinition

    return EntityDefinition(name="topic", display_name="Topic", keywords=["ai", "cloud", "python"])


@pytest.fixture
def sample_article() -> object:
    from radar.models import Article

    return Article(
        title="AI and cloud market update",
        link="https://example.com/article-1",
        summary="Python tooling and AI adoption continue to grow.",
        published=datetime.now(UTC) - timedelta(days=1),
        source="Example RSS",
        category="tech",
        matched_entities={"topic": ["ai", "cloud", "python"]},
    )


@pytest.fixture
def tmp_duckdb(tmp_path: Path) -> Path:
    return tmp_path / "test_radar_data.duckdb"


@pytest.fixture
def tmp_search_db(tmp_path: Path) -> Path:
    return tmp_path / "test_search_index.db"


@pytest.fixture
def tmp_storage(tmp_duckdb: Path) -> object:
    from radar.storage import RadarStorage

    storage = RadarStorage(tmp_duckdb)
    try:
        yield storage
    finally:
        storage.close()


@pytest.fixture
def tmp_search_index(tmp_search_db: Path) -> object:
    from radar.search_index import SearchIndex

    index = SearchIndex(tmp_search_db)
    try:
        yield index
    finally:
        index.close()
