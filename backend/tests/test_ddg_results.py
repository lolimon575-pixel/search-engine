from urllib.parse import quote

import pytest

from app.websearch.ddg import Parser


def test_organic_redirect_preserves_encoded_query_characters_and_description():
    target = "https://example.com/search?q=shoes%26bags"
    parser = Parser()
    parser.feed('<a class="result__a" href="//duckduckgo.com/l/?uddg=' + quote(target, safe="") + '">Shop <b>catalog</b></a><div class="result__snippet">Official catalog</div>')
    assert parser.items == [["Shop catalog", target, "Official catalog"]]


@pytest.mark.parametrize("host", ["duckduckgo.com", "links.duckduckgo.com"])
def test_ad_redirect_is_excluded_without_attaching_its_snippet_to_an_organic_result(host):
    parser = Parser()
    parser.feed('<a class="result__a" href="https://example.com">Organic</a>')
    parser.feed('<a class="result__a" href="https://' + host + '/y.js?ad_domain=shop.com">Sponsored sale</a><div class="result__snippet">Ad description</div>')
    assert parser.items == [["Organic", "https://example.com", ""]]


@pytest.mark.parametrize("url", ["https://[broken", "javascript:alert(1)", "https://user:pass@example.com"])
def test_invalid_result_does_not_break_the_search_or_pollute_another_description(url):
    parser = Parser()
    parser.feed('<a class="result__a" href="' + url + '">Invalid</a><div class="result__snippet">Invalid snippet</div>')
    parser.feed('<a class="result__a" href="https://example.com">Valid</a><div class="result__snippet">Valid snippet</div>')
    assert parser.items == [["Valid", "https://example.com", "Valid snippet"]]


def test_lookalike_provider_host_is_not_treated_as_a_search_redirect():
    url = "https://fakeduckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com"
    parser = Parser()
    parser.feed('<a class="result__a" href="' + url + '">Lookalike</a>')
    assert parser.items == [["Lookalike", url, ""]]
