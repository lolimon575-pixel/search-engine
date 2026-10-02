import asyncio
import threading

import httpx
import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.mark.parametrize("route,target,result", [
    ("/api/search?q=test", "search", ([], [])),
    ("/api/suggest?q=test", "suggest", []),
    ("/api/organization?domain=example.com", "profile", None),
    ("/api/verification?url=https://example.com/", "verify", {"status": "VERIFIED"}),
])
def test_slow_requests_do_not_block_other_endpoints(monkeypatch, route, target, result):
    entered, release = threading.Event(), threading.Event()

    def slow(*args, **kwargs):
        entered.set()
        release.wait(1)
        return result

    monkeypatch.setattr(main, "get_stats", lambda: {"sites": 97})
    if target == "search":
        monkeypatch.setattr(main.web_search, "search", slow)
    elif target == "suggest":
        monkeypatch.setattr(main, "get_suggestions", slow)
    elif target == "profile":
        monkeypatch.setattr(main, "get_organization_profile", slow)
    else:
        monkeypatch.setattr(main.web_search.verifier, "verify", slow)

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test") as client:
            pending = asyncio.create_task(client.get(route))
            while not entered.is_set():
                await asyncio.sleep(0.005)
            try:
                response = await client.get("/api/registry/stats")
                assert response.status_code == 200
                assert not pending.done(), "A slow request blocked the entire API"
            finally:
                release.set()
                await pending

    asyncio.run(exercise())


def test_registry_endpoint_exposes_only_public_fields(monkeypatch):
    monkeypatch.setattr(main, "get_site", lambda domain: {
        "domain": domain, "url": "https://example.com", "organization": "Example",
        "billing_status": "active", "stripe_customer_id": "cus_private",
        "stripe_subscription_id": "sub_private", "profile_settings": {"draft": "private"},
        "internal_note": "private",
    })
    response = TestClient(main.app).get("/api/registry/site?domain=example.com")
    assert response.status_code == 200
    site = response.json()["site"]
    assert site["organization"] == "Example"
    assert site["billing_status"] == "active"
    assert "stripe_customer_id" not in site
    assert "stripe_subscription_id" not in site
    assert "profile_settings" not in site
    assert "internal_note" not in site


@pytest.mark.parametrize("route", ["/api/organization", "/api/registry/site"])
def test_malformed_domains_return_a_validation_error(route):
    response = TestClient(main.app).get(route, params={"domain": "https://[broken"})
    assert response.status_code == 400


def test_upstream_search_failure_is_distinct_from_an_empty_result(monkeypatch):
    monkeypatch.setattr(main.web_search, "search", lambda *args, **kwargs: ([], ["duckduckgo: ConnectError"]))
    client = TestClient(main.app)
    failed = client.get("/api/search?q=test")
    assert failed.status_code == 503
    assert "ConnectError" not in failed.text
    monkeypatch.setattr(main.web_search, "search", lambda *args, **kwargs: ([], []))
    empty = client.get("/api/search?q=test")
    assert empty.status_code == 200
    assert empty.json()["results"] == []


def test_original_query_can_be_searched_without_repeating_correction(monkeypatch):
    from app.websearch.service import WebSearchService
    service = WebSearchService(max_check_jobs=0)
    monkeypatch.setattr(main, "web_search", service)
    try:
        client = TestClient(main.app)
        corrected = client.get("/api/search", params={"q": "pumma", "engine": "index"})
        assert corrected.json()["corrected_query"] == "PUMA"
        assert corrected.json()["results"][0]["url"] == "https://puma.com/"
        original = client.get("/api/search", params={"q": "pumma", "engine": "index", "autocorrect": "false"})
        assert original.status_code == 200
        assert original.json()["corrected_query"] is None
        assert original.json()["results"] == []
    finally:
        service.close()
