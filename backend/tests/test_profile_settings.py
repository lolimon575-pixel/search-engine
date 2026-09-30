import pytest
from pydantic import ValidationError

from app import profile_settings as settings


@pytest.fixture
def owner(monkeypatch):
    site = {"url": "https://example.com", "owner_verification": "DOMAIN_CONTROL",
            "billing_status": "active", "links": {"support": "https://support.vendor.com/example"}}
    saved = []
    monkeypatch.setattr(settings, "authorize_owner", lambda domain, token: token == "valid")
    monkeypatch.setattr(settings, "get_site", lambda domain: site)
    monkeypatch.setattr(settings, "update_profile_settings", lambda domain, data: saved.append((domain, data)) or True)
    return site, saved


def request(**overrides):
    return settings.ProfileSettingsRequest(domain="example.com", ownership_token="valid", **overrides)


def test_paid_owner_can_save_presentation_without_changing_trust(owner):
    _, saved = owner
    result = settings.save_profile_settings(request(tagline=" Our catalog ", primary_label="Catalog",
        primary_url="https://example.com/catalog", links=[{"label": "Help", "url": "https://help.example.com/"}]))
    assert result["saved"]
    assert saved[0][0] == "example.com"
    assert saved[0][1]["tagline"] == "Our catalog"
    assert saved[0][1]["primary_action"]["url"] == "https://example.com/catalog"
    assert "owner_verification" not in saved[0][1]
    assert "billing_status" not in saved[0][1]


@pytest.mark.parametrize("url", ["javascript:alert(1)", "http://example.com/", "https://example.com.evil.org/",
                                 "https://evil.org/", "https://user:pass@example.com/", "https://example.com:8443/",
                                 "https://[broken/"])
def test_owner_cannot_publish_unapproved_links(owner, url):
    with pytest.raises(ValueError):
        settings.save_profile_settings(request(primary_label="Go", primary_url=url))
    assert owner[1] == []


def test_existing_official_external_link_remains_editable(owner):
    settings.save_profile_settings(request(links=[{"label": "Support", "url": "https://support.vendor.com/example"}]))
    with pytest.raises(ValueError):
        settings.save_profile_settings(request(links=[{"label": "Other", "url": "https://support.vendor.com/other"}]))


@pytest.mark.parametrize("status", ["inactive", "canceled", "past_due", "premium_demo"])
def test_non_subscribers_cannot_save(owner, status):
    owner[0]["billing_status"] = status
    with pytest.raises(PermissionError):
        settings.save_profile_settings(request())
    assert owner[1] == []


def test_token_and_owner_control_are_both_required(owner):
    with pytest.raises(PermissionError):
        settings.save_profile_settings(settings.ProfileSettingsRequest(domain="example.com", ownership_token="wrong"))
    owner[0]["owner_verification"] = "unverified"
    with pytest.raises(PermissionError):
        settings.save_profile_settings(request())
    assert owner[1] == []


def test_cancellation_between_read_and_write_is_rejected(owner, monkeypatch):
    monkeypatch.setattr(settings, "update_profile_settings", lambda domain, data: False)
    with pytest.raises(PermissionError):
        settings.save_profile_settings(request())


def test_custom_presentation_disappears_on_cancellation_without_overriding_trust():
    custom = {"tagline": "Custom", "billing_status": "active", "owner_verification": "DOMAIN_CONTROL"}
    base = {"tagline": "Registry", "billing_status": "canceled", "owner_verification": "unverified"}
    assert settings.apply_profile_settings(base, custom) == base
    base["billing_status"] = "active"
    result = settings.apply_profile_settings(base, custom)
    assert result["tagline"] == "Custom"
    assert result["owner_verification"] == "unverified"


def test_editor_limits_and_primary_pair(owner):
    with pytest.raises(ValidationError):
        request(links=[{"label": str(i), "url": "https://example.com"} for i in range(9)])
    with pytest.raises(ValueError):
        settings.save_profile_settings(request(primary_label="Go"))
    with pytest.raises(ValidationError):
        settings.save_profile_settings(request(accent="red;display:none"))
    with pytest.raises(ValueError):
        settings.save_profile_settings(request(links=[{"label": "Help", "url": "https://example.com"},
                                                     {"label": " Help ", "url": "https://example.com/help"}]))


def test_editor_api_rejects_an_invalid_owner_token(owner):
    from fastapi.testclient import TestClient
    from app.main import app
    response = TestClient(app).post("/api/organization/profile", json={
        "domain": "example.com", "ownership_token": "wrong", "tagline": "Changed"})
    assert response.status_code == 403
    assert owner[1] == []


def test_editor_api_hides_internal_storage_errors(monkeypatch):
    from fastapi.testclient import TestClient
    from app import main

    def unavailable(body):
        raise RuntimeError("private database connection details")

    monkeypatch.setattr(main, "save_profile_settings", unavailable)
    response = TestClient(main.app).post("/api/organization/profile", json={
        "domain": "example.com", "ownership_token": "valid"})
    assert response.status_code == 503
    assert "private database" not in response.text
