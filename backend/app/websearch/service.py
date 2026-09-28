from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlsplit, urlunsplit
import threading, time, hashlib
from .ddg import search as ddg_search
from .ranker import rank, diversify, promote_verified_official
from .query_features import discussion_query, is_discussion_url
from app.verification.engine import VerificationEngine
from app.verification.ledger import VerificationLedger


def canonical(url):
    p = urlsplit(url)
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return urlunsplit((p.scheme.lower(), host, p.path.rstrip("/") or "/", "", ""))


class WebSearchService:
    def __init__(self):
        self.verifier = VerificationEngine()
        self.ledger = VerificationLedger()
        self.cache = {}
        self.jobs = set()
        self.lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix="nova-verify")

    def search(self, query, limit=10, mode="web"):
        mode = (mode or "web").strip().lower()
        key = f"{mode}:{query.strip().lower()}"

        with self.lock:
            cached = self.cache.get(key)
            if cached and time.time() - cached["at"] < 45:
                return cached["results"][:limit], []

        try:
            provider_query = discussion_query(query) if mode == "discussions" else query
            raw = ddg_search(provider_query, max(36, limit * 5))
        except Exception as e:
            return [], [f"duckduckgo: {type(e).__name__}"]

        unique = {}
        for item in raw:
            unique.setdefault(canonical(item.url), item)

        candidates = rank(query, list(unique.values()))
        candidate_limit = min(len(candidates), max(20, limit * 2))
        candidates = candidates[:candidate_limit]

        # Verify enough top candidates to let NOVA safely recognize and promote
        # a confirmed official site before the final diverse result set is chosen.
        first_batch = candidates[:min(6, len(candidates))]
        if first_batch:
            with ThreadPoolExecutor(max_workers=6, thread_name_prefix="nova-initial") as pool:
                futures = {pool.submit(self.verifier.verify, item.url): item for item in first_batch}
                for future in as_completed(futures):
                    item = futures[future]
                    try:
                        item.verification = future.result()
                        self._record_verification(item.url, item.verification)
                    except Exception as e:
                        item.verification = {
                            "status": "WARNING",
                            "checked_at": None,
                            "url": item.url,
                            "reasons": [f"Проверка не завершена: {type(e).__name__}"],
                            "officiality": {"status": "UNKNOWN", "organization": "", "evidence": []},
                            "technical": {},
                            "verification_version": "1.4.0",
                        }

        candidates = promote_verified_official(query, candidates)

        if mode == "discussions":
            candidates = [item for item in candidates if is_discussion_url(item.url)]
        elif mode == "official":
            trusted = {"OWNER_VERIFIED", "EXTERNAL_CONFIRMED", "CURATED"}
            official_candidates = [
                item for item in candidates
                if ((item.verification or {}).get("officiality") or {}).get("status") in trusted
            ]
            if official_candidates:
                candidates = official_candidates

        cache_limit = min(20, len(candidates))
        results = diversify(candidates, cache_limit)

        pending_urls = []
        for item in results:
            if not item.verification:
                cached_verification = self.verifier.peek(item.url)
                if cached_verification:
                    item.verification = cached_verification
                else:
                    item.verification = {
                        "status": "UNKNOWN",
                        "message": "Проверка ещё не выполнялась."
                    }
                    pending_urls.append(item.url)

        with self.lock:
            self.cache[key] = {"at": time.time(), "results": results}

        for url in pending_urls:
            self._schedule(query, url)

        return results[:limit], []

    def _record_verification(self, url, data):
        try:
            self.ledger.append({
                "verification_id": hashlib.sha256(
                    f"{url}|{data.get('checked_at', '')}".encode()
                ).hexdigest()[:20],
                "domain": data.get("technical", {}).get("final_host", ""),
                "timestamp": data.get("checked_at"),
                "result": data.get("status"),
                "officiality": data.get("officiality", {}).get("status"),
                "verification_version": data.get("verification_version"),
            })
        except Exception:
            pass

    def _schedule(self, query, url):
        key = canonical(url)
        with self.lock:
            if key in self.jobs:
                return
            self.jobs.add(key)
        self.pool.submit(self._verify, key, url)

    def _verify(self, key, url):
        try:
            data = self.verifier.verify(url, query="")
            with self.lock:
                for cached in self.cache.values():
                    for item in cached["results"]:
                        if canonical(item.url) == key:
                            item.verification = data
            try:
                self.ledger.append({
                    "verification_id": hashlib.sha256(f"{url}|{data.get('checked_at','')}".encode()).hexdigest()[:20],
                    "domain": data.get("technical", {}).get("final_host", ""),
                    "timestamp": data.get("checked_at"),
                    "result": data.get("status"),
                    "officiality": data.get("officiality", {}).get("status"),
                    "verification_version": data.get("verification_version"),
                })
            except Exception:
                pass
        finally:
            with self.lock:
                self.jobs.discard(key)
