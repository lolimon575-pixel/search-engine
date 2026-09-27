import re
from .models import WebResult

def rank(query: str, results: list[WebResult]) -> list[WebResult]:
    terms = [x for x in re.findall(r"[\w]+", query.lower()) if len(x) > 1]
    for r in results:
        hay = f"{r.title} {r.description} {r.url}".lower()
        title = f"{r.title} {r.url}".lower()
        r.matched_terms = [t for t in terms if t in hay]
        r.score = round(len(r.matched_terms) * 1.5 + sum(t in title for t in terms) * 2 + 1 / max(r.provider_rank, 1), 5)
    return sorted(results, key=lambda x: x.score, reverse=True)
