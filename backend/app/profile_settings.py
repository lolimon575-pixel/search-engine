"""Owner-controlled presentation for active Profile Plus subscriptions."""
import re
from urllib.parse import urlsplit

from pydantic import BaseModel, Field

from app.registry_db import get_site, normalize_domain, update_profile_settings


def authorize_owner(domain, token):
    # Ownership's verifier imports public profile presentation, so load this lazily.
    from app.ownership import authorize_owner as check
    return check(domain, token)


class ProfileLink(BaseModel):
    label: str = Field(min_length=1, max_length=40)
    url: str = Field(min_length=1, max_length=1000)


class ProfileSettingsRequest(BaseModel):
    domain: str = Field(min_length=1, max_length=253)
    ownership_token: str = Field(min_length=1, max_length=200)
    tagline: str = Field(default="", max_length=120)
    description: str = Field(default="", max_length=500)
    accent: str = Field(default="#365fb7", max_length=7)
    primary_label: str = Field(default="", max_length=40)
    primary_url: str = Field(default="", max_length=1000)
    links: list[ProfileLink] = Field(default_factory=list, max_length=8)


def _owned_url(value, domain, existing_urls):
    value = value.strip()
    try:
        parsed = urlsplit(value)
        host = normalize_domain(parsed.hostname or "")
        valid = (parsed.scheme == "https" and host and not parsed.username
                 and not parsed.password and parsed.port in {None, 443})
    except ValueError:
        valid = False
        host = ""
    if not valid or not (host == domain or host.endswith("." + domain) or value in existing_urls):
        raise ValueError("Ссылки должны вести на ваш HTTPS-домен или уже указанный официальный раздел.")
    return value


def save_profile_settings(body):
    domain = normalize_domain(body.domain)
    # Prove domain control before reading or changing the paid presentation.
    if not authorize_owner(domain, body.ownership_token):
        raise PermissionError("Подтвердите право управления доменом на этом устройстве.")
    site = get_site(domain)
    if not site or site.get("owner_verification") != "DOMAIN_CONTROL":
        raise PermissionError("Сначала подтвердите контроль домена.")
    if site.get("billing_status") not in {"active", "trialing"}:
        raise PermissionError("Редактирование карточки доступно с активным Profile Plus.")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", body.accent):
        raise ValueError("Выберите цвет в формате #RRGGBB.")
    existing_urls = set((site.get("links") or {}).values()) | {site["url"]}
    links = {}
    for link in body.links:
        label = link.label.strip()
        if not label or label in links:
            raise ValueError("Названия разделов должны быть непустыми и разными.")
        links[label] = _owned_url(link.url, domain, existing_urls)
    if bool(body.primary_label.strip()) != bool(body.primary_url.strip()):
        raise ValueError("Укажите название и ссылку основного действия.")
    settings = {
        "tagline": body.tagline.strip(), "description": body.description.strip(),
        "profile_accent": body.accent.lower(), "links": links,
        "primary_action": {
            "label": body.primary_label.strip(),
            "url": _owned_url(body.primary_url, domain, existing_urls),
        } if body.primary_url.strip() else None,
    }
    if not update_profile_settings(domain, settings):
        raise PermissionError("Карточка недоступна для редактирования. Проверьте статус подписки.")
    return {"saved": True, "domain": domain}


def apply_profile_settings(profile, settings):
    # Cancellation removes paid presentation; stored settings survive renewal.
    if profile.get("billing_status") not in {"active", "trialing"} or not isinstance(settings, dict):
        return profile
    return {**profile, **{key: settings[key] for key in (
        "tagline", "description", "profile_accent", "links", "primary_action"
    ) if key in settings}}
