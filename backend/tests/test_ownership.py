from datetime import datetime, timedelta, timezone

import app.ownership as ownership


class _Response:
    status_code = 200

    def __init__(self, text):
        self.text = text


class _Client:
    def __init__(self, token, **_):
        self.token = token

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def get(self, _url):
        return _Response(self.token)


def test_owner_verification_requires_matching_well_known_token(monkeypatch):
    token = "nova-test-token"
    private_token = "nova-owner-private-test"
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(ownership, "_valid_host", lambda _domain: "example.com")
    monkeypatch.setattr(
        ownership,
        "get_ownership_claim",
        lambda *_: {
            "status": "pending",
            "owner_token_hash": ownership._token_hash(private_token),
            "expires_at": now + timedelta(hours=1),
            "proof_method": "http-well-known",
        },
    )
    monkeypatch.setattr(
        ownership,
        "mark_ownership_verified",
        lambda *_: {
            "verified_at": now,
            "proof_method": "http-well-known",
        },
    )
    monkeypatch.setattr(ownership, "get_site", lambda *_: {"id": 1})
    monkeypatch.setattr(ownership._verifier, "_assert_public_host", lambda *_: None)
    monkeypatch.setattr(ownership.httpx, "Client", lambda **kwargs: _Client(token, **kwargs))

    result = ownership.verify_challenge("example.com", token, private_token)

    assert result["verified"] is True
    assert result["status"] == "domain_control_verified"
    assert result["premium_eligible"] is True


def test_payment_is_not_part_of_domain_verification_result(monkeypatch):
    claim = {"verified_at": datetime.now(timezone.utc), "proof_method": "http-well-known"}
    monkeypatch.setattr(ownership, "get_site", lambda *_: {"id": 1})

    result = ownership._verified_response("example.com", claim)

    assert "payment" not in result
    assert "rank" in result["ranking_note"].lower()


def test_public_proof_never_authorizes_billing(monkeypatch):
    monkeypatch.setattr(ownership, "_valid_host", lambda domain: domain)
    monkeypatch.setattr(ownership, "owner_token_authorized", lambda *_: True)
    assert ownership.authorize_owner("example.com", "nova-public-proof") is False


def test_private_credential_is_hashed_for_authorization(monkeypatch):
    monkeypatch.setattr(ownership, "_valid_host", lambda domain: domain)
    calls = []
    def lookup(domain, token_hash):
        calls.append((domain, token_hash))
        return True
    monkeypatch.setattr(ownership, "owner_token_authorized", lookup)
    assert ownership.authorize_owner("example.com", "nova-owner-private") is True
    assert calls == [("example.com", ownership._token_hash("nova-owner-private"))]


def test_public_proof_cannot_claim_an_existing_verification(monkeypatch):
    monkeypatch.setattr(ownership, "_valid_host", lambda domain: domain)
    monkeypatch.setattr(ownership, "get_ownership_claim", lambda *_: {
        "status": "verified", "owner_token_hash": ownership._token_hash("nova-owner-secret"),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
    })
    result = ownership.verify_challenge("example.com", "nova-public-proof", "nova-owner-attacker")
    assert result["verified"] is False
    assert result["status"] == "invalid_owner_token"


def test_legacy_claim_without_private_credential_is_rejected(monkeypatch):
    monkeypatch.setattr(ownership, "_valid_host", lambda domain: domain)
    monkeypatch.setattr(ownership, "get_ownership_claim", lambda *_: {"status": "verified"})
    assert ownership.verify_challenge("example.com", "nova-public-proof")["verified"] is False


def test_verified_claim_still_expires(monkeypatch):
    private = "nova-owner-secret"
    monkeypatch.setattr(ownership, "_valid_host", lambda domain: domain)
    monkeypatch.setattr(ownership, "get_ownership_claim", lambda *_: {
        "status": "verified", "owner_token_hash": ownership._token_hash(private),
        "expires_at": datetime.now(timezone.utc) - timedelta(seconds=1),
    })
    result = ownership.verify_challenge("example.com", "nova-public-proof", private)
    assert result["status"] == "expired"
    assert result["verified"] is False


def test_challenge_separates_public_proof_from_private_credential(monkeypatch):
    monkeypatch.setattr(ownership, "_valid_host", lambda domain: domain)
    monkeypatch.setattr(ownership, "get_site", lambda *_: {"id": 1})
    stored = []
    def create(domain, proof_hash, expires, private_hash):
        stored.append((proof_hash, private_hash))
        return {"expires_at": expires}
    monkeypatch.setattr(ownership, "create_ownership_claim", create)
    result = ownership.create_challenge("example.com")
    assert result["token"] != result["owner_token"]
    assert stored == [(ownership._token_hash(result["token"]), ownership._token_hash(result["owner_token"]))]
    assert all(result["owner_token"] not in instruction for instruction in result["instructions"])


def test_challenge_response_is_not_cacheable(monkeypatch):
    from fastapi.testclient import TestClient
    from app import main
    monkeypatch.setattr(main, 'create_challenge', lambda domain: {'token': 'public', 'owner_token': 'private'})
    response = TestClient(main.app).post('/api/ownership/challenge', json={'domain': 'example.com'})
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'


def test_verification_api_requires_private_credential():
    from fastapi.testclient import TestClient
    from app import main
    response = TestClient(main.app).post('/api/ownership/verify', json={'domain': 'example.com', 'token': 'nova-public'})
    assert response.status_code == 422
