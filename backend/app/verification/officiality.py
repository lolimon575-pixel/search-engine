from urllib.parse import urlsplit

from app.registry_db import get_site, normalize_domain
from app.verification.registry_data import REGISTRY
from app.profile_settings import apply_profile_settings


def base_domain(host):
    return normalize_domain(host)


def verify_officiality(url, site_signals=None, external=None, *, use_database=True):
    host = base_domain(urlsplit(url).hostname or "")
    try:
        db_item = get_site(host) if use_database else None
    except Exception:
        db_item = None

    if db_item:
        owner_verified = db_item.get("owner_verification") == "DOMAIN_CONTROL"
        if owner_verified:
            return {
                "status": "OWNER_VERIFIED",
                "organization": db_item["organization"],
                "domain": host,
                "method": "domain-control+database-registry",
                "evidence": [
                    f"Домен {host} находится в реестре NOVA и сопоставлен с организацией {db_item['organization']}.",
                    f"Контроль домена подтверждён через файл {host}/.well-known/nova-verification.txt.",
                    "Платный профиль, если он подключён, не влияет на органическую позицию результата.",
                ],
                "registry_id": db_item["id"],
                "ownership_verified_at": db_item.get("ownership_verified_at"),
            }

        return {
            "status": "CONFIRMED",
            "organization": db_item["organization"],
            "domain": host,
            "method": "database-registry",
            "evidence": [
                f"Домен {host} находится в реестре NOVA и сопоставлен с организацией {db_item['organization']}.",
                "Запись хранится в курируемом реестре официальных сайтов NOVA.",
                "Контроль домена владельцем через NOVA пока не подтверждён.",
            ],
            "registry_id": db_item["id"],
        }

    item = REGISTRY.get(host)
    if item:
        return {
            "status": "CONFIRMED",
            "organization": item["organization"],
            "domain": host,
            "method": "curated-domain-registry",
            "evidence": [
                f"Домен {host} находится в курируемом реестре NOVA и сопоставлен с организацией {item['organization']}.",
                "Эта запись не является подтверждением юридической личности владельца.",
            ],
        }

    if external:
        return {
            "status": "EXTERNAL_CONFIRMED",
            "organization": external.get("organization", ""),
            "domain": host,
            "method": "wikidata-p856",
            "evidence": [external.get("evidence", "Домен указан как official website во внешнем источнике.")],
            "source": external.get("source", "Wikidata"),
            "source_url": external.get("item", ""),
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
            "evidence": evidence + ["Эти признаки не являются независимым подтверждением владения доменом."],
        }

    return {
        "status": "UNKNOWN",
        "organization": "",
        "domain": host,
        "method": "no-independent-confirmation",
        "evidence": ["Независимого подтверждения соответствия организации этому домену пока нет."],
    }


def get_organization_profile(domain):
    host = base_domain(domain)
    try:
        row = get_site(host)
    except Exception:
        row = None

    if row:
        owner_verified = row.get("owner_verification") == "DOMAIN_CONTROL"
        return apply_profile_settings({
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
            "method": row["source"],
            "confirmation_level": row["confirmation_level"],
            "source_url": row["source_url"],
            "last_check": row["last_check"],
            "profile_tier": row.get("profile_tier") or "standard",
            "profile_badge": row.get("profile_badge"),
            "profile_accent": row.get("profile_accent"),
            "billing_status": row.get("billing_status") or "inactive",
            "billing_period_end": row.get("billing_period_end"),
            "owner_verification": row.get("owner_verification") or "unverified",
            "ownership_verified_at": row.get("ownership_verified_at"),
            "trust_level": "domain_control_verified" if owner_verified else "curated_registry",
            "premium_eligible": owner_verified,
            "ranking_policy": "Профиль компании и его тариф не влияют на органический NOVA Rank.",
        }, row.get("profile_settings"))

    item = REGISTRY.get(host)
    if not item:
        return None
    return {
        "organization": item["organization"],
        "domain": host,
        "url": "https://" + host,
        "category": item.get("category"),
        "tagline": item.get("tagline"),
        "description": item.get("description"),
        "links": item.get("links") or {},
        "profile_tier": item.get("profile_tier", "standard"),
        "profile_badge": item.get("profile_badge"),
        "profile_accent": item.get("profile_accent"),
        "method": "curated-domain-registry",
        "owner_verification": "unverified",
        "trust_level": "curated_registry",
        "premium_eligible": False,
        "ranking_policy": "Профиль компании и его тариф не влияют на органический NOVA Rank.",
    }


def is_registry_domain(host):
    normalized = base_domain(host)
    if normalized in REGISTRY:
        return True
    try:
        return bool(get_site(normalized))
    except Exception:
        return False
