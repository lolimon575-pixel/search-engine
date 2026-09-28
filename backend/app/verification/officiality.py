from urllib.parse import urlsplit

from app.registry_catalog import REGISTRY
from app.registry_db import get_latest_verified_claim, get_site, normalize_domain


def base_domain(host):
    return normalize_domain(host)


def verify_officiality(url, site_signals=None, external=None):
    host = base_domain(urlsplit(url).hostname or "")

    try:
        owner_claim = get_latest_verified_claim(host)
    except Exception:
        owner_claim = None

    try:
        db_item = get_site(host)
    except Exception:
        db_item = None

    if owner_claim:
        organization = (db_item or {}).get("organization") or owner_claim.get("organization_name") or host
        return {
            "status": "OWNER_VERIFIED",
            "organization": organization,
            "domain": host,
            "method": "domain-control-challenge",
            "confidence": "highest",
            "evidence": [
                f"Владелец подтвердил контроль домена {host} через challenge-файл на самом сайте.",
                "Платный профиль, если подключён, не влияет на позицию сайта в поисковой выдаче.",
            ],
            "registry_id": (db_item or {}).get("id"),
        }

    if external:
        return {
            "status": "EXTERNAL_CONFIRMED",
            "organization": external.get("organization", ""),
            "domain": host,
            "method": "wikidata-p856",
            "confidence": "high",
            "evidence": [external.get("evidence", "Домен указан как official website во внешнем источнике.")],
            "source": external.get("source", "Wikidata"),
            "source_url": external.get("item", ""),
        }

    if db_item:
        return {
            "status": "CURATED",
            "organization": db_item["organization"],
            "domain": host,
            "method": "nova-curated-registry",
            "confidence": "medium",
            "evidence": [
                f"Домен {host} сопоставлен NOVA с организацией {db_item['organization']}.",
                "Это редакционная запись реестра, а не доказательство контроля домена владельцем.",
            ],
            "registry_id": db_item["id"],
        }

    item = REGISTRY.get(host)
    if item:
        return {
            "status": "CURATED",
            "organization": item["organization"],
            "domain": host,
            "method": "nova-curated-registry",
            "confidence": "medium",
            "evidence": [
                f"Домен {host} находится в редакционном реестре NOVA и сопоставлен с организацией {item['organization']}.",
                "Для статуса Owner Verified владелец должен подтвердить контроль домена.",
            ],
        }

    signals = site_signals or {}
    evidence = []
    if signals.get("organization"):
        evidence.append("На самом сайте обнаружено название организации в структурированных данных.")
    if signals.get("same_as"):
        evidence.append("На сайте обнаружены внешние ссылки sameAs.")

    if evidence:
        return {
            "status": "SIGNALS",
            "organization": signals.get("organization", ""),
            "domain": host,
            "method": "site-self-signals",
            "confidence": "low",
            "evidence": evidence + ["Эти признаки исходят от самого сайта и не являются независимым подтверждением владения доменом."],
        }

    return {
        "status": "UNKNOWN",
        "organization": "",
        "domain": host,
        "method": "no-independent-confirmation",
        "confidence": "unknown",
        "evidence": ["Независимого подтверждения соответствия организации этому домену пока нет."],
    }


def get_organization_profile(domain):
    host = base_domain(domain)
    try:
        row = get_site(host)
    except Exception:
        row = None

    if row:
        return {
            "id": row["organization_id"],
            "site_id": row["id"],
            "organization": row["organization"],
            "domain": host,
            "url": row["url"],
            "category": row["category"],
            "tagline": row.get("tagline"),
            "description": row["description"],
            "logo_url": row["logo_url"],
            "links": row["links"] or {},
            "profile": row.get("profile") or {},
            "profile_tier": row.get("profile_tier") or "standard",
            "ownership_status": row.get("ownership_status") or "unclaimed",
            "method": row["source"],
            "confirmation_level": row["confirmation_level"],
            "source_url": row["source_url"],
            "last_check": row["last_check"],
        }

    item = REGISTRY.get(host)
    if not item:
        return None
    return {
        "organization": item["organization"],
        "domain": host,
        "category": item["category"],
        "tagline": item.get("tagline"),
        "description": item.get("description"),
        "links": item.get("links") or {},
        "profile_tier": "standard",
        "ownership_status": "unclaimed",
        "method": "nova-curated-registry",
        "confirmation_level": "CURATED",
    }


def is_registry_domain(host):
    normalized = base_domain(host)
    if normalized in REGISTRY:
        return True
    try:
        return bool(get_site(normalized))
    except Exception:
        return False


def find_entity_profile(query):
    raw = (query or "").strip().casefold()
    if not raw:
        return None
    normalized = normalize_domain(raw)
    compact = "".join(ch for ch in raw if ch.isalnum())

    matches = []
    seen_orgs = set()
    for domain, item in REGISTRY.items():
        org = item["organization"]
        org_key = "".join(ch for ch in org.casefold() if ch.isalnum())
        domain_key = domain.casefold().removeprefix("www.")
        root_key = domain_key.split(".")[0]
        if raw in {domain_key, "www." + domain_key} or compact in {org_key, root_key}:
            if org_key in seen_orgs:
                continue
            seen_orgs.add(org_key)
            matches.append(domain)

    if normalized in REGISTRY and normalized not in matches:
        matches.insert(0, normalized)

    if not matches:
        return None

    domain = matches[0]
    profile = get_organization_profile(domain)
    if not profile:
        return None

    try:
        claim = get_latest_verified_claim(domain)
    except Exception:
        claim = None

    profile["identity_status"] = "OWNER_VERIFIED" if claim else profile.get("confirmation_level", "CURATED")
    profile["trust_explanation"] = (
        "Владелец домена подтвердил контроль через challenge на сайте."
        if claim else
        "Организация и домен сопоставлены в редакционном реестре NOVA. Владелец ещё не проходил domain-control challenge."
    )
    return profile
