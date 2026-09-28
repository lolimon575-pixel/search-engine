"""NOVA Search Core v1 - trusted registry ranking layer."""

from typing import Any

from app.verification.registry_data import REGISTRY


def normalize_query(value: str) -> str:
    return " ".join((value or "").lower().strip().split())


def search_registry(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search NOVA knowledge layer before external search."""
    q = normalize_query(query)
    if not q:
        return []

    results = []
    for domain, profile in REGISTRY.items():
        text = " ".join([
            domain,
            profile.get("organization", ""),
            profile.get("category", ""),
            profile.get("tagline", ""),
            profile.get("description", ""),
        ]).lower()

        score = 0
        reasons = []

        if q == domain or q == domain.replace(".com", ""):
            score += 100
            reasons.append("exact_domain")
        if q in profile.get("organization", "").lower():
            score += 90
            reasons.append("organization_match")
        if q in text:
            score += 40
            reasons.append("profile_match")

        if score:
            results.append({
                "domain": domain,
                "organization": profile.get("organization"),
                "category": profile.get("category"),
                "nova_score": score,
                "reasons": reasons,
                "profile": profile,
            })

    results.sort(key=lambda item: item["nova_score"], reverse=True)
    return results[:limit]
