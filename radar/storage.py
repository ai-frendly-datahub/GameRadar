from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Iterable, List

import duckdb

from .logger import get_logger
from .models import Article

logger = get_logger(__name__)


def _utc_naive(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert tz-aware datetime to UTC naive for DuckDB."""
    if dt is None:
        return None
    if dt.tzinfo:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


class RadarStorage:
    """DuckDB 기반 경량 스토리지."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.conn = duckdb.connect(str(self.db_path))
            self._ensure_tables()
        except duckdb.Error as exc:
            logger.error(f"Failed to connect to database at {db_path}: {exc}")
            raise

    def __enter__(self) -> RadarStorage:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Context manager exit - ensures connection is closed."""
        self.close()

    def __del__(self) -> None:
        """Destructor - safety net for connection cleanup."""
        try:
            if hasattr(self, "conn") and self.conn is not None:
                self.conn.close()
        except Exception:
            # Suppress exceptions during cleanup
            pass

    def close(self) -> None:
        """Close database connection."""
        try:
            if self.conn is not None:
                self.conn.close()
        except duckdb.Error as exc:
            logger.warning("close_failed", error=str(exc))

    def _ensure_tables(self) -> None:
        self.conn.execute(
            """
            CREATE SEQUENCE IF NOT EXISTS articles_id_seq START 1;
            CREATE TABLE IF NOT EXISTS articles (
                id BIGINT PRIMARY KEY DEFAULT nextval('articles_id_seq'),
                category TEXT NOT NULL,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                link TEXT NOT NULL UNIQUE,
                summary TEXT,
                published TIMESTAMP,
                collected_at TIMESTAMP NOT NULL,
                entities_json TEXT
            );
            """
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_category_time ON articles (category, published, collected_at);"
        )

    def upsert_articles(self, articles: Iterable[Article]) -> None:
        """중복 링크는 덮어쓰고 최신 수집 시각을 기록. 배치 처리로 최적화."""
        now = _utc_naive(datetime.now(timezone.utc))
        article_list = list(articles)
        logger.info("upserting_articles", count=len(article_list))

        if not article_list:
            return

        try:
            # 배치 처리: 중복 링크 제거 (마지막 항목만 유지)
            seen_links: dict[str, Article] = {}
            for article in article_list:
                seen_links[article.link] = article

            unique_articles = list(seen_links.values())

            # 배치 DELETE: 모든 링크를 한 번에 삭제
            links_to_delete = [article.link for article in unique_articles]
            placeholders = ",".join(["?"] * len(links_to_delete))
            self.conn.execute(f"DELETE FROM articles WHERE link IN ({placeholders})", links_to_delete)

            # 배치 INSERT: executemany()로 모든 기사를 한 번에 삽입
            insert_data: List[tuple[str, str, str, str, Optional[str], Optional[datetime], Optional[datetime], str]] = []
            for article in unique_articles:
                entities_json = json.dumps(article.matched_entities, ensure_ascii=False)
                published = _utc_naive(article.published)
                insert_data.append(
                    (
                        article.category,
                        article.source,
                        article.title,
                        article.link,
                        article.summary,
                        published,
                        now,
                        entities_json,
                    )
                )

            self.conn.executemany(
                """
                INSERT INTO articles (category, source, title, link, summary, published, collected_at, entities_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                insert_data,
            )
        except duckdb.Error as exc:
            logger.error(
                "batch_upsert_failed",
                count=len(article_list),
                error=str(exc),
            )
            # 배치 실패 시 개별 처리로 폴백
            for article in article_list:
                try:
                    entities_json = json.dumps(article.matched_entities, ensure_ascii=False)
                    published = _utc_naive(article.published)

                    self.conn.execute("DELETE FROM articles WHERE link = ?", [article.link])
                    self.conn.execute(
                        """
                        INSERT INTO articles (category, source, title, link, summary, published, collected_at, entities_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            article.category,
                            article.source,
                            article.title,
                            article.link,
                            article.summary,
                            published,
                            now,
                            entities_json,
                        ],
                    )
                except duckdb.Error as article_exc:
                    logger.error(
                        "upsert_failed",
                        article_link=article.link,
                        error=str(article_exc),
                    )
                    # Continue processing remaining articles (partial success)
                    continue

    def recent_articles(self, category: str, *, days: int = 7, limit: int = 200) -> List[Article]:
        """최근 N일 내 기사 반환."""
        since = _utc_naive(datetime.now(timezone.utc) - timedelta(days=days))
        cur = self.conn.execute(
            """
            SELECT category, source, title, link, summary, published, collected_at, entities_json
            FROM articles
            WHERE category = ? AND COALESCE(published, collected_at) >= ?
            ORDER BY COALESCE(published, collected_at) DESC
            LIMIT ?
            """,
            [category, since, limit],
        )
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]

        results: List[Article] = []
        for row in rows:
            row_map = dict(zip(columns, row))
            published = row_map.get("published")

            entities = {}
            raw_entities = row_map.get("entities_json")
            if raw_entities:
                try:
                    entities = json.loads(raw_entities)
                except json.JSONDecodeError:
                    entities = {}

            results.append(
                Article(
                    title=row_map.get("title", ""),
                    link=row_map.get("link", ""),
                    summary=row_map.get("summary") or "",
                    published=published,
                    source=row_map.get("source", ""),
                    category=row_map.get("category", ""),
                    matched_entities=entities,
                )
            )
        return results

    def delete_older_than(self, days: int) -> int:
        """보존 기간 밖 데이터 삭제."""
        cutoff = _utc_naive(datetime.now(timezone.utc) - timedelta(days=days))
        count_row = self.conn.execute(
            "SELECT COUNT(*) FROM articles WHERE COALESCE(published, collected_at) < ?", [cutoff]
        ).fetchone()
        to_delete = count_row[0] if count_row else 0
        self.conn.execute("DELETE FROM articles WHERE COALESCE(published, collected_at) < ?", [cutoff])
        if to_delete > 0:
            logger.info("retention_cleanup", deleted_count=to_delete)
        return to_delete
