from __future__ import annotations

from importlib import import_module


def test_collect_browser_sources_forwards_source_config(monkeypatch) -> None:
    module = import_module("radar.browser_collector")
    source = import_module("radar.models").Source(
        name="루리웹 뉴스",
        type="javascript",
        url="https://bbs.ruliweb.com/news",
        config={"wait_for": ".board_list"},
    )
    captured: dict[str, object] = {}

    def fake_collect(*, sources, category, timeout, health_db_path):
        captured["sources"] = sources
        captured["category"] = category
        captured["timeout"] = timeout
        captured["health_db_path"] = health_db_path
        return [], []

    monkeypatch.setattr(module, "_BROWSER_COLLECTION_AVAILABLE", True)
    monkeypatch.setattr(module, "_core_collect", fake_collect)

    articles, errors = module.collect_browser_sources([source], "game")

    assert articles == []
    assert errors == []
    assert captured["category"] == "game"
    assert captured["timeout"] == 15_000
    assert captured["health_db_path"] is None
    assert captured["sources"] == [
        {
            "name": "루리웹 뉴스",
            "type": "javascript",
            "url": "https://bbs.ruliweb.com/news",
            "config": {"wait_for": ".board_list"},
        }
    ]
