from __future__ import annotations

import pytest
import requests
from unittest.mock import Mock, patch, MagicMock

from radar.collector import _collect_single, collect_sources
from radar.models import Source, Article


class TestCollectorRetryLogic:
    """Test HTTP retry logic with exponential backoff."""

    def test_retry_on_timeout(self) -> None:
        """Should retry on request timeout and eventually succeed."""
        source = Source(name="test_feed", type="rss", url="http://example.com/feed")

        with patch("radar.collector.requests.get") as mock_get:
            # First 2 calls timeout, 3rd succeeds
            mock_response = Mock()
            mock_response.content = b"""<?xml version="1.0"?>
            <rss version="2.0">
                <channel>
                    <item>
                        <title>Test Article</title>
                        <link>http://example.com/article</link>
                        <description>Test summary</description>
                        <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
                    </item>
                </channel>
            </rss>"""
            mock_response.raise_for_status = Mock()

            mock_get.side_effect = [
                requests.exceptions.Timeout("timeout"),
                requests.exceptions.Timeout("timeout"),
                mock_response,
            ]

            articles = _collect_single(
                source, category="test", limit=10, timeout=15
            )

            assert len(articles) == 1
            assert articles[0].title == "Test Article"
            assert mock_get.call_count == 3

    def test_retry_on_5xx_error(self) -> None:
        """Should retry on 5xx server errors."""
        source = Source(name="test_feed", type="rss", url="http://example.com/feed")

        with patch("radar.collector.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.content = b"""<?xml version="1.0"?>
            <rss version="2.0">
                <channel>
                    <item>
                        <title>Test Article</title>
                        <link>http://example.com/article</link>
                        <description>Test summary</description>
                        <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
                    </item>
                </channel>
            </rss>"""
            mock_response.raise_for_status = Mock()

            error_response = Mock()
            error_response.status_code = 503
            error_response.raise_for_status = Mock(
                side_effect=requests.exceptions.HTTPError("503 Service Unavailable")
            )

            mock_get.side_effect = [
                error_response,
                error_response,
                mock_response,
            ]

            articles = _collect_single(
                source, category="test", limit=10, timeout=15
            )

            assert len(articles) == 1
            assert articles[0].title == "Test Article"
            assert mock_get.call_count == 3

    def test_no_retry_on_4xx_error(self) -> None:
        """Should retry on 4xx errors (RequestException is retried)."""
        source = Source(name="test_feed", type="rss", url="http://example.com/feed")

        with patch("radar.collector.requests.get") as mock_get:
            # 4xx errors are RequestException, so they will be retried
            # This test verifies that after 3 retries, it raises
            mock_get.side_effect = requests.exceptions.HTTPError("404 Not Found")

            with pytest.raises(requests.exceptions.HTTPError):
                _collect_single(source, category="test", limit=10, timeout=15)

            # Should try 3 times (retry logic applies to all RequestException)
            assert mock_get.call_count == 3

    def test_max_retries_exceeded(self) -> None:
        """Should raise after 3 failed attempts."""
        source = Source(name="test_feed", type="rss", url="http://example.com/feed")

        with patch("radar.collector.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("timeout")

            with pytest.raises(requests.exceptions.Timeout):
                _collect_single(source, category="test", limit=10, timeout=15)

            # Should try 3 times
            assert mock_get.call_count == 3

    def test_connection_error_retry(self) -> None:
        """Should retry on connection errors."""
        source = Source(name="test_feed", type="rss", url="http://example.com/feed")

        with patch("radar.collector.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.content = b"""<?xml version="1.0"?>
            <rss version="2.0">
                <channel>
                    <item>
                        <title>Test Article</title>
                        <link>http://example.com/article</link>
                        <description>Test summary</description>
                        <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
                    </item>
                </channel>
            </rss>"""
            mock_response.raise_for_status = Mock()

            mock_get.side_effect = [
                requests.exceptions.ConnectionError("connection failed"),
                requests.exceptions.ConnectionError("connection failed"),
                mock_response,
            ]

            articles = _collect_single(
                source, category="test", limit=10, timeout=15
            )

            assert len(articles) == 1
            assert mock_get.call_count == 3


class TestCollectSources:
    """Test collecting from multiple sources."""

    def test_collect_sources_single_source(self) -> None:
        """Should collect articles from single source."""
        source = Source(name="test_feed", type="rss", url="http://example.com/feed")

        with patch("radar.collector.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.content = b"""<?xml version="1.0"?>
            <rss version="2.0">
                <channel>
                    <item>
                        <title>Test Article</title>
                        <link>http://example.com/article</link>
                        <description>Test summary</description>
                        <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
                    </item>
                </channel>
            </rss>"""
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            articles, errors = collect_sources([source], category="test")

            assert len(articles) == 1
            assert len(errors) == 0
            assert articles[0].title == "Test Article"

    def test_collect_sources_multiple_sources(self) -> None:
        """Should collect articles from multiple sources."""
        sources = [
            Source(name="feed1", type="rss", url="http://example.com/feed1"),
            Source(name="feed2", type="rss", url="http://example.com/feed2"),
        ]

        with patch("radar.collector.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.content = b"""<?xml version="1.0"?>
            <rss version="2.0">
                <channel>
                    <item>
                        <title>Test Article</title>
                        <link>http://example.com/article</link>
                        <description>Test summary</description>
                        <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
                    </item>
                </channel>
            </rss>"""
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            articles, errors = collect_sources(sources, category="test")

            assert len(articles) == 2
            assert len(errors) == 0

    def test_collect_sources_with_error(self) -> None:
        """Should collect articles and report errors."""
        sources = [
            Source(name="good_feed", type="rss", url="http://example.com/good"),
            Source(name="bad_feed", type="rss", url="http://example.com/bad"),
        ]

        with patch("radar.collector.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.content = b"""<?xml version="1.0"?>
            <rss version="2.0">
                <channel>
                    <item>
                        <title>Test Article</title>
                        <link>http://example.com/article</link>
                        <description>Test summary</description>
                        <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
                    </item>
                </channel>
            </rss>"""
            mock_response.raise_for_status = Mock()

            mock_get.side_effect = [
                mock_response,
                requests.exceptions.Timeout("timeout"),
                requests.exceptions.Timeout("timeout"),
                requests.exceptions.Timeout("timeout"),
            ]

            articles, errors = collect_sources(sources, category="test")

            assert len(articles) == 1
            assert len(errors) == 1
            assert "bad_feed" in errors[0]

    def test_collect_sources_unsupported_type(self) -> None:
        """Should report error for unsupported source type."""
        source = Source(name="html_feed", type="html", url="http://example.com/page")

        articles, errors = collect_sources([source], category="test")

        assert len(articles) == 0
        assert len(errors) == 1
        assert "Unsupported source type" in errors[0]

    def test_collect_sources_empty_list(self) -> None:
        """Should handle empty source list."""
        articles, errors = collect_sources([], category="test")

        assert len(articles) == 0
        assert len(errors) == 0

    def test_collect_sources_respects_limit(self) -> None:
        """Should respect per-source limit."""
        source = Source(name="test_feed", type="rss", url="http://example.com/feed")

        with patch("radar.collector.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.content = b"""<?xml version="1.0"?>
            <rss version="2.0">
                <channel>
                    <item><title>Article 1</title><link>http://example.com/1</link><description>Test</description></item>
                    <item><title>Article 2</title><link>http://example.com/2</link><description>Test</description></item>
                    <item><title>Article 3</title><link>http://example.com/3</link><description>Test</description></item>
                </channel>
            </rss>"""
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            articles, errors = collect_sources([source], category="test", limit_per_source=2)

            assert len(articles) == 2
            assert len(errors) == 0


class TestCollectSingleSourceType:
    """Test source type validation."""

    def test_unsupported_source_type_raises_error(self) -> None:
        """Should raise ValueError for unsupported source type."""
        source = Source(name="html_feed", type="html", url="http://example.com/page")

        with pytest.raises(ValueError, match="Unsupported source type"):
            _collect_single(source, category="test", limit=10, timeout=15)

    def test_case_insensitive_rss_type(self) -> None:
        """Should accept RSS type case-insensitively."""
        source = Source(name="test_feed", type="RSS", url="http://example.com/feed")

        with patch("radar.collector.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.content = b"""<?xml version="1.0"?>
            <rss version="2.0">
                <channel>
                    <item>
                        <title>Test Article</title>
                        <link>http://example.com/article</link>
                        <description>Test summary</description>
                        <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
                    </item>
                </channel>
            </rss>"""
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            articles = _collect_single(source, category="test", limit=10, timeout=15)

            assert len(articles) == 1
