import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import httpx

from app.registry_db import (
    create_ownership_claim,
    get_claim_status,
    get_ownership_claim,
    get_site,
    mark_ownership_verified,
    normalize_domain,
)
from app.verification.engine import VerificationEngine


CHALLENGE_PATH = "/.well-known/nova-verification.txt"
CHALLENGE_TTL_HOURS = 24
_verifier = VerificationEngine(timeout=5)


def _token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _valid_host(domain):
    host = normalize_domain(domain)
    if not host or len(host) > 253 or "." not in host:
        raise ValueError("Некорректный домен")
    _verifier._assert_public_host("https://" + host)
    return host


def create_challenge(domain):
    host = _valid_host(domain)
    if not get_site(host):
        raise ValueError("Для этого домена ещё нет NOVA Profile. Сначала домен должен пройти добавление в курируемый реестр.")
    token = "nova-" + secrets.token_urlsafe(24)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=CHALLENGE_TTL_HOURS)
    row = create_ownership_claim(host, _token_hash(token), expires_at)
    if not row:
        raise RuntimeError("Реестр подтверждения временно недоступен")
    return {
        "domain": host,
        "status": "pending",
        "method": "http-well-known",
        "challenge_path": CHALLENGE_PATH,
        "challenge_url": f"https://{host}{CHALLENGE_PATH}",
        "token": token,
        "expires_at": row["expires_at"],
        "instructions": [
            f"Создайте текстовый файл по адресу https://{host}{CHALLENGE_PATH}",
            "Поместите в файл только выданный NOVA token.",
            "После публикации нажмите «Проверить домен».",
        ],
        "ranking_note": "Подтверждение владельца и платный профиль не повышают органический NOVA Rank.",
    }


def verify_challenge(domain, token):
    host = _valid_host(domain)
    clean_token = (token or "").strip()
    if not clean_token.startswith("nova-") or len(clean_token) > 200:
        return {"domain": host, "verified": False, "status": "invalid_token"}

    token_hash = _token_hash(clean_token)
    claim = get_ownership_claim(host, token_hash)
    if not claim:
        return {"domain": host, "verified": False, "status": "challenge_not_found"}

    now = datetime.now(timezone.utc)
    if claim["status"] == "verified":
        return _verified_response(host, claim)
    if claim["expires_at"] <= now:
        return {"domain": host, "verified": False, "status": "expired"}

    url = f"https://{host}{CHALLENGE_PATH}"
    try:
        _verifier._assert_public_host(url)
        with httpx.Client(
            timeout=5,
            follow_redirects=False,
            headers={"User-Agent": "NOVA-Ownership-Verification/1.0"},
        ) as client:
            response = client.get(url)
        if response.status_code != 200:
            return {
                "domain": host,
                "verified": False,
                "status": "proof_not_reachable",
                "http_status": response.status_code,
            }
        body = response.text.strip()
        if len(body) > 4096 or body != clean_token:
            return {"domain": host, "verified": False, "status": "proof_mismatch"}
    except Exception as exc:
        return {
            "domain": host,
            "verified": False,
            "status": "proof_check_failed",
            "error": type(exc).__name__,
        }

    verified = mark_ownership_verified(host, token_hash)
    if not verified:
        return {"domain": host, "verified": False, "status": "claim_update_failed"}
    return _verified_response(host, verified)


def _verified_response(host, claim):
    profile = get_site(host)
    return {
        "domain": host,
        "verified": True,
        "status": "domain_control_verified",
        "verified_at": claim.get("verified_at"),
        "proof_method": claim.get("proof_method"),
        "profile_exists": bool(profile),
        "premium_eligible": bool(profile),
        "assurance": "Подтверждён технический контроль домена. Юридическая принадлежность компании требует отдельной проверки.",
        "ranking_note": "Статус владельца и платный профиль не добавляют баллы органическому NOVA Rank.",
    }


def ownership_status(domain):
    host = normalize_domain(domain)
    row = get_claim_status(host)
    if not isinstance(row, dict):
        row = dict(row)
    row["profile_exists"] = bool(get_site(host)) if host else False
    row["premium_eligible"] = bool(
        row.get("status") == "verified" and row.get("profile_exists")
    )
    return row
