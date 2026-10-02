"""NOVA's bounded, local full-text index. No search requests or billing data stored."""
from collections import OrderedDict
import ipaddress
import re
import sqlite3
import threading
import time
from urllib.parse import urlsplit, urlunsplit

from app.verification.registry_data import REGISTRY
from .models import WebResult


SECTIONS = {
    "careers": "Карьера вакансии вакансия работа careers jobs", "jobs": "Карьера вакансии вакансия работа careers jobs",
    "shop": "Магазин каталог купить shop store", "store": "Магазин каталог купить shop store",
    "products": "Продукты каталог products", "docs": "Документация docs documentation API",
    "developers": "Разработчикам developers API", "developer": "Разработчикам developer API",
    "support": "Поддержка помощь support help", "help": "Поддержка помощь support help",
    "about": "О компании about", "newsroom": "Новости пресса newsroom news",
    "pricing": "Тарифы цены pricing", "research": "Исследования research",
    "learn": "Обучение learn", "download": "Скачать download", "business": "Для бизнеса business",
}
ALIASES = {
    "puma.com": "пума", "google.com": "гугл", "youtube.com": "ютуб ютюб",
    "github.com": "гитхаб", "openai.com": "опен аи", "apple.com": "эппл",
    "microsoft.com": "майкрософт", "auto.ru": "автору авто ру auto ru",
    "avito.ru": "авито", "yandex.ru": "яндекс", "ozon.ru": "озон",
    "wildberries.ru": "вайлдберриз вб", "sberbank.ru": "сбер сбербанк",
}


def words(value):
    return re.findall(r"[^\W_]+", str(value).casefold().replace("ё", "е"), re.UNICODE)


def normalized(value):
    return " ".join(words(value))


def document_url(url):
    """Retain query strings: different destination queries can be different pages."""
    try:
        p = urlsplit(url)
        host = (p.hostname or "").lower().rstrip(".")
        if p.scheme.lower() not in {"https", "http"} or p.username or p.password or not host:
            return ""
        if host == "localhost" or "." not in host or host.endswith((".local", ".internal")):
            return ""
        try:
            if not ipaddress.ip_address(host).is_global:
                return ""
        except ValueError:
            pass
        port = p.port
        if port and port != (443 if p.scheme.lower() == "https" else 80):
            host += ":" + str(port)
        return urlunsplit((p.scheme.lower(), host, p.path or "/", p.query, ""))
    except (ValueError, TypeError):
        return ""


