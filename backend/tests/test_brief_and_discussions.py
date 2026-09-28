from app.websearch.brief import build_brief
from app.websearch.models import WebResult
from app.websearch.query_features import discussion_query, is_discussion_url


def result(title, url, description):
    return WebResult(title=title, url=url, description=description, provider_rank=1)


def test_discussion_query_targets_human_sources():
    query = discussion_query("python packaging")
    assert "site:reddit.com" in query
    assert "site:stackoverflow.com" in query
    assert is_discussion_url("https://news.ycombinator.com/item?id=1")
    assert not is_discussion_url("https://example.com/article")


def test_brief_requires_multiple_distinct_sources():
    items = [
        result("Guide A", "https://a.example/guide", "Python packaging guide explains wheels, source distributions and publishing packages."),
        result("Guide B", "https://b.example/guide", "Python packaging documentation covers project metadata, builds and package indexes."),
    ]
    brief = build_brief("how python packaging works", items)
    assert brief is not None
    assert brief["kind"] == "extractive"
    assert len(brief["passages"]) == 2


def test_brief_avoids_single_source_answer():
    items = [
        result("Guide A", "https://a.example/one", "Python packaging guide explains wheels, source distributions and publishing packages."),
        result("Guide A2", "https://a.example/two", "More Python packaging information from the same website and the same publisher."),
    ]
    assert build_brief("how python packaging works", items) is None
