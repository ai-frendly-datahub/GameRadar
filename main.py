from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from radar_core.config_loader import filter_sources
from radar_core.models import StandardNotificationConfig
from radar_core.ontology import annotate_articles_with_ontology

from radar.analyzer import apply_entity_rules
from radar.collector import collect_sources
from radar.common.validators import validate_article
from radar.config_loader import (
    load_category_config,
    load_category_quality_config,
    load_notification_config,
    load_settings,
)
from radar.date_storage import apply_date_storage_policy
from radar.logger import configure_logging, get_logger
from radar.models import Article, CategoryConfig, Source
from radar.notifier import (
    CompositeNotifier,
    EmailNotifier,
    NotificationPayload,
    Notifier,
    WebhookNotifier,
)
from radar.quality_report import build_quality_report, write_quality_report
from radar.raw_logger import RawLogger
from radar.relevance import apply_source_context_entities, filter_relevant_articles
from radar.reporter import generate_index_html, generate_report
from radar.search_index import SearchIndex
from radar.storage import RadarStorage

logger = get_logger(__name__)


def _select_quality_articles(
    storage: RadarStorage,
    *,
    category_cfg: CategoryConfig,
    effective_sources: list[Source],
    recent_days: int,
    per_source_limit: int,
) -> list[Article]:
    """Use a wider window for source-quality coverage than the report body."""
    quality_days = max(recent_days, 14)
    quality_limit = max(1000, per_source_limit * max(len(effective_sources), 1) * 3)
    return filter_relevant_articles(
        apply_source_context_entities(
            storage.recent_articles(
                category_cfg.category_name,
                days=quality_days,
                limit=quality_limit,
            ),
            effective_sources,
        ),
        effective_sources,
    )


def _send_notifications(
    *,
    notification_config: StandardNotificationConfig,
    category_name: str,
    sources_count: int,
    collected_count: int,
    matched_count: int,
    errors_count: int,
    report_path: Path,
) -> None:
    """Send notifications if configured.

    Args:
        notification_config: Standard notification config
        category_name: Category name
        sources_count: Number of sources
        collected_count: Number of collected articles
        matched_count: Number of matched articles
        errors_count: Number of errors
        report_path: Path to generated report
    """
    if not notification_config.enabled:
        return

    notifiers: list[Notifier] = []
    enabled_channels = {channel.lower() for channel in notification_config.channels}

    email_config = notification_config.email
    if email_config is not None and (email_config.enabled or "email" in enabled_channels):
        email_notifier = EmailNotifier(
            smtp_host=email_config.smtp_host,
            smtp_port=email_config.smtp_port,
            smtp_user=email_config.smtp_user,
            smtp_password=email_config.smtp_password,
            from_addr=email_config.from_addr,
            to_addrs=email_config.to_addrs,
        )
        notifiers.append(email_notifier)

    webhook_config = notification_config.webhook
    if webhook_config is not None and (webhook_config.enabled or "webhook" in enabled_channels):
        webhook_notifier = WebhookNotifier(
            url=webhook_config.url,
            method=webhook_config.method,
            headers=webhook_config.headers,
        )
        notifiers.append(webhook_notifier)

    if not notifiers:
        return

    # Build notification payload
    payload = NotificationPayload(
        category_name=category_name,
        sources_count=sources_count,
        collected_count=collected_count,
        matched_count=matched_count,
        errors_count=errors_count,
        timestamp=datetime.now(UTC),
        report_url=str(report_path),
    )

    # Send via composite notifier
    composite = CompositeNotifier(notifiers)
    result = composite.send(payload)

    if result:
        logger.info("notifications_sent", category=category_name)
    else:
        logger.warning("notifications_failed", category=category_name)


