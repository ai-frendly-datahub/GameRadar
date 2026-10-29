from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from radar.collector import (
    GAMERADAR_USER_AGENT,
    _collect_single,
    _robots_permits,
    classify_stored_link,
)
from radar.exceptions import SourceError
from radar.models import Source

_FIXTURE = Path("tests/fixtures/article_links.xml").read_bytes()
_ROBOTS = Path("tests/fixtures/robots_disallow.txt").read_text(encoding="utf-8")
_FEED_URL = "https://www.gamedeveloper.com/rss.xml"


def test_collect_single_keeps_each_items_own_absolute_url() -> None:
    source = Source(name="Game Developer", type="rss", url=_FEED_URL)
    response = Mock()
    response.content = _FIXTURE
    response.raise_for_status = Mock()

    with patch("radar.collector.requests.get", return_value=response):
        articles = _collect_single(source, category="game", limit=20, timeout=15)

    assert [(article.title, article.link) for article in articles] == [
        ("Relative article", "https://www.gamedeveloper.com/news/own-article"),
        ("BitSummit", "https://bitsummit.org"),
        ("Game Conference MX", "https://www.gameconferencemx.com"),
        ("PAX West", "https://west.paxsite.com"),
        ("Joined host path", "https://games.london"),
        ("Real business story", "https://www.gamedeveloper.com/business/real-story"),
        ("From the index", "https://www.gamedeveloper.com/news/from-guid"),
        ("Episode with article guid", "http://games.ign.com/articles/122/1226317p1.html"),
        ("Ordinary article", "https://www.gamedeveloper.com/programming/ordinary-article"),
    ]


def test_classify_stored_link_matches_audit_rules() -> None:
    assert (
        classify_stored_link("https://www.gamedeveloper.combitsummit.org", _FEED_URL)
        == "glued_or_relative_host"
    )
    assert (
        classify_stored_link(
            "https://www.podtrac.com/pts/redirect.mp3/mgln.ai/e/495/pscrb.fm/rss/p/file.mp3",
            "https://feeds.megaphone.fm/gamescoop",
        )
        == "feed_redirect"
    )
    assert classify_stored_link("https://www.stitcher.com", _FEED_URL) == "list_index_or_feed"
    assert classify_stored_link("/news/story", _FEED_URL) == "relative"
    assert classify_stored_link("", _FEED_URL) == "missing"
    assert (
        classify_stored_link(
            "https://www.gamedeveloper.com/programming/ordinary-article",
            _FEED_URL,
        )
        is None
    )


def test_robots_disallow_does_not_fetch_the_feed(real_robots_permits: None) -> None:
    del real_robots_permits
    source = Source(name="Blocked", type="rss", url="https://example.com/private-feed")
    seen: list[str] = []

    def _get(url: str, **kwargs: object) -> Mock:
        seen.append(url)
        assert kwargs["verify"] is True
        headers = kwargs["headers"]
        assert isinstance(headers, dict)
        assert headers["User-Agent"] == GAMERADAR_USER_AGENT
        assert "Mozilla" not in str(headers["User-Agent"])
        response = Mock()
        response.status_code = 200
        response.text = _ROBOTS
        response.content = _ROBOTS.encode()
        return response

    with (
        patch("radar.collector.requests.get", side_effect=_get),
        pytest.raises(SourceError, match="robots.txt disallows"),
    ):
        _collect_single(source, category="game", limit=5, timeout=15)

    assert seen == ["https://example.com/robots.txt"]


def test_robots_404_still_fetches_the_feed(real_robots_permits: None) -> None:
    del real_robots_permits
    source = Source(name="Open", type="rss", url="https://example.com/feed.xml")
    seen: list[str] = []

    def _get(url: str, **_kwargs: object) -> Mock:
        seen.append(str(url))
        response = Mock()
        response.raise_for_status = Mock()
        if str(url).endswith("/robots.txt"):
            response.status_code = 404
            response.text = "missing"
            response.content = b"missing"
            return response
        response.status_code = 200
        response.content = b"""<?xml version="1.0"?>
        <rss version="2.0"><channel><item>
          <title>Allowed story</title>
          <link>https://example.com/news/allowed-story</link>
          <description>Body</description>
        </item></channel></rss>"""
        return response

    with patch("radar.collector.requests.get", side_effect=_get):
        articles = _collect_single(source, category="game", limit=5, timeout=15)

    assert seen == ["https://example.com/robots.txt", "https://example.com/feed.xml"]
    assert [article.link for article in articles] == ["https://example.com/news/allowed-story"]


def test_robots_transport_error_does_not_invent_a_block(real_robots_permits: None) -> None:
    del real_robots_permits
    with patch(
        "radar.collector.requests.get",
        side_effect=requests.exceptions.ConnectionError("robots down"),
    ):
        assert (
            _robots_permits(
                "https://example.com/feed.xml",
                session=None,
                timeout=5,
            )
            is True
        )
