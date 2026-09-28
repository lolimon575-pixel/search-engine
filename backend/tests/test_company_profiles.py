from app.verification import officiality
from app.verification.registry_data import REGISTRY


def test_puma_is_profile_plus_demo_with_key_sections():
    puma = REGISTRY["puma.com"]

    assert puma["organization"] == "PUMA"
    assert puma["profile_tier"] == "premium_demo"
    assert puma["profile_badge"] == "Profile Plus Demo"
    assert puma["links"]["shop"].startswith("https://")
    assert puma["links"]["running"].startswith("https://")
    assert puma["links"]["football"].startswith("https://")
    assert puma["links"]["careers"].startswith("https://")
    assert puma["links"]["investors"].startswith("https://")
    assert puma["links"]["sustainability"].startswith("https://")
    assert REGISTRY["eu.puma.com"] is puma
    assert REGISTRY["about.puma.com"] is puma


def test_curated_profiles_have_multiple_key_sections():
    for domain in [
        "github.com",
        "microsoft.com",
        "apple.com",
        "openai.com",
        "stripe.com",
        "nvidia.com",
        "tesla.com",
        "booking.com",
    ]:
        links = REGISTRY[domain]["links"]
        assert len(links) >= 4, domain


def test_public_organization_profile_hides_stripe_object_ids(monkeypatch):
    monkeypatch.setattr(officiality, "get_site", lambda host: {
        "organization_id": 1,
        "id": 2,
        "organization": "Example",
        "url": "https://example.com",
        "category": "Technology",
        "tagline": "Example tagline",
        "description": "Example description",
        "logo_url": None,
        "links": {"about": "https://example.com/about"},
        "source": "test",
        "confirmation_level": "NOVA",
        "source_url": None,
        "last_check": None,
        "profile_tier": "premium",
        "profile_badge": "Profile Plus",
        "profile_accent": "#111111",
        "billing_status": "active",
        "billing_period_end": None,
        "stripe_customer_id": "cus_internal",
        "stripe_subscription_id": "sub_internal",
        "owner_verification": "DOMAIN_CONTROL",
        "ownership_verified_at": None,
    })

    profile = officiality.get_organization_profile("example.com")

    assert profile["profile_tier"] == "premium"
    assert profile["billing_status"] == "active"
    assert "stripe_customer_id" not in profile
    assert "stripe_subscription_id" not in profile
