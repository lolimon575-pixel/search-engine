import os
import hmac
import hashlib
from datetime import datetime, timezone

import stripe

from app.ownership import authorize_owner

from app.registry_db import (
    find_domain_by_customer,
    find_domain_by_subscription,
    get_billing_profile,
    normalize_domain,
    set_billing_state,
)


def _secret_key():
    return os.getenv("STRIPE_SECRET_KEY", "").strip()


def _webhook_secret():
    return os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()


def _public_url():
    return os.getenv("NOVA_PUBLIC_URL", "").strip().rstrip("/")


def _price_id():
    return os.getenv("STRIPE_PROFILE_PLUS_PRICE_ID", "").strip()


def _payment_link():
    return os.getenv("STRIPE_PROFILE_PLUS_PAYMENT_LINK", "").strip()


def configured():
    return bool((_secret_key() or _payment_link()) and _price_id() and _public_url())


def _reference_for_domain(domain):
    secret = _webhook_secret()
    if not secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET is not configured")
    encoded = normalize_domain(domain).replace(".", "_")
    signature = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()[:20]
    return f"{encoded}__{signature}"


def _domain_from_reference(reference):
    value = (reference or "").strip()
    if "__" not in value:
        return None
    encoded, supplied = value.rsplit("__", 1)
    secret = _webhook_secret()
    if not secret:
        return None
    expected = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()[:20]
    if not hmac.compare_digest(supplied, expected):
        return None
    return normalize_domain(encoded.replace("_", "."))


def _client():
    key = _secret_key()
    if not key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")
    stripe.api_key = key
    return stripe


def _require_owner_verified(domain):
    host = normalize_domain(domain)
    profile = get_billing_profile(host)
    if not profile:
        raise ValueError("NOVA Profile для этого домена не найден.")
    if profile.get("owner_verification") != "DOMAIN_CONTROL":
        raise PermissionError("Сначала подтвердите контроль домена через Owner Verification.")
    return host, profile


def create_checkout(domain, ownership_token):
    host, profile = _require_owner_verified(domain)
    if not authorize_owner(host, ownership_token):
        raise PermissionError("Нужно повторно подтвердить право управления этим доменом.")
    if profile.get("billing_status") in {"active", "trialing"}:
        raise ValueError("Profile Plus уже активен для этого домена.")

    if not _secret_key():
        link = _payment_link()
        if not link:
            raise RuntimeError("Stripe checkout is not configured")
        separator = "&" if "?" in link else "?"
        return {
            "checkout_url": f"{link}{separator}client_reference_id={_reference_for_domain(host)}",
            "session_id": None,
            "domain": host,
            "checkout_mode": "payment_link",
            "ranking_policy": "Profile Plus не влияет на органический NOVA Rank.",
        }

    client = _client()
    customer = profile.get("stripe_customer_id")
    params = {
        "mode": "subscription",
        "line_items": [{"price": _price_id(), "quantity": 1}],
        "success_url": f"{_public_url()}/?billing=success&domain={host}",
        "cancel_url": f"{_public_url()}/?billing=cancel&domain={host}",
        "allow_promotion_codes": True,
        "client_reference_id": _reference_for_domain(host),
        "metadata": {
            "nova_domain": host,
            "nova_plan": "profile_plus",
            "ranking_policy": "no_paid_ranking",
        },
        "subscription_data": {
            "metadata": {
                "nova_domain": host,
                "nova_plan": "profile_plus",
                "ranking_policy": "no_paid_ranking",
            },
            "billing_mode": {"type": "flexible"},
        },
    }
    if customer:
        params["customer"] = customer

    session = client.checkout.Session.create(**params)
    return {
        "checkout_url": session.url,
        "session_id": session.id,
        "domain": host,
        "checkout_mode": "checkout_session",
        "ranking_policy": "Profile Plus не влияет на органический NOVA Rank.",
    }


def create_portal(domain, ownership_token):
    host, profile = _require_owner_verified(domain)
    if not authorize_owner(host, ownership_token):
        raise PermissionError("Нужно повторно подтвердить право управления этим доменом.")
    customer = profile.get("stripe_customer_id")
    if not customer:
        raise ValueError("Для этого домена ещё нет Stripe Customer.")
    client = _client()
    session = client.billing_portal.Session.create(
        customer=customer,
        return_url=f"{_public_url()}/?billing=portal&domain={host}",
    )
    return {"portal_url": session.url, "domain": host}


def billing_status(domain):
    host = normalize_domain(domain)
    profile = get_billing_profile(host)
    if not profile:
        return {
            "found": False,
            "domain": host,
            "configured": configured(),
            "status": "unavailable",
        }
    return {
        "found": True,
        "domain": host,
        "configured": configured(),
        "owner_verified": profile.get("owner_verification") == "DOMAIN_CONTROL",
        "profile_tier": profile.get("profile_tier") or "standard",
        "billing_status": profile.get("billing_status") or "inactive",
        "billing_period_end": profile.get("billing_period_end"),
        "price_id": _price_id() or None,
        "mode": os.getenv("NOVA_STRIPE_MODE", "sandbox"),
        "ranking_policy": "Оплата Profile Plus не влияет на NOVA Rank.",
    }


def _period_end(subscription):
    value = subscription.get("current_period_end")
    if not value:
        return None
    return datetime.fromtimestamp(int(value), tz=timezone.utc)


def _sync_subscription(subscription, fallback_domain=None):
    metadata = subscription.get("metadata") or {}
    domain = normalize_domain(metadata.get("nova_domain") or fallback_domain or "")
    if not domain:
        domain = find_domain_by_subscription(subscription.get("id"))
    if not domain:
        domain = find_domain_by_customer(subscription.get("customer"))
    if not domain:
        return None

    return set_billing_state(
        domain,
        customer_id=subscription.get("customer"),
        subscription_id=subscription.get("id"),
        status=subscription.get("status"),
        period_end=_period_end(subscription),
    )


def handle_webhook(payload, signature):
    secret = _webhook_secret()
    if not secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET is not configured")

    event = stripe.Webhook.construct_event(payload, signature, secret)
    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        reference = obj.get("client_reference_id") or ""
        verified_reference_domain = _domain_from_reference(reference)
        metadata_domain = normalize_domain((obj.get("metadata") or {}).get("nova_domain") or "")
        domain = metadata_domain or verified_reference_domain or ""
        subscription_id = obj.get("subscription")
        if domain:
            set_billing_state(
                domain,
                customer_id=obj.get("customer"),
                subscription_id=subscription_id,
                status="active" if obj.get("payment_status") == "paid" else "incomplete",
            )
        if subscription_id and _secret_key():
            client = _client()
            subscription = client.Subscription.retrieve(subscription_id)
            _sync_subscription(subscription, fallback_domain=domain)

    elif event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        _sync_subscription(obj)

    elif event_type == "invoice.payment_failed":
        subscription_id = obj.get("subscription")
        customer_id = obj.get("customer")
        domain = find_domain_by_subscription(subscription_id) or find_domain_by_customer(customer_id)
        if domain:
            set_billing_state(
                domain,
                customer_id=customer_id,
                subscription_id=subscription_id,
                status="past_due",
            )

    return {"received": True, "type": event_type}
