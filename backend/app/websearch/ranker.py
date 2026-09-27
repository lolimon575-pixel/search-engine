import re
from .models import WebResult

def rank(query: str, results: list[WebResult]) -> list[WebResult]:
    terms = [x for x in re.findall(r"[\w]+", query.lower()) if len(x) > 1]
    for r in results:
        hay = (r.title + " " + r.description + " " + r.url).lower()
        title = (r.title + " " + r.url).lower()
        matched = [t for t in terms if t in hay]
        title_hits = sum(t in title for t in terms)
        r.matched_terms = matched
        r.score = round(len(matched) * 1.5 + title_hits * 2 + 1 / max(r.provider_rank, 1), 5)
    return sorted(results, key=lambda x: x.score, reverse=True)
