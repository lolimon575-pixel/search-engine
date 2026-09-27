import httpx
from urllib.parse import urlsplit


def verify_wikidata(domain, timeout=2.5):
    host = (domain or "").lower().strip().rstrip(".")
    if not host:
        return None

    # P856 = official website. Match the registered host, allowing
    # http/https and a trailing slash.
    query = f"""
SELECT ?item ?itemLabel ?website WHERE {{
  ?item wdt:P856 ?website .
  FILTER(
    LCASE(REPLACE(REPLACE(STR(?website), "^https?://", ""), "/.*$", ""))
    = "{host}"
  )
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,ru". }}
}}
LIMIT 5
"""
    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "NOVA-Search/1.4 (verification)"}
        ) as client:
            response = client.get(
                "https://query.wikidata.org/sparql",
                params={"query": query, "format": "json"},
            )
            response.raise_for_status()
            rows = response.json().get("results", {}).get("bindings", [])
    except Exception:
        return None

    if not rows:
        return None

    first = rows[0]
    return {
        "source": "Wikidata",
        "property": "P856",
        "item": first.get("item", {}).get("value", ""),
        "organization": first.get("itemLabel", {}).get("value", ""),
        "website": first.get("website", {}).get("value", ""),
        "evidence": f"Wikidata содержит этот домен как official website (P856).",
    }
