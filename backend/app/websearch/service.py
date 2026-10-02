"""Progressive search: local retrieval now, bounded network work in the background."""
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import threading
import time
from urllib.parse import urlsplit, urlunsplit

from .ddg import search as ddg_search
from .correction import suggest_correction
from .local_index import LocalIndex, document_url
from . import index_storage
from .ranker import rank, diversify, promote_verified_official
from .query_features import discussion_query
from app.verification.engine import VerificationEngine
from app.verification.ledger import VerificationLedger


def canonical(url):
    valid = document_url(url)
    if not valid:
        return ""
    p = urlsplit(valid)
    return urlunsplit((p.scheme, p.netloc.removeprefix("www."), p.path.rstrip("/") or "/", p.query, ""))
OFFICIAL = {"OWNER_VERIFIED", "CONFIRMED", "EXTERNAL_CONFIRMED"}


@dataclass
class SearchBatch:
    results: list
    errors: list
    searched_query: str
    corrected_query: str | None = None
    search_pending: bool = False
    verification_pending: bool = False
    source: str = "index"
    elapsed_ms: float = 0

    def __iter__(self):
        yield self.results
        yield self.errors


class WebSearchService:
    def __init__(self, index=None, verifier=None, provider=None, max_cache=256, max_web_jobs=12, max_check_jobs=64):
        self.index = index if index is not None else LocalIndex()
        self.verifier = verifier if verifier is not None else VerificationEngine()
        self.provider = provider if provider is not None else ddg_search
        self.ledger = VerificationLedger()
        self.cache = OrderedDict()
        self.jobs = set()
        self.lock = threading.RLock()
        self.max_cache = max_cache
        self.max_web_jobs = max_web_jobs
        self.max_check_jobs = max_check_jobs
        self.web_jobs = 0
        self.pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix="nova-verify")
        self.web_pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix="nova-web")
        self.storage_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="nova-index-store")
        self.storage_pending = False
        self.storage_buffer = OrderedDict()
        self.storage_ready = False
        self.warming = False

    def warm_index(self):
        with self.lock:
            if self.warming:
                return
            self.warming = True
        self.storage_pool.submit(self._restore_index)

    def _restore_index(self):
        try:
            for doc in reversed(index_storage.load_documents()):
                self.index.add(doc["url"], doc["title"], doc["description"], seen_at=float(doc["seen_at"]))
            self.storage_ready = True
        except Exception:
            pass  # The curated index remains available when the DB is offline.

    def search(self, query, limit=10, mode="web", freshness="", engine="auto", autocorrect=True):
        started = time.perf_counter()
        query = query.strip()
        key = (mode, freshness, engine, bool(autocorrect), query.casefold())
        with self.lock:
            entry = self.cache.get(key)
            if entry and time.monotonic() - entry["at"] < 90:
                self.cache.move_to_end(key)
                self._start_checks(entry, limit)
                batch = self._snapshot(entry, limit)
                batch.elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                return batch
            local = self.index.search(query, 60, mode, freshness) if engine != "web" else []
            corrected = None
            if not local and autocorrect and mode != "exact" and not freshness and engine != "web":
                corrected = self.index.correction(query)
                if corrected:
                    local = self.index.search(corrected, 60, mode, freshness)
            entry = {"at": time.monotonic(), "query": query, "searched_query": corrected or query,
                     "corrected_query": corrected, "mode": mode, "freshness": freshness,
                     "engine": engine, "results": self._prepare(corrected or query, local),
                     "errors": [], "search_pending": False, "web_done": engine == "index"}
            self.cache[key] = entry
            self.cache.move_to_end(key)
            while len(self.cache) > self.max_cache:
                self.cache.popitem(last=False)
            if engine != "index":
                if self.web_jobs < self.max_web_jobs:
                    entry["search_pending"] = True
                    self.web_jobs += 1
                    self.web_pool.submit(self._expand, key, entry, autocorrect)
                else:
                    entry["errors"] = ["web: busy"]
            self._start_checks(entry, limit)
            batch = self._snapshot(entry, limit)
        batch.elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return batch

    def _prepare(self, query, candidates):
        unique = {}
        for item in candidates:
            url = canonical(item.url)
            if url:
                unique.setdefault(url, item.model_copy(deep=True))
        items = list(unique.values())
        index_scores = {item.url: item.score for item in items if item.provider == "nova-index"}
        items = rank(query, items)
        for item in items:
            if item.url in index_scores:
                item.score += index_scores[item.url]
                item.rank_signals = list(dict.fromkeys(item.rank_signals + ["index_match"]))
            item.verification = self.verifier.preview(item.url)
        return promote_verified_official(query, items)[:60]

    def _snapshot(self, entry, limit):
        items = entry["results"]
        if entry["mode"] == "verified":
            items = [item for item in items if item.verification.get("officiality", {}).get("status") in OFFICIAL]
        results = [item.model_copy(deep=True) for item in diversify(items, limit)]
        pending = any(document_url(item.url) in self.jobs for item in entry["results"])
        providers = {item.provider for item in results}
        source = "hybrid" if len(providers) > 1 else ("web" if (providers and "nova-index" not in providers) or (not providers and (entry["engine"] == "web" or entry["web_done"] and entry["engine"] != "index")) else "index")
        for item in results:
            if item.verification.get("status") == "UNKNOWN":
                item.verification["pending"] = document_url(item.url) in self.jobs
        return SearchBatch(results, list(entry["errors"]), entry["searched_query"], entry["corrected_query"],
                           entry["search_pending"], pending, source)

    def _expand(self, key, entry, autocorrect):
        raw, errors = [], []
        searched = entry["searched_query"]
        corrected = entry["corrected_query"]
        try:
            provider_query = f'"{searched}"' if entry["mode"] == "exact" else (discussion_query(searched) if entry["mode"] == "discussions" else searched)
            raw = self.provider(provider_query, 120, freshness=entry["freshness"])
            # Remote spelling suggestions only follow an actually empty result.
            if not raw and not entry["results"] and autocorrect and entry["mode"] != "exact":
                correction = suggest_correction(searched)
                if correction:
                    retry = discussion_query(correction) if entry["mode"] == "discussions" else correction
                    raw = self.provider(retry, 120, freshness=entry["freshness"])
                    if raw:
                        corrected = searched = correction
            if entry["mode"] == "discussions":
                from .query_features import is_discussion_url
                raw = [item for item in raw if is_discussion_url(item.url)]
            local = self.index.search(searched, 60, entry["mode"], entry["freshness"]) if entry["engine"] != "web" else []
            candidates = self._prepare(searched, local + raw)
            with self.lock:
                if self.cache.get(key) is entry:
                    entry.update(results=candidates, searched_query=searched, corrected_query=corrected)
                    self._start_checks(entry, 30)
            learned = self.index.ingest(raw)
            self._save_later(learned)
        except Exception as exc:
            errors = ["web: " + type(exc).__name__]
        finally:
            with self.lock:
                self.web_jobs -= 1
                if self.cache.get(key) is entry:
                    entry.update(search_pending=False, web_done=True, errors=errors)

    def _save_later(self, documents):
        with self.lock:
            if not documents or not self.storage_ready:
                return
            for doc in documents:
                self.storage_buffer[doc["url"]] = doc
                self.storage_buffer.move_to_end(doc["url"])
            while len(self.storage_buffer) > 500:
                self.storage_buffer.popitem(last=False)
            if self.storage_pending:
                return
            self.storage_pending = True
        self.storage_pool.submit(self._save)

    def _save(self):
        while True:
            with self.lock:
                if not self.storage_buffer:
                    self.storage_pending = False
                    return
                documents = [self.storage_buffer.popitem(last=False)[1] for _ in range(min(100, len(self.storage_buffer)))]
            try:
                index_storage.save_documents(documents)
            except Exception:
                pass

    def _start_checks(self, entry, limit):
        # Verified mode checks hidden candidates as well, so they can enter the results.
        candidates = entry["results"][:12 if entry["mode"] == "verified" else min(30, limit)]
        for item in candidates:
            checked = self.verifier.peek(item.url)
            if checked:
                item.verification = checked
                continue
            if item.verification.get("status") not in {None, "UNKNOWN"}:
                continue
            key = document_url(item.url)
            if key not in self.jobs and len(self.jobs) < self.max_check_jobs:
                self.jobs.add(key)
                self.pool.submit(self._verify, key, item.url)

    def _verify(self, key, url):
        try:
            try:
                data = self.verifier.verify(url)
            except Exception as exc:
                data = {"status": "WARNING", "checked_at": None, "url": url, "pending": False,
                        "reasons": ["Проверка не завершена: " + type(exc).__name__],
                        "officiality": self.verifier.preview(url).get("officiality", {}), "technical": {}}
            with self.lock:
                for cached in self.cache.values():
                    for item in cached["results"]:
                        if document_url(item.url) == key:
                            item.verification = deepcopy(data)
            try:
                self.ledger.append({"verification_id": hashlib.sha256(f"{url}|{data.get('checked_at', '')}".encode()).hexdigest()[:20],
                                    "domain": data.get("technical", {}).get("final_host", ""),
                                    "timestamp": data.get("checked_at"), "result": data.get("status"),
                                    "officiality": data.get("officiality", {}).get("status"),
                                    "verification_version": data.get("verification_version")})
            except Exception:
                pass
        finally:
            with self.lock:
                self.jobs.discard(key)

    def close(self):
        self.web_pool.shutdown(wait=True)
        self.pool.shutdown(wait=True)
        self.storage_pool.shutdown(wait=True)
