from concurrent.futures import ThreadPoolExecutor
import threading
import time
from fastapi.testclient import TestClient
from app import main
from app.verification.engine import VerificationEngine
from app.verification import officiality
from app.websearch.local_index import LocalIndex
from app.websearch.models import WebResult
from app.websearch.service import WebSearchService, SearchBatch


def wait_for(predicate):
    deadline = time.monotonic() + 3
    while not predicate():
        assert time.monotonic() < deadline, "Background work didn't finish"
        threading.Event().wait(0.005)


def service(**kwargs):
    result = WebSearchService(**kwargs)
    result.ledger = type("SilentLedger", (), {"append": lambda *_: None})()
    return result


def test_first_results_wait_for_neither_provider_nor_verification():
    web_entered, check_entered, release = threading.Event(), threading.Event(), threading.Event()
    def provider(*args, **kwargs):
        web_entered.set(); release.wait(3)
        return [WebResult(title="PUMA new", url="https://puma.com/new")]
    class BlockingVerifier(VerificationEngine):
        def verify(self, url, **kwargs):
            check_entered.set(); release.wait(3)
            data = {**self.preview(url), "status": "VERIFIED", "pending": False}
            with self.cache_lock:
                self.cache[url] = {"ts": time.time(), "data": data}
            return data
    s = service(provider=provider, verifier=BlockingVerifier())
    try:
        batch = s.search("puma")
        assert batch.results[0].url == "https://puma.com/"
        assert batch.search_pending and batch.verification_pending
        assert batch.results[0].verification["status"] == "UNKNOWN"
        assert batch.results[0].verification["officiality"]["status"] == "CONFIRMED"
        assert web_entered.wait(1) and check_entered.wait(1)
        assert not release.is_set()
        release.set(); wait_for(lambda: s.web_jobs == 0 and not s.jobs)
        assert any(row.url == "https://puma.com/new" for row in s.search("puma").results)
    finally:
        release.set(); s.close()


def test_index_only_never_calls_provider_and_snapshots_are_detached():
    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected web request")
    s = service(provider=forbidden, max_check_jobs=0)
    try:
        first = s.search("авто ру", engine="index")
        assert not first.search_pending and not first.errors
        first.results[0].verification["officiality"]["organization"] = "Changed"
        first.results[0].title = "Changed"
        second = s.search("авто ру", engine="index")
        assert second.results[0].title == "Авто.ру"
        assert second.results[0].verification["officiality"]["organization"] == "Авто.ру"
    finally:
        s.close()


def test_identical_concurrent_queries_start_one_provider_job():
    entered, release, calls = threading.Event(), threading.Event(), []
    def provider(*args, **kwargs):
        calls.append(args[0]); entered.set(); release.wait(3); return []
    s = service(provider=provider, max_check_jobs=0)
    try:
        with ThreadPoolExecutor(max_workers=16) as workers:
            batches = list(workers.map(lambda _: s.search("puma"), range(32)))
        assert entered.wait(1)
        assert len(calls) == 1 and all(b.search_pending for b in batches)
    finally:
        release.set(); s.close()


def test_cache_and_network_queues_have_hard_bounds():
    release = threading.Event()
    s = service(index=LocalIndex(registry={}), provider=lambda *a, **k: (release.wait(3) and []), max_cache=4, max_web_jobs=2, max_check_jobs=0)
    try:
        batches = [s.search(f"test {i}", autocorrect=False) for i in range(40)]
        assert len(s.cache) == 4 and s.web_jobs == 2
        assert sum(b.search_pending for b in batches) == 2
        assert batches[-1].errors == ["web: busy"]
    finally:
        release.set(); s.close()


def test_expired_search_cannot_be_overwritten_by_old_provider_job():
    entered = [threading.Event(), threading.Event()]
    releases = [threading.Event(), threading.Event()]
    calls = []
    def provider(*args, **kwargs):
        n = len(calls); calls.append(n); entered[n].set(); releases[n].wait(3)
        return [WebResult(title="old" if n == 0 else "new", url=f"https://example.com/{n}")]
    s = service(index=LocalIndex(registry={}), provider=provider, max_check_jobs=0)
    try:
        s.search("sample", autocorrect=False); assert entered[0].wait(1)
        next(iter(s.cache.values()))["at"] -= 100
        s.search("sample", autocorrect=False); assert entered[1].wait(1)
        releases[0].set(); wait_for(lambda: s.web_jobs == 1)
        assert s.search("sample", autocorrect=False).results == []
        releases[1].set(); wait_for(lambda: s.web_jobs == 0)
        assert s.search("sample", autocorrect=False).results[0].title == "new"
    finally:
        for release in releases: release.set()
        s.close()


