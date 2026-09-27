from datetime import datetime, timezone
from urllib.parse import urljoin,urlsplit
from urllib.request import Request,build_opener
from urllib.error import HTTPError
import ipaddress,json,re,socket,time
from html import unescape
from .officiality import verify_officiality

class VerificationEngine:
    def __init__(self,timeout=3,ttl=600):
        self.timeout=timeout; self.ttl=ttl; self.cache={}
    def peek(self,url):
        x=self.cache.get(url)
        return {**x["data"],"cached":True} if x and time.time()-x["ts"]<self.ttl else {}
    def verify(self,url,**_):
        cached=self.peek(url)
        if cached:return cached
        started=time.monotonic(); checked=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
        original=(urlsplit(url).hostname or "").lower(); current=url; redirects=[]; reasons=[]; status=None; ctype=""; body=b""
        try:
            self._assert_public_host(current)
            req=Request(current,headers={"User-Agent":"NOVA-Verification/1.0","Range":"bytes=0-16384"})
            try:
                with build_opener().open(req,timeout=self.timeout) as r:
                    status=r.status or r.getcode(); final=r.geturl() or current; ctype=r.headers.get("Content-Type",""); body=r.read(16384)
            except HTTPError as e:
                status=e.code; final=current
        except Exception as e:
            final=current; reasons.append("Сетевая проверка: "+type(e).__name__)
        final_host=(urlsplit(final).hostname or "").lower(); https=urlsplit(final).scheme.lower()=="https"
        if original and final_host and original!=final_host: reasons.append("После перенаправления изменился домен")
        if not https: reasons.append("Соединение не использует HTTPS")
        if status is None: reasons.append("HTTP-ответ не получен")
        elif status>=400: reasons.append(f"Сайт вернул HTTP {status}")
        technical_ok=https and status is not None and 200<=status<400 and not reasons
        signals=self._extract_signals(body,ctype)
        data={"status":"VERIFIED" if technical_ok else "WARNING","checked_at":checked,"cached":False,"url":url,"duration_ms":round((time.monotonic()-started)*1000),"reasons":reasons or ["HTTPS и HTTP-проверка пройдены."],"officiality":verify_officiality(final,signals),"technical":{"https":https,"http_status":status,"final_url":final,"redirects":redirects,"content_type":ctype,"original_host":original,"final_host":final_host,"dns_resolved":not bool(reasons)}}
        self.cache[url]={"ts":time.time(),"data":data}; return data
    def _assert_public_host(self,url):
        host=(urlsplit(url).hostname or "").lower()
        if not host or host in ("localhost","127.0.0.1") or host.endswith(".local"): raise ValueError("private host")
        for raw in {x[4][0] for x in socket.getaddrinfo(host,None,type=socket.SOCK_STREAM)}:
            ip=ipaddress.ip_address(raw)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved: raise ValueError("private destination")
    @staticmethod
    def _extract_signals(body,ctype):
        out={"canonical":"","organization":"","same_as":[]}
        if not body or "html" not in ctype.lower(): return out
        text=body.decode("utf-8",errors="ignore")
        m=re.search(r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\']([^"\']+)',text,re.I)
        if m: out["canonical"]=m.group(1)
        for raw in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',text,re.I|re.S):
            try: data=json.loads(unescape(raw).strip())
            except Exception: continue
            nodes=data if isinstance(data,list) else [data]
            for n in nodes:
                if not isinstance(n,dict): continue
                typ=n.get("@type",[]); typ=[typ] if isinstance(typ,str) else typ
                if any(str(t).lower() in {"organization","corporation","brand","website"} for t in typ):
                    out["organization"]=n.get("name") or out["organization"]
                    same=n.get("sameAs",[]); same=[same] if isinstance(same,str) else same
                    out["same_as"].extend(x for x in same if isinstance(x,str))
        out["same_as"]=list(dict.fromkeys(out["same_as"]))[:10]; return out
