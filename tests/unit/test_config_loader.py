from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from radar.config_loader import (
    _dict_items,
    _parse_entity,
    _parse_source,
    _read_yaml_dict,
    _resolve_path,
    _string_value,
    load_category_config,
    load_category_quality_config,
    load_settings,
)


class TestLoadSettings:
    """Test global settings loading."""

    def test_load_settings_with_default_config(self) -> None:
        """Should load settings from default config.yaml."""
        settings = load_settings()

        assert settings.database_path is not None
        assert settings.report_dir is not None
        assert settings.raw_data_dir is not None
        assert settings.search_db_path is not None

    def test_load_settings_missing_config_file(self) -> None:
        """Should raise FileNotFoundError when config file missing."""
        with pytest.raises(FileNotFoundError):
            load_settings(Path("/nonexistent/config.yaml"))

    def test_load_settings_resolves_relative_paths(self) -> None:
        """Should resolve relative paths from project root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_file = config_dir / "config.yaml"
            config_file.write_text(
                "database_path: data/test.duckdb\n"
                "report_dir: reports\n"
                "raw_data_dir: data/raw\n"
                "search_db_path: data/search.db\n",
                encoding="utf-8",
            )

            settings = load_settings(config_file)

            assert settings.database_path.is_absolute()
            assert settings.report_dir.is_absolute()

    def test_load_settings_handles_absolute_paths(self) -> None:
        """Should handle absolute paths in config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_file = config_dir / "config.yaml"
            abs_db_path = Path(tmpdir) / "data" / "test.duckdb"
            config_file.write_text(
                f"database_path: {abs_db_path}\n"
                "report_dir: reports\n"
                "raw_data_dir: data/raw\n"
                "search_db_path: data/search.db\n",
                encoding="utf-8",
            )

            settings = load_settings(config_file)

            assert settings.database_path == abs_db_path

    def test_load_settings_uses_defaults_for_missing_keys(self) -> None:
        """Should use default values for missing config keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_file = config_dir / "config.yaml"
            config_file.write_text("", encoding="utf-8")

            settings = load_settings(config_file)

            assert "radar_data.duckdb" in str(settings.database_path)
            assert "reports" in str(settings.report_dir)


class TestLoadCategoryConfig:
    """Test category configuration loading."""

    def test_load_category_config_basic(self) -> None:
        """Should load category config from YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            categories_dir = Path(tmpdir)
            config_file = categories_dir / "tech.yaml"
            config_file.write_text(
                "category_name: tech\n"
                "display_name: Technology\n"
                "sources:\n"
                "  - name: TechNews\n"
                "    type: rss\n"
                "    url: http://example.com/feed\n"
                "entities:\n"
                "  - name: python\n"
                "    display_name: Python\n"
                "    keywords:\n"
                "      - python\n",
                encoding="utf-8",
            )

            config = load_category_config("tech", categories_dir)

            assert config.category_name == "tech"
            assert config.display_name == "Technology"
            assert len(config.sources) == 1
            assert len(config.entities) == 1

    def test_load_category_config_missing_file(self) -> None:
        """Should raise FileNotFoundError when category file missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError):
                load_category_config("nonexistent", Path(tmpdir))

    def test_real_game_config_uses_ruliweb_rss_and_disables_blocked_sources(self) -> None:
        """Should keep smoke-warning sources out of the live collector path."""
        config = load_category_config("game")
        sources = {source.name: source for source in config.sources}

        ruliweb = sources["루리웹 뉴스"]
        assert ruliweb.type == "rss"
        assert ruliweb.url == "https://bbs.ruliweb.com/news/rss"
        assert ruliweb.collection_tier == "C1_rss"
        assert ruliweb.config["bypass_crawl_health"] is True

        assert sources["Eurogamer"].enabled is False
        assert "connection reset" in sources["Eurogamer"].notes
        assert sources["게임포커스"].enabled is False
        assert "403/404" in sources["게임포커스"].notes
        assert sources["VentureBeat Gaming"].enabled is False
        assert "403" in sources["VentureBeat Gaming"].notes
        assert sources["Esports Insider"].enabled is False
        assert "resets" in sources["Esports Insider"].notes
        assert sources["The Esports Observer"].enabled is False
        assert "HTTP 500" in sources["The Esports Observer"].notes
        assert sources["인벤 뉴스"].enabled is False
        assert "404" in sources["인벤 뉴스"].notes
        assert sources["디스이즈게임"].enabled is False
        assert "403" in sources["디스이즈게임"].notes
        assert sources["Famitsu"].enabled is False
        assert "404" in sources["Famitsu"].notes
        assert sources["4Gamer"].enabled is False
        assert "404" in sources["4Gamer"].notes
        assert sources["Kinda Funny Games Daily"].enabled is False
        assert "404" in sources["Kinda Funny Games Daily"].notes

    def test_load_category_config_multiple_sources(self) -> None:
        """Should load multiple sources from config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            categories_dir = Path(tmpdir)
            config_file = categories_dir / "tech.yaml"
            config_file.write_text(
                "category_name: tech\n"
                "display_name: Technology\n"
                "sources:\n"
                "  - name: Source1\n"
                "    type: rss\n"
                "    url: http://example.com/1\n"
                "  - name: Source2\n"
                "    type: rss\n"
                "    url: http://example.com/2\n"
                "entities: []\n",
                encoding="utf-8",
            )

            config = load_category_config("tech", categories_dir)

            assert len(config.sources) == 2
            assert config.sources[0].name == "Source1"
            assert config.sources[1].name == "Source2"

    def test_load_category_config_multiple_entities(self) -> None:
        """Should load multiple entities from config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            categories_dir = Path(tmpdir)
            config_file = categories_dir / "tech.yaml"
            config_file.write_text(
                "category_name: tech\n"
                "display_name: Technology\n"
                "sources: []\n"
                "entities:\n"
                "  - name: python\n"
                "    display_name: Python\n"
                "    keywords: [python]\n"
                "  - name: javascript\n"
                "    display_name: JavaScript\n"
                "    keywords: [javascript]\n",
                encoding="utf-8",
            )

            config = load_category_config("tech", categories_dir)

            assert len(config.entities) == 2
            assert config.entities[0].name == "python"
            assert config.entities[1].name == "javascript"

    def test_load_category_config_uses_category_name_as_display_name_fallback(self) -> None:
        """Should use category_name as display_name if display_name missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            categories_dir = Path(tmpdir)
            config_file = categories_dir / "tech.yaml"
            config_file.write_text(
                "category_name: tech\nsources: []\nentities: []\n",
                encoding="utf-8",
            )

            config = load_category_config("tech", categories_dir)

            assert config.display_name == "tech"


