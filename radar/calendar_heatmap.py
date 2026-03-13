from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import plotly.graph_objects as go


def build_calendar_heatmap(articles: list[dict[str, Any]], days_back: int = 90) -> str:
    """
    Build a calendar heatmap showing game release dates over the last N days.

    Returns HTML string with embedded Plotly figure.

    Args:
        articles: List of article dicts with 'published' ISO datetime strings
        days_back: Number of days to include (default 90)

    Returns:
        HTML string containing the Plotly heatmap
    """
    # Parse dates and build week/day matrix
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=days_back)

    # Initialize matrix: weeks (rows) x days (cols)
    # We'll use a dict to handle sparse data
    heatmap_data: dict[tuple[int, int], int] = {}

    for article in articles:
        published_str = article.get("published") or article.get("published_at")
        if not published_str:
            continue

        try:
            # Parse ISO format datetime
            if isinstance(published_str, str):
                # Handle ISO format with or without timezone
                if published_str.endswith("Z"):
                    published_str = published_str[:-1] + "+00:00"
                published = datetime.fromisoformat(published_str)
            else:
                published = published_str

            # Ensure timezone-aware
            if published.tzinfo is None:
                published = published.replace(tzinfo=UTC)

            # Skip if outside range
            if published < cutoff or published > now:
                continue

            # Calculate week of year and day of week
            week_num = published.isocalendar()[1]
            day_of_week = published.weekday()  # 0=Monday, 6=Sunday

            key = (week_num, day_of_week)
            heatmap_data[key] = heatmap_data.get(key, 0) + 1
        except (ValueError, AttributeError):
            continue

    # Build matrix for Plotly
    # Get range of weeks present
    if not heatmap_data:
        # Return empty figure if no data
        fig = go.Figure()
        fig.add_annotation(text="No data available", showarrow=False)
        html_str = fig.to_html(include_plotlyjs=False, div_id="calendarHeatmap")
        return str(html_str)

    weeks = sorted(set(k[0] for k in heatmap_data.keys()))
    min_week = weeks[0]
    max_week = weeks[-1]

    # Create matrix: rows=weeks, cols=days (0=Monday, 6=Sunday)
    z_data = []
    week_labels = []

    for week in range(min_week, max_week + 1):
        row = []
        for day in range(7):
            row.append(heatmap_data.get((week, day), 0))
        z_data.append(row)
        week_labels.append(f"W{week}")

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # Create Plotly heatmap
    fig = go.Figure(
        data=go.Heatmap(
            z=z_data,
            x=day_names,
            y=week_labels,
            colorscale="YlOrRd",
            hovertemplate="Week %{y}<br>%{x}<br>%{z} releases<extra></extra>",
            colorbar=dict(
                title="Releases",
                thickness=16,
                len=0.7,
                tickfont=dict(size=11, color="rgba(233,238,251,.72)"),
                tickcolor="rgba(233,238,251,.72)",
            ),
        )
    )

    fig.update_layout(
        title="",
        xaxis=dict(
            title="",
            tickfont=dict(size=11, color="rgba(233,238,251,.72)"),
            showgrid=False,
            side="bottom",
        ),
        yaxis=dict(
            title="",
            tickfont=dict(size=11, color="rgba(233,238,251,.72)"),
        ),
        margin=dict(l=80, r=60, t=20, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="var(--sans)", color="rgba(233,238,251,.72)"),
        hovermode="closest",
        height=400,
    )

    html_str = fig.to_html(include_plotlyjs=False, div_id="calendarHeatmap")
    return str(html_str)
