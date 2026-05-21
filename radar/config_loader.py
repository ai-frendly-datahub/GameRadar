from __future__ import annotations

from pathlib import Path
from typing import cast

import yaml

from .models import (
    CategoryConfig,
    EmailConfig,
    EntityDefinition,
    RadarSettings,
    Source,
    StandardNotificationConfig,
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


def _bool_value(raw: dict[str, object], key: str, default: bool) -> bool:
    value = raw.get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
    return default


def _float_value(raw: dict[str, object], key: str, default: float) -> float:
    value = raw.get(key)
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return default
    return default


def _string_list_value(raw: dict[str, object], key: str) -> list[str]:
    value = raw.get(key)
    if isinstance(value, list):
        values = cast(list[object], value)
    elif isinstance(value, tuple | set):
        values = list(cast(tuple[object, ...] | set[object], value))
    elif isinstance(value, str) and value.strip():
        values = [value]
    else:
        values = []
    return [str(item).strip() for item in values if str(item).strip()]


def _dict_value(raw: dict[str, object], key: str) -> dict[str, object]:
    value = raw.get(key)
    if isinstance(value, dict):
        return {str(k): v for k, v in cast(dict[object, object], value).items()}
    return {}


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


def _resolve_env_refs(value: object) -> object:
    """Resolve ${VAR} environment variable references in strings."""
    if isinstance(value, str):
        result = value
        import re

        for match in re.finditer(r"\$\{([^}]+)\}", value):
            var_name = match.group(1)
            env_value = __import__("os").environ.get(var_name, "")
            result = result.replace(match.group(0), env_value)
        return result
    elif isinstance(value, dict):
        return {k: _resolve_env_refs(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_refs(item) for item in value]
    return value


def load_settings(config_path: Path | None = None) -> RadarSettings:
    """Load global radar settings such as database and report directories."""
    project_root = Path(__file__).resolve().parent.parent
    config_file = config_path or project_root / "config" / "config.yaml"

    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    raw = _read_yaml_dict(config_file)
    db_path = _resolve_path(
        _string_value(raw, "database_path", "data/radar_data.duckdb"), project_root=project_root
    )
    report_dir = _resolve_path(
        _string_value(raw, "report_dir", "reports"), project_root=project_root
    )
    raw_data_dir = _resolve_path(
        _string_value(raw, "raw_data_dir", "data/raw"), project_root=project_root
    )
    search_db_path = _resolve_path(
        _string_value(raw, "search_db_path", "data/search_index.db"), project_root=project_root
    )

    return RadarSettings(
        database_path=db_path,
        report_dir=report_dir,
        raw_data_dir=raw_data_dir,
        search_db_path=search_db_path,
    )


def load_category_config(category_name: str, categories_dir: Path | None = None) -> CategoryConfig:
    """Load a category YAML and parse it into a CategoryConfig object."""
    raw = _read_yaml_dict(_category_file(category_name, categories_dir=categories_dir))
    sources = [_parse_source(entry) for entry in _dict_items(raw.get("sources"))]
    entities = [_parse_entity(entry) for entry in _dict_items(raw.get("entities"))]

    display_name = (
        _string_value(raw, "display_name", "")
        or _string_value(raw, "category_name", "")
        or category_name
    )

    return CategoryConfig(
        category_name=_string_value(raw, "category_name", category_name),
        display_name=display_name,
        sources=sources,
        entities=entities,
    )


def _category_file(category_name: str, categories_dir: Path | None = None) -> Path:
    project_root = Path(__file__).resolve().parent.parent
    base_dir = categories_dir or project_root / "config" / "categories"
    config_file = Path(base_dir) / f"{category_name}.yaml"

    if not config_file.exists():
        raise FileNotFoundError(f"Category config not found: {config_file}")

    return config_file


def load_category_quality_config(
    category_name: str,
    categories_dir: Path | None = None,
) -> dict[str, object]:
    """Load quality-related category contract sections."""
    raw = _read_yaml_dict(_category_file(category_name, categories_dir=categories_dir))
    quality_config: dict[str, object] = {}
    for key in ("data_quality", "source_backlog", "integration_candidates"):
        if key in raw:
            quality_config[key] = _resolve_env_refs(raw[key])
    return quality_config


def _parse_source(entry: dict[str, object]) -> Source:
    if not entry:
        raise ValueError("Empty source entry in category config")
    source_config = _dict_value(entry, "config")
    for key in (
        "event_model",
        "verification_role",
        "observed_date_field",
        "event_date_field",
        "merge_policy",
    ):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            source_config.setdefault(key, value)
    canonical_key_fields = entry.get("canonical_key_fields")
    if isinstance(canonical_key_fields, list):
        source_config.setdefault(
            "canonical_key_fields",
            [str(item) for item in cast(list[object], canonical_key_fields)],
        )
    return Source(
        name=_string_value(entry, "name", "Unnamed Source"),
        type=_string_value(entry, "type", "rss"),
        url=_string_value(entry, "url", ""),
        id=_string_value(entry, "id", ""),
        enabled=_bool_value(entry, "enabled", True),
        language=_string_value(entry, "language", ""),
        country=_string_value(entry, "country", ""),
        region=_string_value(entry, "region", ""),
        trust_tier=_string_value(entry, "trust_tier", "T3_professional"),
        weight=_float_value(entry, "weight", 1.0),
        content_type=_string_value(entry, "content_type", "news"),
        collection_tier=_string_value(entry, "collection_tier", "C1_rss"),
        producer_role=_string_value(entry, "producer_role", ""),
        info_purpose=_string_list_value(entry, "info_purpose"),
        notes=_string_value(entry, "notes", ""),
        config=source_config,
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


def _parse_notifications(raw: dict[str, object]) -> StandardNotificationConfig:
    """Parse notification configuration from YAML."""
    enabled = raw.get("enabled", False)
    if not isinstance(enabled, bool):
        enabled = False

    channels = _string_list_value(raw, "channels")

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
        smtp_user=_string_value(
            email_dict,
            "smtp_user",
            _string_value(email_dict, "username", ""),
        ),
        smtp_password=email_smtp_password,
        from_addr=_string_value(
            email_dict,
            "from_addr",
            _string_value(email_dict, "from_address", ""),
        ),
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
        url=_string_value(
            webhook_dict,
            "url",
            _string_value(raw, "webhook_url", ""),
        ),
        method=_string_value(webhook_dict, "method", "POST"),
        headers=webhook_headers,
    )

    return StandardNotificationConfig(
        enabled=enabled,
        channels=channels,
        email=email_config,
        webhook=webhook_config,
    )


def load_notification_config(
    config_path: Path | None = None,
) -> StandardNotificationConfig:
    """Load notification configuration from notifications.yaml.

    Args:
        config_path: Path to notifications.yaml. If None, uses project_root/config/notifications.yaml

    Returns:
        StandardNotificationConfig with resolved environment variables

    Raises:
        FileNotFoundError: If notifications.yaml does not exist
    """
    project_root = Path(__file__).resolve().parent.parent
    config_file = config_path or project_root / "config" / "notifications.yaml"

    if not config_file.exists():
        return StandardNotificationConfig(enabled=False, channels=[])

    raw = _read_yaml_dict(config_file)
    notifications_raw = raw.get("notifications", {})
    if not isinstance(notifications_raw, dict):
        return StandardNotificationConfig(enabled=False, channels=[])

    notifications_dict = cast(dict[str, object], notifications_raw)
    enabled = bool(notifications_dict.get("enabled", False))
    channels_raw = notifications_dict.get("channels", [])
    channels = [str(c) for c in cast(list[object], channels_raw) if isinstance(c, str)]

    email_config = None
    email_raw = notifications_dict.get("email")
    if isinstance(email_raw, dict):
        email_dict = cast(dict[str, object], _resolve_env_refs(email_raw))
        try:
            smtp_port_raw = email_dict.get("smtp_port", 587)
            smtp_port = int(smtp_port_raw) if isinstance(smtp_port_raw, (int, str)) else 587
            email_to_addresses = [
                str(addr)
                for addr in cast(list[object], email_dict.get("to_addresses", []))
                if isinstance(addr, str) and addr.strip()
            ]
            email_config = EmailConfig(
                enabled=_bool_value(email_dict, "enabled", "email" in channels),
                smtp_host=_string_value(email_dict, "smtp_host", ""),
                smtp_port=smtp_port,
                smtp_user=_string_value(
                    email_dict, "smtp_user", _string_value(email_dict, "username", "")
                ),
                smtp_password=_string_value(
                    email_dict,
                    "smtp_password",
                    _string_value(email_dict, "password", ""),
                ),
                from_addr=_string_value(
                    email_dict,
                    "from_addr",
                    _string_value(email_dict, "from_address", ""),
                ),
                to_addrs=email_to_addresses,
            )
        except (ValueError, KeyError):
            email_config = None

    webhook_config = None
    webhook_raw = notifications_dict.get("webhook_url")
    if isinstance(webhook_raw, str):
        resolved = _resolve_env_refs(webhook_raw)
        webhook_url = str(resolved) if resolved else ""
        webhook_config = WebhookConfig(
            enabled="webhook" in channels and bool(webhook_url),
            url=webhook_url,
        )

    webhook_object_raw = notifications_dict.get("webhook")
    if isinstance(webhook_object_raw, dict):
        webhook_dict = cast(dict[str, object], _resolve_env_refs(webhook_object_raw))
        webhook_config = WebhookConfig(
            enabled=_bool_value(webhook_dict, "enabled", "webhook" in channels),
            url=_string_value(webhook_dict, "url", ""),
            method=_string_value(webhook_dict, "method", "POST"),
            headers=(
                {
                    str(k): str(v)
                    for k, v in cast(dict[object, object], webhook_dict.get("headers", {})).items()
                }
                if isinstance(webhook_dict.get("headers"), dict)
                else {}
            ),
        )

    return StandardNotificationConfig(
        enabled=enabled,
        channels=channels,
        email=email_config,
        webhook=webhook_config,
    )