class TestParseSource:
    """Test source parsing."""

    def test_parse_source_basic(self) -> None:
        """Should parse source from dict."""
        entry = {"name": "BBC", "type": "rss", "url": "http://example.com/feed"}

        source = _parse_source(entry)

        assert source.name == "BBC"
        assert source.type == "rss"
        assert source.url == "http://example.com/feed"

    def test_parse_source_empty_entry_raises_error(self) -> None:
        """Should raise ValueError for empty source entry."""
        with pytest.raises(ValueError, match="Empty source entry"):
            _parse_source({})

    def test_parse_source_missing_url_uses_default(self) -> None:
        """Should use empty string for missing URL."""
        entry = {"name": "BBC", "type": "rss"}

        source = _parse_source(entry)

        assert source.url == ""

    def test_parse_source_missing_name_uses_default(self) -> None:
        """Should use default name for missing name."""
        entry = {"type": "rss", "url": "http://example.com"}

        source = _parse_source(entry)

        assert source.name == "Unnamed Source"

    def test_parse_source_missing_type_uses_default(self) -> None:
        """Should use 'rss' as default type."""
        entry = {"name": "BBC", "url": "http://example.com"}

        source = _parse_source(entry)

        assert source.type == "rss"

    def test_parse_source_preserves_metadata_and_config(self) -> None:
        """Should preserve taxonomy metadata and browser config."""
        entry = {
            "name": "Steam News",
            "type": "rss",
            "url": "https://store.steampowered.com/feeds/news.xml",
            "id": "steam_news",
            "enabled": False,
            "language": "en",
            "country": "US",
            "region": "NorthAmerica",
            "trust_tier": "T1_authoritative",
            "weight": 1.7,
            "content_type": "patch_note",
            "collection_tier": "C1_rss",
            "producer_role": "platform",
            "info_purpose": ["patch", "release"],
            "notes": "Official patch feed",
            "config": {"wait_for": ".newsHub"},
        }

        source = _parse_source(entry)

        assert source.id == "steam_news"
        assert source.enabled is False
        assert source.language == "en"
        assert source.country == "US"
        assert source.region == "NorthAmerica"
        assert source.trust_tier == "T1_authoritative"
        assert source.weight == 1.7
        assert source.content_type == "patch_note"
        assert source.collection_tier == "C1_rss"
        assert source.producer_role == "platform"
        assert source.info_purpose == ["patch", "release"]
        assert source.notes == "Official patch feed"
        assert source.config == {"wait_for": ".newsHub"}

    def test_parse_source_preserves_event_contract_metadata(self) -> None:
        """Should preserve source-level event contract metadata in config."""
        entry = {
            "name": "Steam News",
            "type": "rss",
            "url": "https://store.steampowered.com/feeds/news.xml",
            "event_model": "patch_note",
            "canonical_key_fields": ["game_id", "platform", "version"],
            "verification_role": "official_patch_reference",
            "config": {"freshness_sla_days": 7},
        }

        source = _parse_source(entry)

        assert source.config["event_model"] == "patch_note"
        assert source.config["canonical_key_fields"] == ["game_id", "platform", "version"]
        assert source.config["verification_role"] == "official_patch_reference"
        assert source.config["freshness_sla_days"] == 7

    def test_load_category_quality_config_returns_quality_contract(self) -> None:
        """Should return quality contract sections from category YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            categories_dir = Path(tmpdir)
            config_file = categories_dir / "game.yaml"
            config_file.write_text(
                "category_name: game\n"
                "data_quality:\n"
                "  quality_outputs:\n"
                "    tracked_event_models:\n"
                "      - patch_note\n"
                "source_backlog:\n"
                "  operational_candidates:\n"
                "    - id: steam_top_sellers\n"
                "sources: []\n"
                "entities: []\n",
                encoding="utf-8",
            )

            quality = load_category_quality_config("game", categories_dir)

        assert quality["data_quality"] == {
            "quality_outputs": {"tracked_event_models": ["patch_note"]}
        }
        assert quality["source_backlog"] == {
            "operational_candidates": [{"id": "steam_top_sellers"}]
        }


class TestParseEntity:
    """Test entity parsing."""

    def test_parse_entity_basic(self) -> None:
        """Should parse entity from dict."""
        entry = {
            "name": "python",
            "display_name": "Python",
            "keywords": ["python", "py"],
        }

        entity = _parse_entity(entry)

        assert entity.name == "python"
        assert entity.display_name == "Python"
        assert entity.keywords == ["python", "py"]

    def test_parse_entity_empty_entry_raises_error(self) -> None:
        """Should raise ValueError for empty entity entry."""
        with pytest.raises(ValueError, match="Empty entity entry"):
            _parse_entity({})

    def test_parse_entity_missing_display_name_uses_name(self) -> None:
        """Should use name as display_name if missing."""
        entry = {"name": "python", "keywords": ["python"]}

        entity = _parse_entity(entry)

        assert entity.display_name == "python"

    def test_parse_entity_missing_keywords_uses_empty_list(self) -> None:
        """Should use empty list for missing keywords."""
        entry = {"name": "python", "display_name": "Python"}

        entity = _parse_entity(entry)

        assert entity.keywords == []

    def test_parse_entity_keywords_as_list(self) -> None:
        """Should handle keywords as list."""
        entry = {
            "name": "python",
            "display_name": "Python",
            "keywords": ["python", "py"],
        }

        entity = _parse_entity(entry)

        assert entity.keywords == ["python", "py"]

    def test_parse_entity_keywords_as_tuple(self) -> None:
        """Should handle keywords as tuple."""
        entry = {
            "name": "python",
            "display_name": "Python",
            "keywords": ("python", "py"),
        }

        entity = _parse_entity(entry)

        assert set(entity.keywords) == {"python", "py"}

    def test_parse_entity_keywords_as_set(self) -> None:
        """Should handle keywords as set."""
        entry = {
            "name": "python",
            "display_name": "Python",
            "keywords": {"python", "py"},
        }

        entity = _parse_entity(entry)

        assert set(entity.keywords) == {"python", "py"}

    def test_parse_entity_strips_whitespace_from_keywords(self) -> None:
        """Should strip whitespace from keywords."""
        entry = {
            "name": "python",
            "display_name": "Python",
            "keywords": ["  python  ", "  py  "],
        }

        entity = _parse_entity(entry)

        assert entity.keywords == ["python", "py"]

    def test_parse_entity_filters_empty_keywords(self) -> None:
        """Should filter out empty keywords."""
        entry = {
            "name": "python",
            "display_name": "Python",
            "keywords": ["python", "", "   ", "py"],
        }

        entity = _parse_entity(entry)

        assert entity.keywords == ["python", "py"]


class TestReadYamlDict:
    """Test YAML reading."""

    def test_read_yaml_dict_basic(self) -> None:
        """Should read YAML file as dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = Path(tmpdir) / "test.yaml"
            yaml_file.write_text("key: value\nother: 123\n", encoding="utf-8")

            result = _read_yaml_dict(yaml_file)

            assert result["key"] == "value"
            assert result["other"] == 123

    def test_read_yaml_dict_empty_file(self) -> None:
        """Should return empty dict for empty YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = Path(tmpdir) / "test.yaml"
            yaml_file.write_text("", encoding="utf-8")

            result = _read_yaml_dict(yaml_file)

            assert result == {}

    def test_read_yaml_dict_non_dict_content(self) -> None:
        """Should return empty dict if YAML is not a dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = Path(tmpdir) / "test.yaml"
            yaml_file.write_text("- item1\n- item2\n", encoding="utf-8")

            result = _read_yaml_dict(yaml_file)

            assert result == {}


