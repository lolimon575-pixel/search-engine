import math
import re
from urllib.parse import urlsplit

from .models import WebResult


def _text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").casefold()).strip()


def _terms(value: str) -> list[str]:
    return [x for x in re.findall(r"[\w]+", _text(value), flags=re.UNICODE) if len(x) > 1]


def _host_parts(url: str) -> tuple[str, str, str]:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").casefold().removeprefix("www.")
    root = host.split(".")[0] if host else ""
    path = (parsed.path or "/").casefold()
    return host, root, path


def rank(query: str, results: list[WebResult]) -> list[WebResult]:
    phrase = _text(query)
    terms = _terms(query)
    compact_query = re.sub(r"[^\w]+", "", phrase, flags=re.UNICODE)

    for result in results:
        title = _text(result.title)
        description = _text(result.description)
        host, root, path = _host_parts(result.url)
        url_text = f"{host}{path}"
        haystack = f"{title} {description} {url_text}"

        matched = [term for term in terms if term in haystack]
        title_hits = sum(term in title for term in terms)
        host_hits = sum(term in host for term in terms)
        path_hits = sum(term in path for term in terms)
        description_hits = sum(term in description for term in terms)
        coverage = len(matched) / max(len(terms), 1)

        score = 0.0
        signals: list[str] = []

        provider_rank = max(result.provider_rank, 1)
        score += 3.2 / math.pow(provider_rank, 0.55)

        if phrase and phrase in title:
            score += 7.0
            signals.append("exact_title")
        elif phrase and phrase in description:
            score += 2.0
            signals.append("exact_description")

        if phrase and phrase in url_text:
            score += 4.0
            signals.append("exact_url")

        score += title_hits * 2.7
        score += host_hits * 3.1
        score += path_hits * 0.9
        score += description_hits * 0.75
        score += coverage * 4.2

        if coverage >= 0.999 and terms:
            signals.append("full_coverage")
        elif coverage >= 0.6:
            signals.append("strong_coverage")

        compact_root = re.sub(r"[^\w]+", "", root, flags=re.UNICODE)
        if compact_query and compact_query == compact_root:
            score += 8.0
            signals.append("domain_match")

        depth = len([part for part in path.split("/") if part])
        if depth == 0:
            score += 1.4
            signals.append("homepage")
        elif depth >= 5:
            score -= min(2.0, (depth - 4) * 0.35)

        if len(result.url) > 180:
            score -= 0.8

        result.matched_terms = matched
        result.rank_signals = list(dict.fromkeys(signals))
        result.score = round(score, 4)

    return sorted(results, key=lambda item: (item.score, -item.provider_rank), reverse=True)


def promote_verified_official(query: str, results: list[WebResult]) -> list[WebResult]:
    query_text = _text(query)
    query_terms = set(_terms(query))
    compact_query = re.sub(r"[^\w]+", "", query_text, flags=re.UNICODE)

    for result in results:
        officiality = (result.verification or {}).get("officiality") or {}
        status = officiality.get("status")
        if status not in {"OWNER_VERIFIED", "CURATED", "EXTERNAL_CONFIRMED"}:
            continue

        organization = _text(officiality.get("organization", ""))
        organization_terms = set(_terms(organization))
        _, root, _ = _host_parts(result.url)
        compact_org = re.sub(r"[^\w]+", "", organization, flags=re.UNICODE)
        compact_root = re.sub(r"[^\w]+", "", root, flags=re.UNICODE)

        exact_org = bool(compact_query and compact_query == compact_org)
        exact_domain = bool(compact_query and compact_query == compact_root)
        full_org_match = bool(query_terms and query_terms.issubset(organization_terms))

        if exact_org or exact_domain or full_org_match:
            bonus = 20.0 if status == "OWNER_VERIFIED" else (12.0 if status == "EXTERNAL_CONFIRMED" else 8.0)
            result.score = round(result.score + bonus, 4)
            result.rank_signals = ["official_match", *[s for s in result.rank_signals if s != "official_match"]]

    return sorted(results, key=lambda item: (item.score, -item.provider_rank), reverse=True)


def diversify(results: list[WebResult], limit: int, max_per_domain: int = 2) -> list[WebResult]:
    if limit <= 0:
        return []

    selected: list[WebResult] = []
    deferred: list[WebResult] = []
    counts: dict[str, int] = {}

    for result in results:
        host, _, _ = _host_parts(result.url)
        key = host or result.url
        if counts.get(key, 0) < max_per_domain:
            selected.append(result)
            counts[key] = counts.get(key, 0) + 1
        else:
            deferred.append(result)
        if len(selected) >= limit:
            return selected[:limit]

    for result in deferred:
        selected.append(result)
        if len(selected) >= limit:
            break

    return selected[:limit]
