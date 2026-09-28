from app.websearch.models import WebResult
from app.websearch.ranker import diversify, promote_verified_official, rank


def result(title, url, provider_rank=1, description=""):
    return WebResult(
        title=title,
        url=url,
        description=description,
        provider_rank=provider_rank,
    )


def test_exact_domain_can_outweigh_provider_position():
    items = [
        result("OpenAI overview — encyclopedia", "https://example.org/openai", 1),
        result("OpenAI", "https://openai.com/", 8),
    ]

    ranked = rank("OpenAI", items)

    assert ranked[0].url == "https://openai.com/"
    assert "domain_match" in ranked[0].rank_signals


def test_diversity_limits_repeated_domain_when_alternatives_exist():
    items = rank("nova", [
        result("NOVA one", "https://a.example/nova/one", 1),
        result("NOVA two", "https://a.example/nova/two", 2),
        result("NOVA three", "https://a.example/nova/three", 3),
        result("NOVA B", "https://b.example/nova", 4),
        result("NOVA C", "https://c.example/nova", 5),
    ])

    selected = diversify(items, 4, max_per_domain=2)
    hosts = [item.url.split("/")[2] for item in selected]

    assert hosts.count("a.example") <= 2
    assert "b.example" in hosts
    assert "c.example" in hosts


def test_confirmed_official_result_is_promoted_for_exact_organization_query():
    generic = result("GitHub guide", "https://docs.example/github", 1)
    official = result("GitHub", "https://github.com/", 7)
    official.verification = {
        "officiality": {
            "status": "OWNER_VERIFIED",
            "organization": "GitHub",
        }
    }

    items = rank("GitHub", [generic, official])
    reranked = promote_verified_official("GitHub", items)

    assert reranked[0].url == "https://github.com/"
    assert reranked[0].rank_signals[0] == "official_match"
