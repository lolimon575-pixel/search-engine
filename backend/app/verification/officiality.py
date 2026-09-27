from urllib.parse import urlsplit

REGISTRY={
 "google.com":{"organization":"Google","category":"Technology","links":[("Поиск","https://www.google.com/"),("Помощь","https://support.google.com/")]},
 "github.com":{"organization":"GitHub","category":"Technology","links":[("Главная","https://github.com/"),("Помощь","https://docs.github.com/")]},
 "microsoft.com":{"organization":"Microsoft","category":"Technology","links":[("Главная","https://www.microsoft.com/"),("Поддержка","https://support.microsoft.com/")]},
 "apple.com":{"organization":"Apple","category":"Technology","links":[("Главная","https://www.apple.com/"),("Поддержка","https://support.apple.com/")]},
}

def base_domain(host:str)->str:
    host=(host or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host

def verify_officiality(url:str, site_signals:dict|None=None)->dict:
    host=base_domain(urlsplit(url).hostname or "")
    if host in REGISTRY:
        item=REGISTRY[host]
        return {"status":"CONFIRMED","organization":item["organization"],"domain":host,"method":"curated-domain-registry","evidence":["Домен присутствует в реестре официальных доменов NOVA."]}
    signals=site_signals or {}
    if signals.get("organization") or signals.get("same_as"):
        return {"status":"SIGNALS","organization":signals.get("organization",""),"domain":host,"method":"site-self-signals","evidence":["Обнаружены структурированные признаки организации; это не независимое подтверждение."]}
    return {"status":"UNKNOWN","organization":"","domain":host,"method":"no-independent-confirmation","evidence":[]}

def get_organization_profile(domain:str):
    host=base_domain(domain); item=REGISTRY.get(host)
    if not item: return None
    return {"organization":item["organization"],"domain":host,"category":item["category"],"method":"curated-domain-registry","description":f"Профиль организации для {item['organization']}.","links":[{"label":a,"url":b} for a,b in item["links"]]}
