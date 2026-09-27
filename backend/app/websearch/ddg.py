from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlparse
import httpx
from .models import WebResult

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(); self.items=[]; self.cur=None; self.buf=[]; self.url=""
    def handle_starttag(self, tag, attrs):
        a=dict(attrs); classes=set((a.get("class") or "").split())
        if tag == "a" and "result__a" in classes:
            self.cur="title"; self.buf=[]; self.url=a.get("href","")
        elif "result__snippet" in classes:
            self.cur="desc"; self.buf=[]
    def handle_data(self, data):
        if self.cur: self.buf.append(data)
    def handle_endtag(self, tag):
        if self.cur == "title" and tag == "a":
            title=" ".join("".join(self.buf).split()); url=self.url; p=urlparse(url)
            if p.netloc.endswith("duckduckgo.com") and p.path.startswith("/l/"):
                url=unquote(parse_qs(p.query).get("uddg",[""])[0])
            if title and url.startswith(("http://","https://")): self.items.append([title,url,""])
            self.cur=None
        elif self.cur == "desc" and tag in ("a","div"):
            if self.items and not self.items[-1][2]: self.items[-1][2]=" ".join("".join(self.buf).split())
            self.cur=None

def search(query: str, limit: int = 20, timeout: float = 8) -> list[WebResult]:
    with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent":"Mozilla/5.0 (compatible; NOVA-Search/1.0)","Accept-Language":"ru,en;q=0.8"}) as client:
        response=client.get("https://html.duckduckgo.com/html/",params={"q":query}); response.raise_for_status()
    parser=Parser(); parser.feed(response.text)
    return [WebResult(title=t,url=u,description=d,provider_rank=i) for i,(t,u,d) in enumerate(parser.items[:limit],1)]
