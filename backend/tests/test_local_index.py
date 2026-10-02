import time
import pytest
from app.websearch.local_index import LocalIndex, document_url
from app.websearch.models import WebResult
from app.nova_search import search_registry


@pytest.fixture(scope="module")
def index():
    return LocalIndex()


@pytest.mark.parametrize("query,url", [
    ("авто ру", "https://auto.ru/"), ("авито", "https://avito.ru/"),
    ("puma вакансии", "https://about.puma.com/en/careers"),
    ("github docs", "https://docs.github.com/"), ("гитхаб", "https://github.com/"),
])
def test_brand_and_section(index, query, url):
    assert index.search(query)[0].url == url
    if query == "авто ру":
        assert all("avito" not in row.url for row in index.search(query))


def test_unknown_words_and_match_syntax_are_not_operators(index):
    assert index.search("несуществующее мкщцхц") == []
    assert index.search('puma OR "avito"') == []
    assert index.search('"') == []


def test_scope_is_exact_or_a_subdomain_and_dates_are_conservative():
    idx = LocalIndex(registry={})
    for url in ["https://github.com/a", "https://docs.github.com/a", "https://fakegithub.com/a", "https://github.com.evil.org/a"]:
        idx.add(url, "example")
    assert {r.url for r in idx.search("example site:github.com")} == {"https://github.com/a", "https://docs.github.com/a"}
    assert idx.search("example", freshness="d") == []
    assert idx.search("example site:[broken") == []


def test_exact_mode_requires_a_phrase():
    idx = LocalIndex(registry={})
    idx.add("https://example.com/a", "first word", "last word")
    assert idx.search("first last")
    assert idx.search("first last", mode="exact") == []


@pytest.mark.parametrize("url", ["file:///etc/passwd", "http://127.0.0.1/", "http://192.168.0.1/", "https://user:pass@example.com/", "https://[broken", "https://localhost/"])
def test_private_or_invalid_addresses(url):
    assert not document_url(url)
    assert not LocalIndex(registry={}).add(url, "test")


def test_distinct_query_pages_and_www_addresses_remain_intact():
    idx = LocalIndex(registry={})
    urls = {"https://www.example.com/search?q=one", "https://www.example.com/search?q=two"}
    for url in urls:
        idx.add(url, "search example")
    assert {r.url for r in idx.search("search")} == urls


def test_bounded_ingestion_preserves_curated_metadata_and_expires_pages():
    idx = LocalIndex(registry={"example.com": {"organization": "Example"}}, max_documents=3)
    idx.ingest([WebResult(title="Fake organization", url="https://example.com/")])
    assert idx.search("example")[0].title == "Example"
    for i in range(10):
        idx.add(f"https://example.org/{i}", "learned", seen_at=time.time()-15*86400 if i == 9 else None)
    assert idx.stats()["documents"] == 3
    assert len(idx.search("learned")) == 1
    assert idx.search("example")[0].title == "Example"


def test_paid_metadata_does_not_change_ranking():
    registry = {"one.example": {"organization": "Same", "profile_tier": "showcase"}, "two.example": {"organization": "Same", "profile_tier": "premium"}}
    first = [(r.url, r.score) for r in LocalIndex(registry).search("same")]
    registry["one.example"]["profile_tier"], registry["two.example"]["profile_tier"] = "premium", "showcase"
    assert [(r.url, r.score) for r in LocalIndex(registry).search("same")] == first
    assert search_registry("nonexistent brand xqzk") == []


def test_local_suggestions_and_conservative_correction(index):
    assert index.suggest("гит")[0] == "GitHub"
    assert index.correction("pumma") == "PUMA"
    assert index.correction("PUMA") is None
    assert index.correction("случайный длинный запрос") is None
