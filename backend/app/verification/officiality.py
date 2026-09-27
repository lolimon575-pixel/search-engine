from urllib.parse import urlsplit

REGISTRY={
 "google.com":{"organization":"Google","category":"Technology"},
 "github.com":{"organization":"GitHub","category":"Technology"},
 "microsoft.com":{"organization":"Microsoft","category":"Technology"},
 "apple.com":{"organization":"Apple","category":"Technology"},
}

def base_domain(host):
    host=(host or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host

def verify_officiality(url, site_signals=None):
    host=base_domain(urlsplit(url).hostname or "")
    if host in REGISTRY:
        return {"status":"CONFIRMED","organization":REGISTRY[host]["organization"],"domain":host,"method":"curated-domain-registry","evidence":["Домен присутствует в реестре официальных доменов NOVA."]}
    s=site_signals or {}
    if s.get("organization") or s.get("same_as"):
        return {"status":"SIGNALS","organization":s.get("organization",""),"domain":host,"method":"site-self-signals","evidence":["Обнаружены структурированные признаки организации; это не независимое подтверждение."]}
    return {"status":"UNKNOWN","organization":"","domain":host,"method":"no-independent-confirmation","evidence":[]}

def get_organization_profile(domain):
    host=base_domain(domain); item=REGISTRY.get(host)
    if not item: return None
    return {"organization":item["organization"],"domain":host,"category":item["category"],"method":"curated-domain-registry"}
