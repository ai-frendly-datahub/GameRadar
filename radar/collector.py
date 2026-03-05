from __future__ import annotations

import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Tuple

import feedparser
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .logger import get_logger
from .models import Article, Source

logger = get_logger(__name__)


def _fetch_url_with_retry(url: str, timeout: int, source_name: str) -> requests.Response:
    """Fetch URL with retry logic on transient errors."""
    attempt = 0

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        reraise=True,
    )
    def _fetch() -> requests.Response:
        nonlocal attempt
        attempt += 1
        if attempt > 1:
            logger.warning("retry_attempt", source_name=source_name, attempt_number=attempt)
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response

    return _fetch()


def collect_sources(
    sources: List[Source],
    *,
    category: str,
    limit_per_source: int = 30,
    timeout: int = 15,
) -> Tuple[List[Article], List[str]]:
    """Fetch items from all configured sources, returning articles and errors."""
    articles: List[Article] = []
    errors: List[str] = []

    for source in sources:
        try:
            articles.extend(_collect_single(source, category=category, limit=limit_per_source, timeout=timeout))
        except Exception as exc:  # noqa: BLE001 - surface errors to the caller
            error_msg = f"{source.name}: {exc}"
            logger.error("fetch_failed", source_name=source.name, error=str(exc))
            errors.append(error_msg)

    return articles, errors


def _collect_single(
    source: Source,
    *,
    category: str,
    limit: int,
    timeout: int,
) -> List[Article]:
    if source.type.lower() != "rss":
        raise ValueError(f"Unsupported source type '{source.type}'. Only 'rss' is supported in the template.")

    logger.info("fetching_source", source_name=source.name, url=source.url)
    response = _fetch_url_with_retry(source.url, timeout, source.name)

    feed = feedparser.parse(response.content)
    items: List[Article] = []

    for entry in feed.entries[:limit]:
        published = _extract_datetime(entry)
        summary = entry.get("summary", "") or entry.get("description", "") or ""

        items.append(
            Article(
                title=(entry.get("title") or "").strip() or "(no title)",
                link=(entry.get("link") or "").strip(),
                summary=summary.strip(),
                published=published,
                source=source.name,
                category=category,
            )
        )

    return items


def _extract_datetime(entry: dict) -> datetime | None:
    """Parse a feed entry date into a timezone-aware datetime."""
    if entry.get("published_parsed"):
        return datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)
    if entry.get("updated_parsed"):
        return datetime.fromtimestamp(time.mktime(entry.updated_parsed), tz=timezone.utc)

    for key in ("published", "updated", "date"):
        raw = entry.get(key)
        if raw:
            try:
                dt = parsedate_to_datetime(str(raw))
                if dt and dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                continue
    return None
