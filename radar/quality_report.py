from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import Article, CategoryConfig, Source


TRACKED_EVENT_MODEL_ORDER = [
    "steam_chart",
    "store_ranking",
    "patch_note",
    "release_schedule",
]
TRACKED_EVENT_MODELS = set(TRACKED_EVENT_MODEL_ORDER)
ARTICLE_EVIDENCE_ENTITIES = {
    "BusinessSignal",
    "Esports",
    "GameTitle",
    "Genre",
    "Platform",
    "Release",
    "Studio",
}
PATCH_TERMS = {
    "balance",
    "buff",
    "hotfix",
    "nerf",
    "patch",
    "patch notes",
    "update",
    "업데이트",
    "패치",
    "version",
}
RELEASE_TERMS = {
    "announced",
    "arrives",
    "available",
    "beta",
    "coming",
    "demo",
    "launch",
    "out now",
    "pre-order",
    "prerelease",
    "release",
    "release date",
    "season",
    "trailer",
    "예약판매",
    "오픈",
    "출시",
}
STORE_RANKING_TERMS = {
    "best-selling",
    "chart",
    "grossing",
    "rank",
    "ranking",
    "sales",
    "top seller",
    "top sellers",
}
STEAM_CHART_TERMS = {
    "concurrent",
    "most played",
    "player count",
    "players",
    "steam chart",
    "steam charts",
}
PLATFORM_ALIASES = {
    "app store": "ios",
    "epic games": "epic",
    "game pass": "xbox",
    "google play": "android",
    "nintendo": "nintendo",
    "playstation": "playstation",
    "ps4": "playstation",
    "ps5": "playstation",
    "steam": "steam",
    "switch": "nintendo",
    "switch 2": "nintendo",
    "xbox": "xbox",
}
SOURCE_PLATFORM_HINTS = {
    "Nintendo Life": "nintendo",
    "PlayStation Blog": "playstation",
    "Steam News": "steam",
    "Xbox Wire": "xbox",
}
EDITION_PATTERNS = [
    (re.compile(r"\bseason\s+\d+\b", re.IGNORECASE), "season"),
    (re.compile(r"\bearly access\b", re.IGNORECASE), "early-access"),
    (re.compile(r"\b(deluxe|ultimate|gold|collector'?s?)\b", re.IGNORECASE), "premium-edition"),
    (re.compile(r"\b(beta|demo)\b", re.IGNORECASE), "preview"),
]


