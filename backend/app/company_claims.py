import ipaddress
import socket
from urllib.parse import urlsplit

import httpx

from app.registry_db import get_claim, mark_claim_verified, normalize_domain


def _assert_public_host(host):
    if not host or host in {"localhost", "127.0.0.1"} or host.endswith(".local"):
        raise ValueError("private host")
    addresses = {item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    if not addresses:
        raise ValueError("DNS address not found")
    for raw in addresses:
        ip = ipaddress.ip_address(raw)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            raise ValueError("domain points to a non-public address")


def challenge_url(domain):
    host = normalize_domain(domain)
    return f"https://{host}/.well-known/nova-site-verification.txt"


def expected_value(token):
    return f"nova-site-verification={token}"


def verify_claim_challenge(claim_id, timeout=4.0):
    claim = get_claim(claim_id)
    if not claim:
        return {"ok": False, "status": "not_found"}

    host = normalize_domain(claim["domain"])
    _assert_public_host(host)
    url = challenge_url(host)
    expected = expected_value(claim["challenge_token"])

    try:
        with httpx.Client(timeout=timeout, follow_redirects=False, headers={"User-Agent": "NOVA-Ownership/1.0"}) as client:
            response = client.get(url)
    except Exception as exc:
        return {"ok": False, "status": "unreachable", "detail": type(exc).__name__, "challenge_url": url}

    if response.status_code != 200:
        return {"ok": False, "status": "not_verified", "http_status": response.status_code, "challenge_url": url}

    body = response.text.strip()
    if body != expected:
        return {"ok": False, "status": "not_verified", "challenge_url": url}

    verified = mark_claim_verified(claim_id)
    return {
        "ok": True,
        "status": "verified",
        "domain": host,
        "verified_at": verified.get("verified_at") if verified else None,
    }
