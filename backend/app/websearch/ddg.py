from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

import httpx

from .models import WebResult


class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
        self.cur = None
        self.buf = []
        self.url = ""
        self.description_item = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = set((a.get("class") or "").split())
        if tag == "a" and "result__a" in classes:
            self.description_item = None
            self.cur = "title"
            self.buf = []
            self.url = a.get("href", "")
        elif "result__snippet" in classes:
            self.cur = "desc"
            self.buf = []

    def handle_data(self, data):
        if self.cur:
            self.buf.append(data)

    def handle_endtag(self, tag):
        if self.cur == "title" and tag == "a":
            title = " ".join("".join(self.buf).split())
            url = self.url
            try:
                parsed = urlparse(url)
                host = parsed.hostname or ""
                provider_host = host == "duckduckgo.com" or host.endswith(".duckduckgo.com")
                if provider_host and parsed.path == "/y.js":
                    url = ""  # Sponsored click redirects are not organic results.
                elif provider_host and parsed.path.startswith("/l/"):
                    url = parse_qs(parsed.query).get("uddg", [""])[0]
                target = urlparse(url)
                if title and target.scheme in {"http", "https"} and target.hostname and not target.username and not target.password:
                    self.items.append([title, url, ""])
                    self.description_item = self.items[-1]
            except ValueError:
                pass
            self.cur = None
        elif self.cur == "desc" and tag in ("a", "div"):
            if self.description_item is not None and not self.description_item[2]:
                self.description_item[2] = " ".join("".join(self.buf).split())
            self.cur = None


def search(query: str, limit=20, timeout=8, freshness=""):
    params = {"q": query}
    if freshness in {"d", "w", "m", "y"}:
        params["df"] = freshness

    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (compatible; NOVA-Search/1.8)"},
    ) as client:
        response = client.get("https://html.duckduckgo.com/html/", params=params)
        response.raise_for_status()

    parser = Parser()
    parser.feed(response.text)
    return [
        WebResult(title=title, url=url, description=description, provider_rank=index)
        for index, (title, url, description) in enumerate(parser.items[:limit], 1)
    ]
