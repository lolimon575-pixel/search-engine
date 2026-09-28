from app.verification.registry_data import REGISTRY


def test_registry_has_broad_major_company_coverage():
    assert len(REGISTRY) >= 50


def test_showcase_profiles_have_safe_product_metadata():
    for domain, item in REGISTRY.items():
        assert "." in domain
        assert item["organization"]
        assert item["category"]
        assert item.get("profile_tier") in {"standard", "showcase", "premium", "premium_demo"}
        accent = item.get("profile_accent")
        if accent:
            assert accent.startswith("#") and len(accent) == 7
        # Commercial presentation metadata must never smuggle ranking controls.
        assert "score" not in item
        assert "rank" not in item
        assert "boost" not in item


def test_registry_contains_russian_official_sites():
    expected = {
        "yandex.ru",
        "vk.com",
        "mail.ru",
        "sberbank.ru",
        "tbank.ru",
        "ozon.ru",
        "wildberries.ru",
        "avito.ru",
        "kaspersky.ru",
        "2gis.ru",
        "hh.ru",
        "mts.ru",
        "megafon.ru",
        "beeline.ru",
        "rt.ru",
        "alfa-bank.ru",
        "vtb.ru",
        "kinopoisk.ru",
        "rutube.ru",
        "rbc.ru",
        "gazprombank.ru",
        "yota.ru",
        "cian.ru",
        "lamoda.ru",
        "okko.tv",
    }
    assert expected.issubset(REGISTRY.keys())


def test_registry_profile_links_are_https():
    for domain, item in REGISTRY.items():
        for key, url in (item.get("links") or {}).items():
            assert url.startswith("https://"), f"{domain}:{key} must use HTTPS"


def test_new_russian_profiles_have_useful_key_sections():
    assert len(REGISTRY["rutube.ru"]["links"]) >= 3
    assert len(REGISTRY["rbc.ru"]["links"]) >= 3
    assert len(REGISTRY["gazprombank.ru"]["links"]) >= 4
    assert len(REGISTRY["yota.ru"]["links"]) >= 4
