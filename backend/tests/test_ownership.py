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
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(ownership, "_valid_host", lambda _domain: "example.com")
    monkeypatch.setattr(
        ownership,
        "get_ownership_claim",
        lambda *_: {
            "status": "pending",
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

    result = ownership.verify_challenge("example.com", token)

    assert result["verified"] is True
    assert result["status"] == "domain_control_verified"
    assert result["premium_eligible"] is True


def test_payment_is_not_part_of_domain_verification_result(monkeypatch):
    claim = {"verified_at": datetime.now(timezone.utc), "proof_method": "http-well-known"}
    monkeypatch.setattr(ownership, "get_site", lambda *_: {"id": 1})

    result = ownership._verified_response("example.com", claim)

    assert "payment" not in result
    assert "rank" in result["ranking_note"].lower()