class TestResolvePath:
    """Test path resolution."""

    def test_resolve_path_absolute_path(self) -> None:
        """Should return absolute path unchanged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            abs_path = Path(tmpdir) / "test.txt"
            project_root = Path(tmpdir)

            result = _resolve_path(str(abs_path), project_root=project_root)

            assert result == abs_path

    def test_resolve_path_relative_path(self) -> None:
        """Should resolve relative path from project root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            relative = "data/test.txt"

            result = _resolve_path(relative, project_root=project_root)

            assert result == (project_root / relative).resolve()

    def test_resolve_path_with_tilde(self) -> None:
        """Should expand tilde in paths."""
        result = _resolve_path("~/test.txt", project_root=Path("/tmp"))

        assert "~" not in str(result)
        assert result.is_absolute()


class TestStringValue:
    """Test string value extraction."""

    def test_string_value_existing_key(self) -> None:
        """Should return string value for existing key."""
        data = {"key": "value"}

        result = _string_value(data, "key", "default")

        assert result == "value"

    def test_string_value_missing_key(self) -> None:
        """Should return default for missing key."""
        data: dict[str, object] = {}

        result = _string_value(data, "key", "default")

        assert result == "default"

    def test_string_value_non_string_value(self) -> None:
        """Should return default for non-string value."""
        data = {"key": 123}

        result = _string_value(data, "key", "default")

        assert result == "default"

    def test_string_value_empty_string(self) -> None:
        """Should return default for empty string."""
        data = {"key": ""}

        result = _string_value(data, "key", "default")

        assert result == "default"

    def test_string_value_whitespace_only(self) -> None:
        """Should return default for whitespace-only string."""
        data = {"key": "   "}

        result = _string_value(data, "key", "default")

        assert result == "default"


class TestDictItems:
    """Test dict items extraction."""

    def test_dict_items_list_of_dicts(self) -> None:
        """Should extract list of dicts."""
        value = [{"key": "value"}, {"other": "data"}]

        result = _dict_items(value)

        assert len(result) == 2
        assert result[0]["key"] == "value"
        assert result[1]["other"] == "data"

    def test_dict_items_empty_list(self) -> None:
        """Should return empty list for empty input."""
        result = _dict_items([])

        assert result == []

    def test_dict_items_non_list(self) -> None:
        """Should return empty list for non-list input."""
        result = _dict_items("not a list")

        assert result == []

    def test_dict_items_list_with_non_dicts(self) -> None:
        """Should filter out non-dict items."""
        value = [{"key": "value"}, "string", 123, {"other": "data"}]

        result = _dict_items(value)

        assert len(result) == 2
        assert result[0]["key"] == "value"
        assert result[1]["other"] == "data"

    def test_dict_items_converts_keys_to_strings(self) -> None:
        """Should convert dict keys to strings."""
        value = [{1: "value", "key": "data"}]

        result = _dict_items(value)

        assert "1" in result[0]
        assert "key" in result[0]