class LocalIndex:
    def __init__(self, registry=None, max_documents=5000):
        self.max_documents = max_documents
        self.lock = threading.RLock()
        self.db = sqlite3.connect(":memory:", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("CREATE VIRTUAL TABLE documents USING fts5(url UNINDEXED, title, description, aliases, host, tokenize='unicode61 remove_diacritics 2')")
        self.documents = OrderedDict()
        self.brands = {}
        self.seed(REGISTRY if registry is None else registry)

    def seed(self, registry):
        for domain, item in registry.items():
            name = item.get("organization", domain)
            aliases = " ".join((name, domain, ALIASES.get(domain, "")))
            self.brands[normalized(name)] = name
            for alias in ALIASES.get(domain, "").split():
                if len(alias) >= 3:
                    self.brands.setdefault(normalized(alias), name)
            description = " · ".join(filter(None, [item.get("tagline"), item.get("description")]))
            self.add("https://" + domain + "/", name, description, aliases, curated=True)
            for section, url in (item.get("links") or {}).items():
                label = SECTIONS.get(section, section)
                self.add(url, name + " — " + label.split(" ")[0], description + " · " + label,
                         aliases + " " + label, curated=True)

    def add(self, url, title, description="", aliases="", curated=False, seen_at=None):
        url = document_url(url)
        if not url or not str(title).strip():
            return False
        data = {"url": url, "title": str(title)[:300], "description": str(description)[:1500],
                "aliases": aliases[:800], "curated": curated, "seen_at": seen_at or time.time()}
        with self.lock:
            old = self.documents.get(url)
            if old and old["curated"] and not curated:
                return False  # Public snippets never overwrite curated identity or sections.
            self.db.execute("DELETE FROM documents WHERE url = ?", (url,))
            self.db.execute("INSERT INTO documents VALUES (?, ?, ?, ?, ?)",
                            (url, data["title"], data["description"], normalized(aliases), urlsplit(url).hostname))
            self.documents[url] = data
            self.documents.move_to_end(url)
            while len(self.documents) > self.max_documents:
                removable = next((key for key, value in self.documents.items() if not value["curated"]), None)
                if removable is None:
                    break
                self.documents.pop(removable)
                self.db.execute("DELETE FROM documents WHERE url = ?", (removable,))
            self.db.commit()
        return True

    def ingest(self, results):
        learned = []
        for result in results:
            if self.add(result.url, result.title, result.description):
                learned.append({"url": document_url(result.url), "title": result.title[:300],
                                "description": result.description[:1500]})
        return learned

    def search(self, query, limit=30, mode="web", freshness=""):
        if freshness:  # Discovery time isn't publication time; don't mislabel old pages as fresh.
            return []
        scope = re.search(r"\bsite:([^\s]+)", query, re.I)
        host_scope = ""
        if scope:
            try:
                host_scope = (urlsplit("https://" + scope.group(1)).hostname or "").lower().removeprefix("www.")
            except ValueError:
                return []
            query = query[:scope.start()] + query[scope.end():]
        terms = list(dict.fromkeys(words(re.sub(r"https?://", "", query))))[:32]
        expression = " AND ".join('"' + term + '"' for term in terms)
        if not expression and not host_scope:
            return []
        sql = "SELECT *, bm25(documents, 0, 6, 2, 4, 3) AS relevance FROM documents WHERE documents MATCH ?" if expression else "SELECT *, 0 AS relevance FROM documents WHERE 1=1"
        args = [expression] if expression else []
        if host_scope:
            sql += " AND (host = ? OR substr(host, -(length(?) + 1)) = '.' || ?)"
            args.extend([host_scope, host_scope, host_scope])
        sql += " ORDER BY relevance LIMIT 120"
        phrase = normalized(query)
        matches = []
        with self.lock:
            rows = self.db.execute(sql, args).fetchall()
            for row in rows:
                metadata = self.documents[row["url"]]
                if not metadata["curated"] and time.time() - metadata["seen_at"] > 14 * 86400:
                    continue
                if mode == "exact" and phrase not in normalized(" ".join((row["title"], row["description"], row["aliases"], row["host"]))):
                    continue
                if mode == "discussions":
                    from .query_features import is_discussion_url
                    if not is_discussion_url(row["url"]):
                        continue
                homepage = urlsplit(row["url"]).path == "/"
                exact_brand = phrase in self.brands and normalized(self.brands[phrase]) == normalized(row["title"])
                score = 12 + min(16, -row["relevance"]) + (20 if exact_brand and homepage else 0)
                signals = ["index_match"] + (["domain_match", "homepage"] if exact_brand and homepage else [])
                matches.append(WebResult(title=row["title"], url=row["url"], description=row["description"],
                                         provider="nova-index", score=round(score, 4), matched_terms=terms, rank_signals=signals))
        matches.sort(key=lambda r: r.score, reverse=True)
        return matches[:limit]

    def suggest(self, query, limit=6):
        prefix = normalized(query)
        if len(prefix) < 2:
            return []
        with self.lock:
            values = [name for key, name in self.brands.items() if key.startswith(prefix)]
            values.extend(doc["title"] for doc in self.documents.values() if normalized(doc["title"]).startswith(prefix))
        return list(dict.fromkeys(values))[:limit]

    def correction(self, query):
        from .correction import _distance
        key = normalized(query)
        if len(key) < 4 or len(key) > 32 or " " in key or key in self.brands:
            return None
        candidates = sorted((_distance(key, brand), name) for brand, name in self.brands.items() if abs(len(brand) - len(key)) <= 1)
        if not candidates or candidates[0][0] != 1:
            return None
        names = {name for distance, name in candidates if distance == 1}
        return next(iter(names)) if len(names) == 1 else None

    def stats(self):
        with self.lock:
            return {"documents": len(self.documents), "curated": sum(d["curated"] for d in self.documents.values()),
                    "capacity": self.max_documents, "engine": "NOVA FTS5 / BM25"}
