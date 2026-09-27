from urllib.parse import urlsplit

REGISTRY = {
    "google.com": {"organization": "Google", "category": "Technology"},
    "github.com": {"organization": "GitHub", "category": "Technology"},
    "microsoft.com": {"organization": "Microsoft", "category": "Technology"},
    "apple.com": {"organization": "Apple", "category": "Technology"},
    "openai.com": {"organization": "OpenAI", "category": "AI"},
    "riotgames.com": {"organization": "Riot Games", "category": "Games"},
    "steampowered.com": {"organization": "Valve / Steam", "category": "Games"},
    "discord.com": {"organization": "Discord", "category": "Technology"},
    "amazon.com": {"organization": "Amazon", "category": "Commerce"},
    "amazon.de": {"organization": "Amazon", "category": "Commerce"},
    "tesla.com": {"organization": "Tesla", "category": "Automotive"},
    "nvidia.com": {"organization": "NVIDIA", "category": "Technology"},
    "adobe.com": {"organization": "Adobe", "category": "Technology"},
    "spotify.com": {"organization": "Spotify", "category": "Media"},
    "netflix.com": {"organization": "Netflix", "category": "Media"},
    "x.com": {"organization": "X", "category": "Social"},
    "yandex.ru": {"organization": "Yandex", "category": "Technology"},
    "vk.com": {"organization": "VK", "category": "Social"},
}


def base_domain(host):
    host = (host or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def verify_officiality(url, site_signals=None, external=None):
    host = base_domain(urlsplit(url).hostname or "")
    item = REGISTRY.get(host)

    if item:
        return {
            "status": "CONFIRMED",
            "organization": item["organization"],
            "domain": host,
            "method": "curated-domain-registry",
            "evidence": [
                f"Домен {host} находится в реестре доменов, сопоставленных NOVA с организацией {item['organization']}."
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
            "evidence": evidence + [
                "Эти признаки не являются независимым подтверждением владения доменом."
            ],
        }

    return {
        "status": "UNKNOWN",
        "organization": "",
        "domain": host,
        "method": "no-independent-confirmation",
        "evidence": [
            "Независимого подтверждения соответствия организации этому домену пока нет."
        ],
    }


def get_organization_profile(domain):
    host = base_domain(domain)
    item = REGISTRY.get(host)
    if not item:
        return None
    return {
        "organization": item["organization"],
        "domain": host,
        "category": item["category"],
        "method": "curated-domain-registry",
    }
