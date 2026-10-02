"""Run: PYTHONPATH=backend python backend/scripts/benchmark_search.py

Measures local CPU retrieval and registry previews. Excludes network I/O,
hosting cold starts and browser rendering; not a production latency promise.
"""
from statistics import median
from time import perf_counter
from app.websearch.service import WebSearchService

service = WebSearchService(max_check_jobs=0)
queries = ["авто ру", "puma", "puma вакансии", "github docs", "гитхаб", "несуществующий запрос"]
try:
    print(service.index.stats())
    print("Fresh local search: 200 runs per query, no network I/O")
    for query in queries:
        timings = []
        for _ in range(200):
            service.cache.clear()
            started = perf_counter()
            batch = service.search(query, engine="index", autocorrect=False)
            timings.append((perf_counter()-started)*1000)
        timings.sort()
        print(f"{query:24} count={len(batch.results):2} p50={median(timings):.3f}ms p95={timings[189]:.3f}ms")
finally:
    service.close()