def build_quality_report(
    *,
    category: CategoryConfig,
    articles: Iterable[Article],
    errors: Iterable[str] | None = None,
    quality_config: Mapping[str, object] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    generated = _as_utc(generated_at or datetime.now(UTC))
    articles_list = list(articles)
    errors_list = [str(error) for error in (errors or [])]
    quality = _dict(quality_config or {}, "data_quality")
    freshness_sla = _dict(quality, "freshness_sla")
    tracked_event_models = _tracked_event_models(quality)

    event_contracts = _event_contracts(quality)
    event_rows = _build_event_rows(
        articles_list,
        category.sources,
        tracked_event_models,
        event_contracts,
    )
    daily_review_items = _daily_review_items(event_rows)
    source_rows = [
        _build_source_row(
            source=source,
            articles=articles_list,
            event_rows=event_rows,
            errors=errors_list,
            freshness_sla=freshness_sla,
            tracked_event_models=tracked_event_models,
            generated_at=generated,
        )
        for source in category.sources
    ]

    status_counts = Counter(str(row["status"]) for row in source_rows)
    event_counts = Counter(str(row["event_model"]) for row in event_rows)
    summary = {
        "total_sources": len(source_rows),
        "enabled_sources": sum(1 for row in source_rows if row["enabled"]),
        "tracked_sources": sum(1 for row in source_rows if row["tracked"]),
        "fresh_sources": status_counts.get("fresh", 0),
        "stale_sources": status_counts.get("stale", 0),
        "missing_sources": status_counts.get("missing", 0),
        "missing_event_sources": status_counts.get("missing_event", 0),
        "unknown_event_date_sources": status_counts.get("unknown_event_date", 0),
        "not_tracked_sources": status_counts.get("not_tracked", 0),
        "skipped_disabled_sources": status_counts.get("skipped_disabled", 0),
        "collection_error_count": len(errors_list),
    }
    for event_model in TRACKED_EVENT_MODEL_ORDER:
        summary[f"{event_model}_events"] = event_counts.get(event_model, 0)
    summary.update(
        {
            "actionable_game_event_count": len(event_rows),
            "canonical_game_key_present_count": sum(
                1 for row in event_rows if row["canonical_game_key_status"] == "complete"
            ),
            "missing_canonical_game_key_count": sum(
                1 for row in event_rows if row["canonical_game_key_status"] != "complete"
            ),
            "official_or_trade_event_count": sum(
                1
                for row in event_rows
                if row["authority_role"] in {"platform", "publisher", "store", "trade_media"}
            ),
            "event_required_field_gap_count": sum(
                1 for row in event_rows if row["required_field_gaps"]
            ),
            "daily_review_item_count": len(daily_review_items),
        }
    )

    return {
        "category": category.category_name,
        "generated_at": generated.isoformat(),
        "scope_note": (
            "Official platform, store ranking, release schedule, and patch note "
            "signals are tracked separately from broad game media and community "
            "discussion. Broad feeds require game-domain evidence before they "
            "enter reports."
        ),
        "summary": summary,
        "sources": source_rows,
        "events": event_rows,
        "daily_review_items": daily_review_items,
        "source_backlog": (quality_config or {}).get("source_backlog", {}),
        "errors": errors_list,
    }


def write_quality_report(
    report: Mapping[str, object],
    *,
    output_dir: Path,
    category_name: str,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = _parse_datetime(str(report.get("generated_at") or "")) or datetime.now(UTC)
    date_stamp = _as_utc(generated_at).strftime("%Y%m%d")
    latest_path = output_dir / f"{category_name}_quality.json"
    dated_path = output_dir / f"{category_name}_{date_stamp}_quality.json"
    encoded = json.dumps(report, ensure_ascii=False, indent=2, default=str)
    latest_path.write_text(encoded + "\n", encoding="utf-8")
    dated_path.write_text(encoded + "\n", encoding="utf-8")
    return {"latest": latest_path, "dated": dated_path}


def _build_event_rows(
    articles: list[Article],
    sources: list[Source],
    tracked_event_models: set[str],
    event_contracts: Mapping[str, Mapping[str, object]],
) -> list[dict[str, Any]]:
    source_map = {source.name: source for source in sources}
    rows: list[dict[str, Any]] = []
    for article in articles:
        source = source_map.get(article.source)
        if source is None:
            continue
        event_models = _article_event_models(article, source, tracked_event_models)
        event_at = (
            _as_utc(article.published or article.collected_at)
            if (article.published or article.collected_at)
            else None
        )
        for event_model in event_models:
            rows.append(_event_row(article, source, event_model, event_at, event_contracts))
    return rows


def _event_row(
    article: Article,
    source: Source,
    event_model: str,
    event_at: datetime | None,
    event_contracts: Mapping[str, Mapping[str, object]],
) -> dict[str, Any]:
    platform = _normalized_platform(article, source)
    game_title = _normalized_game_title(article)
    edition = _edition(article)
    canonical_game_key = _canonical_game_key(game_title, platform, edition)
    canonical_status = _canonical_key_status(game_title, platform)
    row = {
        "source": article.source,
        "event_model": event_model,
        "title": article.title,
        "url": article.link,
        "event_at": event_at.isoformat() if event_at else None,
        "event_date": event_at.date().isoformat() if event_at else None,
        "platform": _matches(article, "Platform"),
        "normalized_platform": platform,
        "game_title": _matches(article, "GameTitle"),
        "normalized_game_title": game_title,
        "edition": edition,
        "canonical_game_key": canonical_game_key,
        "canonical_game_key_status": canonical_status,
        "game_event_key": _event_key(event_model, canonical_game_key, event_at),
        "genre": _matches(article, "Genre"),
        "release": _matches(article, "Release"),
        "business_signal": _matches(article, "BusinessSignal"),
        "studio": _matches(article, "Studio"),
        "source_signal": _matches(article, "SourceSignal"),
        "authority_role": _authority_role(source),
        "trust_tier": source.trust_tier,
        "producer_role": source.producer_role,
        "version": _extract_version(article),
        "rank": _extract_rank(article),
        "market": source.country or source.region or "",
        "concurrent_players": _extract_player_metric(article),
    }
    row["required_field_gaps"] = _required_field_gaps(row, event_contracts.get(event_model, {}))
    return row


def _build_source_row(
    *,
    source: Source,
    articles: list[Article],
    event_rows: list[dict[str, Any]],
    errors: list[str],
    freshness_sla: Mapping[str, object],
    tracked_event_models: set[str],
    generated_at: datetime,
) -> dict[str, Any]:
    source_articles = [article for article in articles if article.source == source.name]
    source_errors = [error for error in errors if error.startswith(f"{source.name}:")]
    event_models = _source_event_models(source, tracked_event_models)
    event_model = next(iter(sorted(event_models)), _source_event_model(source))
    source_event_rows = [
        row
        for row in event_rows
        if row["source"] == source.name and row["event_model"] in event_models
    ]
    latest_event = _latest_event(source_event_rows)
    latest_event_at = _parse_datetime(str(latest_event.get("event_at") or "")) if latest_event else None
    sla_days = _source_sla_days(source, event_model, freshness_sla)
    age_days = _age_days(generated_at, latest_event_at) if latest_event_at else None
    status = _source_status(
        source=source,
        tracked=bool(event_models),
        article_count=len(source_articles),
        event_count=len(source_event_rows),
        latest_event_at=latest_event_at,
        sla_days=sla_days,
        age_days=age_days,
    )

    return {
        "source": source.name,
        "source_type": source.type,
        "enabled": source.enabled,
        "trust_tier": source.trust_tier,
        "content_type": source.content_type,
        "collection_tier": source.collection_tier,
        "producer_role": source.producer_role,
        "info_purpose": source.info_purpose,
        "tracked": bool(event_models),
        "event_model": event_model,
        "tracked_event_models": sorted(event_models),
        "freshness_sla_days": sla_days,
        "status": status,
        "article_count": len(source_articles),
        "event_count": len(source_event_rows),
        "latest_event_at": latest_event_at.isoformat() if latest_event_at else None,
        "age_days": round(age_days, 2) if age_days is not None else None,
        "latest_title": str(latest_event.get("title", "")) if latest_event else "",
        "latest_url": str(latest_event.get("url", "")) if latest_event else "",
        "latest_source_signal": latest_event.get("source_signal", []) if latest_event else [],
        "errors": source_errors,
    }


def _source_status(
    *,
    source: Source,
    tracked: bool,
    article_count: int,
    event_count: int,
    latest_event_at: datetime | None,
    sla_days: float | None,
    age_days: float | None,
) -> str:
    if not source.enabled:
        return "skipped_disabled"
    if not tracked:
        return "not_tracked"
    if article_count == 0:
        return "missing"
    if event_count == 0:
        return "missing_event"
    if latest_event_at is None or age_days is None:
        return "unknown_event_date"
    if sla_days is not None and age_days > sla_days:
        return "stale"
    return "fresh"


def _tracked_event_models(quality: Mapping[str, object]) -> set[str]:
    outputs = _dict(quality, "quality_outputs")
    raw = outputs.get("tracked_event_models")
    if isinstance(raw, list):
        values = {str(item).strip() for item in raw if str(item).strip()}
        return values & TRACKED_EVENT_MODELS or set(TRACKED_EVENT_MODELS)
    return set(TRACKED_EVENT_MODELS)


def _source_event_model(source: Source) -> str:
    raw = source.config.get("event_model")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()

    content_type = source.content_type.lower()
    purposes = {purpose.lower() for purpose in source.info_purpose}
    if content_type == "patch_note" or "patch" in purposes:
        return "patch_note"
    if content_type == "store_ranking" or {"sales_chart", "top_seller"} & purposes:
        return "store_ranking"
    if content_type == "release_schedule" or {"release_schedule", "release"} & purposes:
        return "release_schedule"
    if "steam_chart" in purposes:
        return "steam_chart"
    return ""


def _source_event_models(source: Source, tracked_event_models: set[str]) -> set[str]:
    raw = source.config.get("event_model")
    models: set[str] = set()
    if isinstance(raw, str) and raw.strip():
        models.add(raw.strip())

    content_type = source.content_type.lower()
    purposes = {purpose.lower() for purpose in source.info_purpose}
    if content_type == "patch_note" or "patch" in purposes:
        models.add("patch_note")
    if content_type == "store_ranking" or {"sales_chart", "top_seller"} & purposes:
        models.add("store_ranking")
    if content_type == "release_schedule" or {"release_schedule", "release"} & purposes:
        models.add("release_schedule")
    if "steam_chart" in purposes:
        models.add("steam_chart")
    return models & tracked_event_models


def _article_event_models(
    article: Article,
    source: Source,
    tracked_event_models: set[str],
) -> list[str]:
    if not _has_game_domain_evidence(article):
        return []
    models = _source_event_models(source, tracked_event_models)
    signals = {value.lower() for value in _matches(article, "SourceSignal")}
    if "patch_note" in signals:
        models.add("patch_note")
    if "store_ranking" in signals:
        models.add("store_ranking")
    if "release_schedule" in signals:
        models.add("release_schedule")
    if "steam_chart" in signals:
        models.add("steam_chart")

    ordered: list[str] = []
    for event_model in TRACKED_EVENT_MODEL_ORDER:
        if event_model in models and _has_event_evidence(article, source, event_model):
            ordered.append(event_model)
    return ordered


def _has_game_domain_evidence(article: Article) -> bool:
    return any(_matches(article, entity_name) for entity_name in ARTICLE_EVIDENCE_ENTITIES)


def _has_event_evidence(article: Article, source: Source, event_model: str) -> bool:
    haystack = _haystack(article)
    if event_model == "patch_note":
        return _has_any_term(haystack, PATCH_TERMS)
    if event_model == "release_schedule":
        if not (_has_any_term(haystack, RELEASE_TERMS) or bool(_matches(article, "Release"))):
            return False
        if source.producer_role == "platform":
            return True
        return bool(_matches(article, "GameTitle") or _matches(article, "Platform"))
    if event_model == "store_ranking":
        return (
            _has_any_term(haystack, STORE_RANKING_TERMS)
            and (source.producer_role in {"trade_media", "platform"} or "sales_chart" in source.info_purpose)
        )
    if event_model == "steam_chart":
        return "steam" in haystack and _has_any_term(haystack, STEAM_CHART_TERMS)
    return False


def _event_contracts(quality: Mapping[str, object]) -> Mapping[str, Mapping[str, object]]:
    raw = quality.get("event_models")
    if not isinstance(raw, Mapping):
        return {}
    return {
        str(key): value
        for key, value in raw.items()
        if isinstance(value, Mapping)
    }


def _daily_review_items(event_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in event_rows:
        reasons: list[str] = []
        if row.get("canonical_game_key_status") != "complete":
            reasons.append(str(row.get("canonical_game_key_status") or "missing_canonical_key"))
        if row.get("required_field_gaps"):
            reasons.append("missing_required_fields")
        if row.get("authority_role") in {"community_media", "community"}:
            reasons.append("official_confirmation_required")
        if not reasons:
            continue
        items.append(
            {
                "reason": reasons,
                "event_model": row.get("event_model"),
                "source": row.get("source"),
                "title": row.get("title"),
                "url": row.get("url"),
                "canonical_game_key": row.get("canonical_game_key"),
                "required_field_gaps": row.get("required_field_gaps"),
                "game_event_key": row.get("game_event_key"),
            }
        )
        if len(items) >= 10:
            break
    return items


def _required_field_gaps(
    row: Mapping[str, Any],
    contract: Mapping[str, object],
) -> list[str]:
    raw = contract.get("required_fields")
    if not isinstance(raw, list):
        return []
    gaps: list[str] = []
    for field in raw:
        field_name = str(field)
        value = _contract_value(row, field_name)
        if value is None or value == "" or value == []:
            gaps.append(field_name)
    return gaps


def _contract_value(row: Mapping[str, Any], field_name: str) -> object:
    if field_name == "game_id":
        return row.get("canonical_game_key")
    if field_name == "game_title":
        return row.get("normalized_game_title")
    if field_name == "platform":
        return row.get("normalized_platform")
    if field_name == "source_url":
        return row.get("url")
    if field_name in {"patch_date", "release_date", "ranking_date", "metric_time", "collected_at"}:
        return row.get("event_at")
    return row.get(field_name)


def _authority_role(source: Source) -> str:
    role = source.producer_role.strip().lower()
    if role:
        return role
    source_type = source.type.lower()
    if source_type == "reddit":
        return "community"
    return "media"


def _normalized_game_title(article: Article) -> str:
    values = _matches(article, "GameTitle")
    if not values:
        return ""
    return _slug(values[0])


def _normalized_platform(article: Article, source: Source) -> str:
    platforms = _matches(article, "Platform")
    for platform in platforms:
        normalized = PLATFORM_ALIASES.get(platform.lower())
        if normalized:
            return normalized
    return SOURCE_PLATFORM_HINTS.get(source.name, "")


def _edition(article: Article) -> str:
    haystack = _haystack(article)
    for pattern, edition in EDITION_PATTERNS:
        if pattern.search(haystack):
            if edition == "season":
                match = pattern.search(haystack)
                return _slug(match.group(0)) if match else edition
            return edition
    return "base"


def _canonical_key_status(game_title: str, platform: str) -> str:
    missing = []
    if not game_title:
        missing.append("game_title")
    if not platform:
        missing.append("platform")
    if missing:
        return "missing_" + "_".join(missing)
    return "complete"


def _canonical_game_key(game_title: str, platform: str, edition: str) -> str:
    parts = [game_title, platform, edition]
    return ":".join(part for part in parts if part)


def _event_key(event_model: str, canonical_game_key: str, event_at: datetime | None) -> str:
    event_date = event_at.date().isoformat() if event_at else "undated"
    base_key = canonical_game_key or "unknown-game"
    return f"{event_model}:{base_key}:{event_date}"


def _extract_version(article: Article) -> str:
    match = re.search(r"\b(?:v(?:ersion)?\s*)?(\d+\.\d+(?:\.\d+)?)\b", _haystack(article), re.IGNORECASE)
    return match.group(1) if match else ""


def _extract_rank(article: Article) -> int | None:
    match = re.search(r"(?:#|no\.\s*|rank(?:ed|ing)?\s*)(\d{1,3})\b", _haystack(article), re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _extract_player_metric(article: Article) -> int | None:
    match = re.search(
        r"(\d{1,3}(?:,\d{3})+|\d{4,})\s+(?:concurrent\s+)?players",
        _haystack(article),
        re.IGNORECASE,
    )
    if not match:
        return None
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return None


def _has_any_term(haystack: str, terms: set[str]) -> bool:
    return any(term in haystack for term in terms)


def _haystack(article: Article) -> str:
    return f"{article.title}\n{article.summary}".lower()


def _slug(value: object) -> str:
    text = str(value).strip().lower()
    normalized = "".join(char if char.isalnum() else "-" for char in text)
    return "-".join(part for part in normalized.split("-") if part)


def _source_sla_days(
    source: Source,
    event_model: str,
    freshness_sla: Mapping[str, object],
) -> float | None:
    raw_source_sla = source.config.get("freshness_sla_days")
    parsed_source_sla = _as_float(raw_source_sla)
    if parsed_source_sla is not None:
        return parsed_source_sla

    suffixed_days = _as_float(freshness_sla.get(f"{event_model}_days"))
    if suffixed_days is not None:
        return suffixed_days

    suffixed_hours = _as_float(freshness_sla.get(f"{event_model}_hours"))
    if suffixed_hours is not None:
        return suffixed_hours / 24
    return None


def _latest_event(event_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    dated: list[tuple[datetime, dict[str, Any]]] = []
    undated: list[dict[str, Any]] = []
    for row in event_rows:
        event_at = _parse_datetime(str(row.get("event_at") or ""))
        if event_at is not None:
            dated.append((event_at, row))
        else:
            undated.append(row)
    if dated:
        return max(dated, key=lambda item: item[0])[1]
    return undated[0] if undated else None


def _matches(article: Article, key: str) -> list[str]:
    matched_entities = article.matched_entities or {}
    if not isinstance(matched_entities, dict):
        return []
    values = matched_entities.get(key, [])
    if isinstance(values, list):
        return [str(value) for value in values]
    return []


def _dict(mapping: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else {}


def _as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _age_days(generated_at: datetime, event_at: datetime) -> float:
    return max(0.0, (_as_utc(generated_at) - _as_utc(event_at)).total_seconds() / 86400)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _parse_datetime(value: str) -> datetime | None:
    if not value or value == "None":
        return None
    try:
        return _as_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except ValueError:
        return None