def run(
    *,
    category: str,
    config_path: Path | None = None,
    categories_dir: Path | None = None,
    per_source_limit: int = 30,
    recent_days: int = 7,
    timeout: int = 15,
    keep_days: int = 90,
    keep_raw_days: int = 180,
    keep_report_days: int = 90,
    snapshot_db: bool = False,
    max_sources: int | None = None,
    exclude_sources: tuple[str, ...] | list[str] = (),
) -> Path:
    """Execute the lightweight collect -> analyze -> report pipeline."""
    configure_logging()
    settings = load_settings(config_path)
    notification_config = load_notification_config(
        config_path.parent / "notifications.yaml" if config_path is not None else None
    )
    category_cfg = load_category_config(category, categories_dir=categories_dir)
    quality_cfg = load_category_quality_config(category, categories_dir=categories_dir)

    effective_sources = filter_sources(
        category_cfg.sources,
        max_sources=max_sources,
        exclude_sources=tuple(exclude_sources or ()),
    )

    logger.info(
        "pipeline_start",
        category=category_cfg.category_name,
        sources_count=len(effective_sources),
    )
    collected, errors = collect_sources(
        effective_sources,
        category=category_cfg.category_name,
        limit_per_source=per_source_limit,
        timeout=timeout,
    )

    collected = annotate_articles_with_ontology(
        collected,
        repo_name="GameRadar",
        sources_by_name={source.name: source for source in effective_sources},
        category_name=category_cfg.category_name,
        search_from=Path(__file__),
        attach_event_model_payload=True,
    )

    raw_logger = RawLogger(settings.raw_data_dir)
    for source in effective_sources:
        source_articles = [article for article in collected if article.source == source.name]
        if source_articles:
            _ = raw_logger.log(source_articles, source_name=source.name)

    analyzed = apply_entity_rules(collected, category_cfg.entities)
    classified = apply_source_context_entities(analyzed, effective_sources)
    scoped_articles = filter_relevant_articles(classified, effective_sources)

    # Validate articles for data quality
    validated_articles = []
    validation_errors = []
    for article in scoped_articles:
        is_valid, article_errors = validate_article(article)
        if is_valid:
            validated_articles.append(article)
        else:
            validation_errors.append(f"{article.link}: {', '.join(article_errors)}")

    storage = RadarStorage(settings.database_path)
    storage.upsert_articles(validated_articles)
    all_errors = errors + validation_errors
    _ = storage.delete_older_than(keep_days)

    with SearchIndex(settings.search_db_path) as search_idx:
        batch_items = [
            (article.link, article.title, article.summary) for article in validated_articles
        ]
        search_idx.upsert_batch(batch_items)

    recent_articles = filter_relevant_articles(
        apply_source_context_entities(
            storage.recent_articles(category_cfg.category_name, days=recent_days, limit=1000),
            effective_sources,
        ),
        effective_sources,
    )
    quality_articles = _select_quality_articles(
        storage,
        category_cfg=category_cfg,
        effective_sources=effective_sources,
        recent_days=recent_days,
        per_source_limit=per_source_limit,
    )
    storage.close()

    matched_count = sum(1 for a in scoped_articles if a.matched_entities)
    recent_matched_count = sum(1 for a in recent_articles if a.matched_entities)
    logger.info(
        "collection_complete",
        collected_count=len(scoped_articles),
        errors_count=len(all_errors),
    )
    logger.info("analysis_complete", matched_count=matched_count)

    stats = {
        "sources": len(effective_sources),
        "collected": len(scoped_articles),
        "matched": matched_count,
        "window_days": recent_days,
        "article_count": len(recent_articles),
        "source_count": len({article.source for article in recent_articles}),
        "matched_count": recent_matched_count,
    }

    quality_report = build_quality_report(
        category=category_cfg,
        articles=quality_articles,
        errors=all_errors,
        quality_config=quality_cfg,
    )
    output_path = settings.report_dir / f"{category_cfg.category_name}_report.html"
    _ = generate_report(
        category=category_cfg,
        articles=recent_articles,
        output_path=output_path,
        stats=stats,
        errors=all_errors,
        quality_report=quality_report,
    )
    quality_paths = write_quality_report(
        quality_report,
        output_dir=settings.report_dir,
        category_name=category_cfg.category_name,
    )
    # Generate index.html
    generate_index_html(settings.report_dir)
    date_storage = apply_date_storage_policy(
        database_path=settings.database_path,
        raw_data_dir=settings.raw_data_dir,
        report_dir=settings.report_dir,
        keep_raw_days=keep_raw_days,
        keep_report_days=keep_report_days,
        snapshot_db=snapshot_db,
    )
    logger.info("report_generated", output_path=str(output_path))
    logger.info("quality_report_generated", output_path=str(quality_paths["latest"]))
    snapshot_path = date_storage.get("snapshot_path")
    if isinstance(snapshot_path, str) and snapshot_path:
        logger.info("snapshot_saved", snapshot_path=snapshot_path)
    if all_errors:
        logger.warning("collection_errors", errors_count=len(all_errors))

    # Send notifications if configured
    _send_notifications(
        notification_config=notification_config,
        category_name=category_cfg.category_name,
        sources_count=len(effective_sources),
        collected_count=len(scoped_articles),
        matched_count=matched_count,
        errors_count=len(all_errors),
        report_path=output_path,
    )

    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lightweight Radar template runner")
    _ = parser.add_argument(
        "--category", required=True, help="Category name matching a YAML in config/categories/"
    )
    _ = parser.add_argument(
        "--config", type=Path, default=None, help="Path to config/config.yaml (optional)"
    )
    _ = parser.add_argument(
        "--categories-dir", type=Path, default=None, help="Custom directory for category YAML files"
    )
    _ = parser.add_argument(
        "--per-source-limit", type=int, default=30, help="Max items to pull from each source"
    )
    _ = parser.add_argument(
        "--recent-days", type=int, default=7, help="Window (days) to show in the report"
    )
    _ = parser.add_argument(
        "--timeout", type=int, default=15, help="HTTP timeout per request (seconds)"
    )
    _ = parser.add_argument(
        "--keep-days", type=int, default=90, help="Retention window for stored items"
    )
    _ = parser.add_argument(
        "--keep-raw-days", type=int, default=180, help="Retention window for raw JSONL directories"
    )
    _ = parser.add_argument(
        "--keep-report-days", type=int, default=90, help="Retention window for dated HTML reports"
    )
    _ = parser.add_argument(
        "--snapshot-db",
        action="store_true",
        default=False,
        help="Create a dated DuckDB snapshot after each run",
    )
    _ = parser.add_argument(
        "--generate-report",
        action="store_true",
        default=False,
        help="Backward-compatible no-op; reports are always generated",
    )
    _ = parser.add_argument(
        "--max-sources",
        type=int,
        default=None,
        help="Hard cap on number of sources iterated (after --exclude-source). Default: no cap.",
    )
    _ = parser.add_argument(
        "--exclude-source",
        action="append",
        default=[],
        metavar="ID_OR_NAME",
        help="Skip this source id or name. May be repeated.",
    )
    return parser.parse_args()


def _to_path(value: object) -> Path | None:
    if isinstance(value, Path):
        return value
    return None


def _to_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _to_optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _to_str_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in cast(list[object], value) if isinstance(item, str)]
    return []


if __name__ == "__main__":
    args = cast(dict[str, object], vars(parse_args()))
    _ = run(
        category=str(args.get("category", "")),
        config_path=_to_path(args.get("config")),
        categories_dir=_to_path(args.get("categories_dir")),
        per_source_limit=_to_int(args.get("per_source_limit"), 30),
        recent_days=_to_int(args.get("recent_days"), 7),
        timeout=_to_int(args.get("timeout"), 15),
        keep_days=_to_int(args.get("keep_days"), 90),
        keep_raw_days=_to_int(args.get("keep_raw_days"), 180),
        keep_report_days=_to_int(args.get("keep_report_days"), 90),
        snapshot_db=bool(args.get("snapshot_db", False)),
        max_sources=_to_optional_int(args.get("max_sources")),
        exclude_sources=_to_str_list(args.get("exclude_source")),
    )
