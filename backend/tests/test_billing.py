import os

from app import billing


def test_signed_domain_reference_round_trip(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")
    ref = billing._reference_for_domain("example.com")

    assert "__" in ref
    assert billing._domain_from_reference(ref) == "example.com"


def test_signed_domain_reference_rejects_tampering(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")
    ref = billing._reference_for_domain("example.com")
    encoded, signature = ref.rsplit("__", 1)

    assert billing._domain_from_reference("evil_com__" + signature) is None


def test_billing_configured_accepts_payment_link_fallback(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.setenv("STRIPE_PROFILE_PLUS_PAYMENT_LINK", "https://buy.stripe.com/test_demo")
    monkeypatch.setenv("STRIPE_PROFILE_PLUS_PRICE_ID", "price_demo")
    monkeypatch.setenv("NOVA_PUBLIC_URL", "https://nova.example")

    assert billing.configured() is True


def test_public_billing_status_does_not_expose_stripe_ids(monkeypatch):
    monkeypatch.setattr(billing, "get_billing_profile", lambda domain: {
        "owner_verification": "DOMAIN_CONTROL",
        "profile_tier": "premium",
        "billing_status": "active",
        "billing_period_end": None,
        "stripe_customer_id": "cus_secret",
        "stripe_subscription_id": "sub_secret",
    })
    monkeypatch.setenv("STRIPE_PROFILE_PLUS_PAYMENT_LINK", "https://buy.stripe.com/test_demo")
    monkeypatch.setenv("STRIPE_PROFILE_PLUS_PRICE_ID", "price_demo")
    monkeypatch.setenv("NOVA_PUBLIC_URL", "https://nova.example")

    status = billing.billing_status("example.com")

    assert status["billing_status"] == "active"
    assert "customer_id" not in status
    assert "subscription_id" not in status
