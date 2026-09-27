from datetime import datetime, timezone
from urllib.parse import urljoin,urlsplit
from urllib.request import Request,build_opener
from urllib.error import HTTPError
import ipaddress,json,re,socket,time
from html import unescape
from .officiality import verify_officiality

class VerificationEngine:
    def __init__(self,timeout=3,ttl=600,max_redirects=4): self.timeout=timeout; self.ttl=ttl; self.max_redirects=max_redirects; self.cache={}
    def peek(self,url):
        item=self.cache.get(url)
        if item and time.time()-item["ts"]<self.ttl: return {**item["data"],"cached":True}
        return {}
    def verify(self,url,query="",title=""):
        cached=self.peek(url)
        if cached:return cached
        started=time.monotonic(); checked=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
        current=url; redirects=[]; reasons=[]; http_status=None; content_type=""; body=b""; original=(urlsplit(url).hostname or "").lower(); dns=False
        try:
            for _ in range(self.max_redirects+1):
                self._assert_public_host(current); dns=True
                req=Request(current,headers={"User-Agent":"NOVA-Verification/1.0","Range":"bytes=0-16384"})
                try:
                    with build_opener().open(req,timeout=self.timeout) as response:
                        http_status=response.status or response.getcode(); final=response.geturl() or current; content_type=response.headers.get("Content-Type",""); body=response.read(16384)
                except HTTPError as exc:
                    http_status=exc.code; final=current; location=exc.headers.get("Location") if exc.headers else None
                    if location and exc.code in (301,302,303,307,308): current=urljoin(current,location); redirects.append(current); continue
                break
        except Exception as exc:
            final=current; reasons.append("Сетевая проверка завершилась: "+type(exc).__name__)
        final_host=(urlsplit(final).hostname or "").lower(); https=urlsplit(final).scheme.lower()=="https"
        if original and final_host and original!=final_host: reasons.append("После перенаправления изменился домен")
        if not https: reasons.append("Соединение не использует HTTPS")
        if http_status is None: reasons.append("HTTP-ответ не получен")
        elif http_status>=400: reasons.append(f"Сайт вернул HTTP {http_status}")
        technical_ok=https and http_status is not None and 200<=http_status<400 and not reasons
        signals=self._extract_signals(body,content_type)
        data={"status":"VERIFIED" if technical_ok else "WARNING","checked_at":checked,"cached":False,"url":url,"duration_ms":round((time.monotonic()-started)*1000),"reasons":reasons or ["HTTPS и HTTP-проверка пройдены."],"officiality":verify_officiality(final,signals),"technical":{"https":https,"http_status":http_status,"final_url":final,"redirects":redirects,"content_type":content_type,"original_host":original,"final_host":final_host,"dns_resolved":dns,"site_signals":signals}}
        self.cache[url]={"ts":time.time(),"data":data}; return data
    def _assert_public_host(self,url):
        host=(urlsplit(url).hostname or "").lower()
        if not host or host in ("localhost","localhost.localdomain") or host.endswith(".local"): raise ValueError("private host")
        addresses={x[4][0] for x in socket.getaddrinfo(host,None,type=socket.SOCK_STREAM)}
        if not addresses: raise ValueError("no DNS")
        for raw in addresses:
            ip=ipaddress.ip_address(raw)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified: raise ValueError("private destination")
    @staticmethod
    def _extract_signals(body,content_type):
        out={"canonical":"","organization":"","organization_url":"","same_as":[],"logo":"","types":[]}
        if not body or "html" not in (content_type or "").lower(): return out
        text=body.decode("utf-8",errors="ignore")
        m=re.search(r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\']([^"\']+)',text,re.I)
        if m: out["canonical"]=m.group(1)
        for raw in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',text,re.I|re.S):
            try:data=json.loads(unescape(raw).strip())
            except Exception:continue
            nodes=data if isinstance(data,list) else [data]
            for node in nodes:
                if not isinstance(node,dict):continue
                if isinstance(node.get("@graph"),list):nodes.extend(node["@graph"])
                types=node.get("@type",[]); types=[types] if isinstance(types,str) else types; out["types"].extend(map(str,types))
                if any(str(t).lower() in {"organization","corporation","brand","website"} for t in types):
                    out["organization"]=node.get("name") or out["organization"]; out["organization_url"]=node.get("url") or out["organization_url"]; same=node.get("sameAs",[]); same=[same] if isinstance(same,str) else same; out["same_as"].extend(x for x in same if isinstance(x,str))
        out["types"]=list(dict.fromkeys(out["types"]))[:10]; out["same_as"]=list(dict.fromkeys(out["same_as"]))[:10]; return out
