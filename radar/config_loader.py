from __future__ import annotations

from pathlib import Path
from typing import cast

import yaml

from .models import (
    CategoryConfig,
    EmailConfig,
    EntityDefinition,
    NotificationConfig,
    RadarSettings,
    Source,
    WebhookConfig,
)


def _resolve_path(path_value: str, *, project_root: Path) -> Path:
    """Resolve a path from config, treating relative paths as project-root relative."""
    path = Path(path_value).expanduser()
    if path.is_absolute():
        return path
    return (project_root / path).resolve()


def _read_yaml_dict(path: Path) -> dict[str, object]:
    raw = cast(object, yaml.safe_load(path.read_text(encoding="utf-8")))
    if isinstance(raw, dict):
        raw_dict = cast(dict[object, object], raw)
        return {str(k): v for k, v in raw_dict.items()}
    return {}


def _string_value(raw: dict[str, object], key: str, default: str) -> str:
    value = raw.get(key)
    if isinstance(value, str) and value.strip():
        return value
    return default


def _dict_items(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []

    items: list[dict[str, object]] = []
    for item in cast(list[object], value):
        if isinstance(item, dict):
            item_dict = cast(dict[object, object], item)
            items.append({str(k): v for k, v in item_dict.items()})
    return items


def _resolve_env_var(value: str) -> str:
    """Resolve environment variable references like ${VAR_NAME}."""
    import os
    import re

    def replace_var(match: re.Match[str]) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, "")

    return re.sub(r"\$\{([^}]+)\}", replace_var, value)


def load_settings(config_path: Path | None = None) -> RadarSettings:
    """Load global radar settings such as database and report directories."""
    project_root = Path(__file__).resolve().parent.parent
    config_file = config_path or project_root / "config" / "config.yaml"

    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    raw = _read_yaml_dict(config_file)
    db_path = _resolve_path(_string_value(raw, "database_path", "data/radar_data.duckdb"), project_root=project_root)
    report_dir = _resolve_path(_string_value(raw, "report_dir", "reports"), project_root=project_root)
    raw_data_dir = _resolve_path(_string_value(raw, "raw_data_dir", "data/raw"), project_root=project_root)
    search_db_path = _resolve_path(_string_value(raw, "search_db_path", "data/search_index.db"), project_root=project_root)

    notifications = None
    notif_raw = raw.get("notifications")
    if isinstance(notif_raw, dict):
        notif_dict = cast(dict[object, object], notif_raw)
        notifications = _parse_notifications({str(k): v for k, v in notif_dict.items()})

    return RadarSettings(
        database_path=db_path,
        report_dir=report_dir,
        raw_data_dir=raw_data_dir,
        search_db_path=search_db_path,
        notifications=notifications,
    )


def load_category_config(category_name: str, categories_dir: Path | None = None) -> CategoryConfig:
    """Load a category YAML and parse it into a CategoryConfig object."""
    project_root = Path(__file__).resolve().parent.parent
    base_dir = categories_dir or project_root / "config" / "categories"
    config_file = Path(base_dir) / f"{category_name}.yaml"

    if not config_file.exists():
        raise FileNotFoundError(f"Category config not found: {config_file}")

    raw = _read_yaml_dict(config_file)
    sources = [_parse_source(entry) for entry in _dict_items(raw.get("sources"))]
    entities = [_parse_entity(entry) for entry in _dict_items(raw.get("entities"))]

    display_name = _string_value(raw, "display_name", "") or _string_value(raw, "category_name", "") or category_name

    return CategoryConfig(
        category_name=_string_value(raw, "category_name", category_name),
        display_name=display_name,
        sources=sources,
        entities=entities,
    )


def _parse_source(entry: dict[str, object]) -> Source:
    if not entry:
        raise ValueError("Empty source entry in category config")
    return Source(
        name=_string_value(entry, "name", "Unnamed Source"),
        type=_string_value(entry, "type", "rss"),
        url=_string_value(entry, "url", ""),
    )


def _parse_entity(entry: dict[str, object]) -> EntityDefinition:
    if not entry:
        raise ValueError("Empty entity entry in category config")
    name = _string_value(entry, "name", "entity")
    display_name = _string_value(entry, "display_name", name)
    keywords_raw = entry.get("keywords")
    keywords: list[object]
    if isinstance(keywords_raw, list):
        keywords = []
        for keyword in cast(list[object], keywords_raw):
            keywords.append(keyword)
    elif isinstance(keywords_raw, tuple | set):
        keywords = []
        for keyword in cast(tuple[object, ...] | set[object], keywords_raw):
            keywords.append(keyword)
    else:
        keywords = []
    keyword_list = [str(keyword).strip() for keyword in keywords if str(keyword).strip()]
    return EntityDefinition(name=name, display_name=display_name, keywords=keyword_list)


def _parse_notifications(raw: dict[str, object]) -> NotificationConfig:
    """Parse notification configuration from YAML."""
    enabled = raw.get("enabled", False)
    if not isinstance(enabled, bool):
        enabled = False

    # Parse email config
    email_raw = raw.get("email")
    email_dict: dict[str, object] = {}
    if isinstance(email_raw, dict):
        email_raw_dict = cast(dict[object, object], email_raw)
        email_dict = {str(k): v for k, v in email_raw_dict.items()}

    email_enabled = email_dict.get("enabled", False)
    if not isinstance(email_enabled, bool):
        email_enabled = False

    email_smtp_password = _string_value(email_dict, "smtp_password", "")
    email_smtp_password = _resolve_env_var(email_smtp_password)

    email_to_addrs_raw = email_dict.get("to_addrs")
    email_to_addrs: list[str] = []
    if isinstance(email_to_addrs_raw, list):
        email_to_addrs = [
            str(addr).strip()
            for addr in cast(list[object], email_to_addrs_raw)
            if str(addr).strip()
        ]

    smtp_port_raw = email_dict.get("smtp_port", 587)
    smtp_port = 587
    if isinstance(smtp_port_raw, int):
        smtp_port = smtp_port_raw

    email_config = EmailConfig(
        enabled=email_enabled,
        smtp_host=_string_value(email_dict, "smtp_host", ""),
        smtp_port=smtp_port,
        smtp_user=_string_value(email_dict, "smtp_user", ""),
        smtp_password=email_smtp_password,
        from_addr=_string_value(email_dict, "from_addr", ""),
        to_addrs=email_to_addrs,
    )

    # Parse webhook config
    webhook_raw = raw.get("webhook")
    webhook_dict: dict[str, object] = {}
    if isinstance(webhook_raw, dict):
        webhook_raw_dict = cast(dict[object, object], webhook_raw)
        webhook_dict = {str(k): v for k, v in webhook_raw_dict.items()}

    webhook_enabled = webhook_dict.get("enabled", False)
    if not isinstance(webhook_enabled, bool):
        webhook_enabled = False

    webhook_headers_raw = webhook_dict.get("headers")
    webhook_headers: dict[str, str] = {}
    if isinstance(webhook_headers_raw, dict):
        headers_dict = cast(dict[object, object], webhook_headers_raw)
        webhook_headers = {str(k): str(v) for k, v in headers_dict.items()}

    webhook_config = WebhookConfig(
        enabled=webhook_enabled,
        url=_string_value(webhook_dict, "url", ""),
        method=_string_value(webhook_dict, "method", "POST"),
        headers=webhook_headers,
    )

    return NotificationConfig(
        enabled=enabled,
        email=email_config,
        webhook=webhook_config,
    )
