from app.websearch.query_features import resolve_bang, discussion_query, is_discussion_url


def test_bang_routes_to_external_search():
    url = resolve_bang("!gh nova search")
    assert url.startswith("https://github.com/search?")
    assert "nova+search" in url


def test_non_bang_query_is_not_redirected():
    assert resolve_bang("nova search") is None


def test_discussion_mode_targets_human_discussion_sources():
    query = discussion_query("python packaging")
    assert "site:reddit.com" in query
    assert "site:stackoverflow.com" in query
    assert is_discussion_url("https://news.ycombinator.com/item?id=1")
    assert not is_discussion_url("https://example.com/post")
