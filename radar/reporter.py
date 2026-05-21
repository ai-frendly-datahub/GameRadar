from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any, cast

from radar_core.ontology import build_summary_ontology_metadata
from radar_core.report_utils import (
    generate_index_html as _core_generate_index_html,
)
from radar_core.report_utils import (
    generate_report as _core_generate_report,
)

from .models import Article, CategoryConfig


def _count_entities(articles: Iterable[Article]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for article in articles:
        matched = article.matched_entities or {}
        if not isinstance(matched, dict):
            continue
        for entity_name, keywords in matched.items():
            if not isinstance(entity_name, str) or not entity_name:
                continue
            if isinstance(keywords, list):
                counts[entity_name] += len(keywords)
            else:
                counts[entity_name] += 1
    return counts


def generate_report(
    *,
    category: CategoryConfig,
    articles: Iterable[Article],
    output_path: Path,
    stats: dict[str, int],
    errors: list[str] | None = None,
    store: Any = None,
    quality_report: Mapping[str, Any] | None = None,
) -> Path:
    """Generate HTML report (delegates to radar-core)."""
    articles_list = list(articles)
    plugin_charts = []

    # --- Universal plugins (entity heatmap + source reliability) ---
    try:
        from radar_core.plugins.entity_heatmap import get_chart_config as _heatmap_config

        _heatmap = _heatmap_config(articles=articles_list)
        if _heatmap is not None:
            plugin_charts.append(_heatmap)
    except Exception:
        pass
    try:
        from radar_core.plugins.source_reliability import get_chart_config as _reliability_config

        _reliability = _reliability_config(store=store)
        if _reliability is not None:
            plugin_charts.append(_reliability)
    except Exception:
        pass

    report_path = _core_generate_report(
        category=category,
        articles=articles_list,
        output_path=output_path,
        stats=stats,
        errors=errors,
        plugin_charts=cast(Any, plugin_charts if plugin_charts else None),
        ontology_metadata=build_summary_ontology_metadata(
            "GameRadar",
            category_name=category.category_name,
            search_from=Path(__file__).resolve(),
        ),
    )
    if quality_report:
        _inject_game_quality_panel(report_path, category.category_name, quality_report)
    return report_path


def _inject_game_quality_panel(
    report_path: Path,
    category_name: str,
    quality_report: Mapping[str, Any],
) -> None:
    panel = _render_game_quality_panel(quality_report)
    targets = {report_path}
    date_stamp = datetime.now(UTC).strftime("%Y%m%d")
    dated_path = report_path.parent / f"{category_name}_{date_stamp}.html"
    if dated_path.exists():
        targets.add(dated_path)

    for target in targets:
        if target.exists():
            html = target.read_text(encoding="utf-8")
            marker = '<section id="entities"'
            if panel in html:
                continue
            if marker in html:
                html = html.replace(marker, panel + "\n      " + marker, 1)
            else:
                html = html.replace("</main>", panel + "\n      </main>", 1)
            target.write_text(html, encoding="utf-8")


def _render_game_quality_panel(quality_report: Mapping[str, Any]) -> str:
    summary = quality_report.get("summary", {})
    if not isinstance(summary, Mapping):
        summary = {}
    events = quality_report.get("events", [])
    event_rows = events if isinstance(events, list) else []
    review_items = quality_report.get("daily_review_items", [])
    review_rows = review_items if isinstance(review_items, list) else []
    chips = [
        ("events", summary.get("actionable_game_event_count", 0)),
        ("keys", summary.get("canonical_game_key_present_count", 0)),
        ("key gaps", summary.get("missing_canonical_game_key_count", 0)),
        ("field gaps", summary.get("event_required_field_gap_count", 0)),
        ("review", summary.get("daily_review_item_count", 0)),
    ]
    chip_html = "\n".join(
        f'              <span class="chip"><strong>{escape(label)}</strong> {escape(str(value))}</span>'
        for label, value in chips
    )
    event_html = _render_game_quality_events(event_rows[:6])
    review_html = _render_game_quality_reviews(review_rows[:6])
    return f"""
      <section id="game-quality" class="section" aria-label="Game quality">
        <div class="section-hd">
          <h2>Game Quality</h2>
          <div class="right">
            <span>{escape(str(quality_report.get("generated_at", "")))}</span>
          </div>
        </div>
        <div class="table-wrap">
          <div class="panel">
            <p>{escape(str(quality_report.get("scope_note", "")))}</p>
            <div class="row" aria-label="Game quality summary">
{chip_html}
            </div>
            <h3>Actionable Events</h3>
{event_html}
            <h3>Daily Review</h3>
{review_html}
          </div>
        </div>
      </section>""".rstrip()


def _render_game_quality_events(rows: list[Any]) -> str:
    if not rows:
        return "            <p>No actionable game events.</p>"
    items: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        event_model = escape(str(row.get("event_model", "")))
        key = escape(str(row.get("canonical_game_key") or row.get("canonical_game_key_status", "")))
        title = escape(str(row.get("title", "")))
        items.append(f"<li><strong>{event_model}</strong> {key}: {title}</li>")
    return "            <ul>" + "\n".join(items) + "</ul>"


def _render_game_quality_reviews(rows: list[Any]) -> str:
    if not rows:
        return "            <p>No daily review items.</p>"
    items: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        reason = _list_text(row.get("reason"))
        key = escape(str(row.get("canonical_game_key") or row.get("game_event_key", "")))
        title = escape(str(row.get("title", "")))
        items.append(f"<li><strong>{reason}</strong> {key}: {title}</li>")
    return "            <ul>" + "\n".join(items) + "</ul>"


def _list_text(value: Any) -> str:
    if isinstance(value, list):
        return escape(", ".join(str(item) for item in value))
    return escape(str(value))


def generate_index_html(
    report_dir: Path,
    summaries_dir: Path | None = None,
) -> Path:
    """Generate index.html (delegates to radar-core)."""
    radar_name = "Game Radar"
    return _core_generate_index_html(report_dir, radar_name)
