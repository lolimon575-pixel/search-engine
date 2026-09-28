"""NOVA Search Core - trusted registry ranking layer."""

from typing import Any

from app.verification.registry_data import REGISTRY


def normalize_query(value: str) -> str:
    return " ".join((value or "").lower().replace("-", " ").split())


def search_registry(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search NOVA knowledge layer before external search providers."""
    q = normalize_query(query)
    if not q:
        return []

    results = []
    for domain, profile in REGISTRY.items():
        organization = normalize_query(profile.get("organization", ""))
        category = normalize_query(profile.get("category", ""))
        text = " ".join([
            domain,
            organization,
            category,
            normalize_query(profile.get("tagline", "")),
            normalize_query(profile.get("description", "")),
        ])

        score = 0
        reasons = []

        if q == normalize_query(domain) or q == domain.replace(".com", ""):
            score += 120
            reasons.append("exact_domain")
        if q == organization:
            score += 110
            reasons.append("exact_organization")
        elif q in organization:
            score += 80
            reasons.append("organization_match")
        if q in text:
            score += 35
            reasons.append("profile_match")

        if profile.get("profile_tier") in ("premium", "verified"):
            score += 5
            reasons.append("profile_available")

        if score:
            results.append({
                "domain": domain,
                "organization": profile.get("organization"),
                "category": profile.get("category"),
                "nova_score": score,
                "reasons": reasons,
                "profile": profile,
            })

    return sorted(results, key=lambda item: item["nova_score"], reverse=True)[:limit]
