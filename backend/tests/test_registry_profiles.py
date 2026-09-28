from app.verification.registry_data import REGISTRY


def test_registry_has_broad_major_company_coverage():
    assert len(REGISTRY) >= 50


def test_showcase_profiles_have_safe_product_metadata():
    for domain, item in REGISTRY.items():
        assert "." in domain
        assert item["organization"]
        assert item["category"]
        assert item.get("profile_tier") in {"standard", "showcase", "premium"}
        accent = item.get("profile_accent")
        if accent:
            assert accent.startswith("#") and len(accent) == 7
        # Commercial presentation metadata must never smuggle ranking controls.
        assert "score" not in item
        assert "rank" not in item
        assert "boost" not in item