def test_limit_30_is_honored_and_verified_mode_keeps_identity_separate_from_http():
    registry = {f"sample{i}.example": {"organization": "Sample"} for i in range(40)}
    s = service(index=LocalIndex(registry), max_check_jobs=0)
    try:
        assert len(s.search("sample", 30, engine="index").results) == 30
    finally:
        s.close()
    s = service(max_check_jobs=0)
    try:
        batch = s.search("puma", mode="verified", engine="index")
        assert batch.results and all(r.verification["officiality"]["status"] == "CONFIRMED" for r in batch.results)
        assert all(r.verification["status"] == "UNKNOWN" for r in batch.results)
    finally:
        s.close()


def test_preview_does_not_access_database_dns_or_http(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected blocking I/O")
    engine = VerificationEngine()
    monkeypatch.setattr(officiality, "get_site", forbidden)
    monkeypatch.setattr(engine, "_resolve_public_host", forbidden)
    preview = engine.preview("https://puma.com/")
    assert preview["officiality"]["status"] == "CONFIRMED"
    assert preview["status"] == "UNKNOWN" and preview["checked_at"] is None
    assert not preview["technical"]


def test_cached_checks_are_used_without_mutating_the_cache():
    engine = VerificationEngine()
    engine.cache["https://puma.com/"] = {"ts": time.time(), "data": {"status": "VERIFIED", "technical": {"http_status": 200}}}
    first = engine.preview("https://puma.com/")
    first["technical"]["http_status"] = 503
    assert engine.preview("https://puma.com/")["technical"]["http_status"] == 200


def test_api_pending_response_is_not_an_empty_or_failed_search(monkeypatch):
    monkeypatch.setattr(main.web_search, "search", lambda *a, **k: SearchBatch([], [], "sample", search_pending=True))
    response = TestClient(main.app).get("/api/search?q=sample")
    assert response.status_code == 200
    assert response.json()["search_pending"] is True
    assert response.json()["index"]["curated"] >= 300
    assert TestClient(main.app).get("/api/search?q=x&engine=invalid").status_code == 422


def test_remote_correction_is_background_only_and_keeps_original_cache_key(monkeypatch):
    from app.websearch import service as module
    monkeypatch.setattr(module, 'suggest_correction', lambda query: 'corrected')
    calls = []
    def provider(query, *args, **kwargs):
        calls.append(query)
        return [] if query == 'misspelled phrase' else [WebResult(title='corrected', url='https://example.com/corrected')]
    s = service(index=LocalIndex(registry={}), provider=provider, max_check_jobs=0)
    try:
        s.search('misspelled phrase')
        wait_for(lambda: s.web_jobs == 0)
        batch = s.search('misspelled phrase')
        assert batch.corrected_query == 'corrected'
        assert batch.searched_query == 'corrected'
        assert calls == ['misspelled phrase', 'corrected']
        s.search('misspelled phrase', autocorrect=False)
        wait_for(lambda: s.web_jobs == 0)
        assert calls == ['misspelled phrase', 'corrected', 'misspelled phrase']
    finally:
        s.close()


def test_failed_checks_are_not_restarted_on_every_poll():
    class BrokenVerifier(VerificationEngine):
        def verify(self, url, **kwargs):
            raise RuntimeError('offline')
    s = service(verifier=BrokenVerifier())
    try:
        s.search('github docs', engine='index')
        wait_for(lambda: not s.jobs)
        batch = s.search('github docs', engine='index')
        assert not batch.verification_pending
        assert batch.results[0].verification['status'] == 'WARNING'
    finally:
        s.close()


def test_background_verification_prioritizes_only_the_requested_result_count():
    release = threading.Event()
    class BlockingVerifier(VerificationEngine):
        def verify(self, url, **kwargs):
            release.wait(3)
            return {**self.preview(url), 'status': 'VERIFIED', 'pending': False}
    s = service(index=LocalIndex(registry={}), verifier=BlockingVerifier(),
                provider=lambda *a, **k: [WebResult(title='sample', url=f'https://example.com/{i}') for i in range(40)])
    try:
        s.search('sample', limit=10)
        wait_for(lambda: s.web_jobs == 0)
        assert len(s.jobs) == 10
        assert len(s.search('sample', limit=30).results) == 30
        assert len(s.jobs) == 30
    finally:
        release.set(); s.close()
