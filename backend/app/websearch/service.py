from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit,urlunsplit
import threading,time
from .ddg import search as ddg_search
from .ranker import rank
from app.verification.engine import VerificationEngine

def canonical(url):
    p=urlsplit(url); host=(p.hostname or "").lower(); host=host[4:] if host.startswith("www.") else host
    return urlunsplit((p.scheme.lower(),host,p.path.rstrip("/") or "/","",""))

class WebSearchService:
    def __init__(self,timeout=8,search_ttl=45): self.timeout=timeout; self.search_ttl=search_ttl; self.verifier=VerificationEngine(); self.cache={}; self.jobs=set(); self.lock=threading.Lock(); self.pool=ThreadPoolExecutor(max_workers=4,thread_name_prefix="nova-verify")
    def _schedule(self,query,results):
        for result in results:
            key=(query.lower(),canonical(result.url))
            if result.verification.get("status") not in (None,"","UNKNOWN"): continue
            with self.lock:
                if key in self.jobs: continue
                self.jobs.add(key)
            self.pool.submit(self._verify_one,key,query,result.url)
    def _verify_one(self,key,query,url):
        try:
            data=self.verifier.verify(url,query=query)
            with self.lock:
                cached=self.cache.get(query.lower())
                if cached:
                    for item in cached["results"]:
                        if canonical(item.url)==canonical(url): item.verification=data
        finally:
            with self.lock:self.jobs.discard(key)
    def search(self,query,limit=10):
        key=query.strip().lower()
        with self.lock:
            cached=self.cache.get(key)
            if cached and time.time()-cached["at"]<=self.search_ttl:
                results=cached["results"][:limit]; self._schedule(query,results); return results,[]
        errors=[]
        try:raw=ddg_search(query,max(20,limit*3),self.timeout)
        except Exception as exc:raw=[]; errors=[f"duckduckgo: {type(exc).__name__}"]
        unique={}
        for item in raw:unique.setdefault(canonical(item.url),item)
        results=rank(query,list(unique.values()))[:limit]
        for item in results:item.verification=self.verifier.peek(item.url) or {"status":"UNKNOWN","message":"Проверка выполняется или ещё не проводилась."}
        with self.lock:self.cache[key]={"at":time.time(),"results":results}
        self._schedule(query,results); return results,errors
