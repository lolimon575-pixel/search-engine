from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlsplit,urlunsplit
import threading,time
from .ddg import search as ddg_search
from .ranker import rank
from app.verification.engine import VerificationEngine

def canonical(url):
    p=urlsplit(url); host=(p.hostname or "").lower()
    if host.startswith("www."): host=host[4:]
    return urlunsplit((p.scheme.lower(),host,p.path.rstrip("/") or "/","",""))

class WebSearchService:
    def __init__(self):
        self.verifier=VerificationEngine()
        self.cache={}
        self.jobs=set()
        self.lock=threading.Lock()
        self.pool=ThreadPoolExecutor(max_workers=6,thread_name_prefix="nova-verify")

    def search(self,query,limit=10):
        key=query.strip().lower()
        with self.lock:
            c=self.cache.get(key)
            if c and time.time()-c["at"]<45:
                return c["results"][:limit],[]

        try:
            raw=ddg_search(query,max(20,limit*3))
        except Exception as e:
            return [],[f"duckduckgo: {type(e).__name__}"]

        unique={}
        for x in raw:
            unique.setdefault(canonical(x.url),x)
        results=rank(query,list(unique.values()))[:limit]

        # IMPORTANT: verify the visible first results before returning them.
        # The previous version returned UNKNOWN and only checked in background,
        # so the browser never saw the completed verification.
        first_batch=results[:min(6,len(results))]
        with ThreadPoolExecutor(max_workers=6,thread_name_prefix="nova-initial") as pool:
            futures={pool.submit(self.verifier.verify,x.url): x for x in first_batch}
            for f in as_completed(futures):
                x=futures[f]
                try:
                    x.verification=f.result()
                except Exception as e:
                    x.verification={
                        "status":"WARNING",
                        "checked_at":None,
                        "url":x.url,
                        "reasons":[f"Проверка не завершена: {type(e).__name__}"],
                        "officiality":{"status":"UNKNOWN","organization":"","evidence":[]},
                        "technical":{}
                    }

        for x in results:
            if not x.verification:
                x.verification=self.verifier.peek(x.url) or {
                    "status":"UNKNOWN",
                    "message":"Проверка ещё не выполнялась."
                }

        with self.lock:
            self.cache[key]={"at":time.time(),"results":results}

        for x in results[len(first_batch):]:
            self._schedule(query,x.url)

        return results,[]

    def _schedule(self,query,url):
        key=canonical(url)
        with self.lock:
            if key in self.jobs:
                return
            self.jobs.add(key)
        self.pool.submit(self._verify,key,url)

    def _verify(self,key,url):
        try:
            data=self.verifier.verify(url,query="")
            with self.lock:
                for c in self.cache.values():
                    for x in c["results"]:
                        if canonical(x.url)==key:
                            x.verification=data
        finally:
            with self.lock:
                self.jobs.discard(key)
