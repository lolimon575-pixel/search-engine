from datetime import datetime, timezone
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
import hashlib, ipaddress, json, re, socket, time
from html import unescape
from .officiality import verify_officiality


class _RedirectRecorder(HTTPRedirectHandler):
    def __init__(self):
        super().__init__()
        self.history = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.history.append({
            "from": req.full_url,
            "to": newurl,
            "status": code,
        })
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class VerificationEngine:
    def __init__(self, timeout=5, ttl=600):
        self.timeout = timeout
        self.ttl = ttl
        self.cache = {}

    def peek(self, url):
        x = self.cache.get(url)
        if x and time.time() - x["ts"] < self.ttl:
            return {**x["data"], "cached": True}
        return {}

    def verify(self, url, **_):
        cached = self.peek(url)
        if cached:
            return cached

        started = time.monotonic()
        checked = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        original_host = (urlsplit(url).hostname or "").lower().rstrip(".")
        current = url
        final = url
        redirects = []
        reasons = []
        dns_resolved = False
        https = urlsplit(url).scheme.lower() == "https"
        http_status = None
        content_type = ""
        body = b""

        try:
            dns_resolved = self._resolve_public_host(original_host)
        except Exception as e:
            reasons.append("DNS: " + str(e))

        try:
            self._assert_public_host(url)
            recorder = _RedirectRecorder()
            opener = build_opener(recorder)
            req = Request(
                url,
                headers={
                    "User-Agent": "NOVA-Verification/1.1",
                    "Range": "bytes=0-32767",
                    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
                },
            )
            try:
                with opener.open(req, timeout=self.timeout) as response:
                    http_status = response.status or response.getcode()
                    final = response.geturl() or url
                    content_type = response.headers.get("Content-Type", "")
                    body = response.read(32768)
            except HTTPError as e:
                http_status = e.code
                final = e.geturl() or url
                content_type = e.headers.get("Content-Type", "") if e.headers else ""
            redirects = recorder.history
        except Exception as e:
            reasons.append("Сетевая проверка: " + type(e).__name__)

        final_host = (urlsplit(final).hostname or "").lower().rstrip(".")
        final_https = urlsplit(final).scheme.lower() == "https"

        if original_host and final_host and original_host != final_host:
            reasons.append("После перенаправления изменился домен")
        if not final_https:
            reasons.append("Конечный адрес не использует HTTPS")
        if http_status is None:
            reasons.append("HTTP-ответ не получен")
        elif http_status >= 400:
            reasons.append(f"Сайт вернул HTTP {http_status}")

        technical_ok = (
            dns_resolved
            and final_https
            and http_status is not None
            and 200 <= http_status < 400
            and not (original_host and final_host and original_host != final_host)
        )

        signals = self._extract_signals(body, content_type)
        officiality = verify_officiality(final, signals)

        if technical_ok:
            status = "VERIFIED"
            status_reasons = ["DNS, HTTPS и HTTP-проверка пройдены."]
        else:
            status = "WARNING"
            status_reasons = reasons or ["Не все технические проверки пройдены."]

        data = {
            "status": status,
            "checked_at": checked,
            "cached": False,
            "url": url,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "reasons": status_reasons,
            "officiality": officiality,
            "technical": {
                "dns_resolved": dns_resolved,
                "https": https,
                "final_https": final_https,
                "http_status": http_status,
                "final_url": final,
                "redirects": redirects,
                "content_type": content_type,
                "original_host": original_host,
                "final_host": final_host,
                "redirect_count": len(redirects),
            },
            "verification_version": "1.4.0",
        }

        self.cache[url] = {"ts": time.time(), "data": data}
        return data

    def _resolve_public_host(self, host):
        if not host:
            raise ValueError("домен не определён")
        addresses = set()
        for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM):
            addresses.add(item[4][0])
        if not addresses:
            raise ValueError("DNS-адрес не найден")
        for raw in addresses:
            ip = ipaddress.ip_address(raw)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
                raise ValueError("домен указывает на непубличный адрес")
        return True

    def _assert_public_host(self, url):
        host = (urlsplit(url).hostname or "").lower()
        if not host or host in ("localhost", "127.0.0.1") or host.endswith(".local"):
            raise ValueError("private host")
        self._resolve_public_host(host)

    @staticmethod
    def _extract_signals(body, ctype):
        out = {"canonical": "", "organization": "", "same_as": []}
        if not body or "html" not in ctype.lower():
            return out

        text = body.decode("utf-8", errors="ignore")
        m = re.search(
            r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\']([^"\']+)',
            text,
            re.I,
        )
        if m:
            out["canonical"] = m.group(1)

        for raw in re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            text,
            re.I | re.S,
        ):
            try:
                data = json.loads(unescape(raw).strip())
            except Exception:
                continue
            nodes = data if isinstance(data, list) else [data]
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                typ = node.get("@type", [])
                typ = [typ] if isinstance(typ, str) else typ
                if any(str(t).lower() in {"organization", "corporation", "brand", "website"} for t in typ):
                    out["organization"] = node.get("name") or out["organization"]
                    same = node.get("sameAs", [])
                    same = [same] if isinstance(same, str) else same
                    out["same_as"].extend(x for x in same if isinstance(x, str))

        out["same_as"] = list(dict.fromkeys(out["same_as"]))[:10]
        return out
