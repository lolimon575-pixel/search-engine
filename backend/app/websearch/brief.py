import re
from urllib.parse import urlsplit


QUESTION_WORDS = {
    "как", "что", "почему", "зачем", "когда", "где", "кто", "какой", "какая", "какие",
    "how", "what", "why", "when", "where", "who", "which",
}


def _terms(value):
    return {x for x in re.findall(r"[\w]+", (value or "").casefold()) if len(x) > 2}


def should_build_brief(query):
    terms = _terms(query)
    if len(terms) >= 3:
        return True
    return bool(terms & QUESTION_WORDS)


def build_brief(query, results, limit=3):
    if not should_build_brief(query):
        return None

    q_terms = _terms(query)
    passages = []
    seen_domains = set()

    for item in results:
        text = " ".join((item.description or "").split())
        if len(text) < 45:
            continue
        host = (urlsplit(item.url).hostname or "").lower().removeprefix("www.")
        if not host or host in seen_domains:
            continue

        overlap = len(q_terms & _terms(f"{item.title} {text}"))
        if q_terms and overlap == 0:
            continue

        seen_domains.add(host)
        passages.append({
            "title": item.title,
            "url": item.url,
            "domain": host,
            "text": text[:280] + ("…" if len(text) > 280 else ""),
        })
        if len(passages) >= limit:
            break

    if len(passages) < 2:
        return None

    return {
        "kind": "extractive",
        "title": "NOVA Brief",
        "note": "Краткий обзор составлен из сниппетов найденных страниц без генерации новых фактов.",
        "passages": passages,
    }
