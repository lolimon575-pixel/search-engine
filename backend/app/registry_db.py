import json
import os
from datetime import datetime, timezone
from urllib.parse import urlsplit

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:
    psycopg = None
    dict_row = None


def database_url():
    return os.getenv("DATABASE_URL", "").strip()


def enabled():
    return bool(database_url()) and psycopg is not None


def _connect():
    if not enabled():
        return None
    return psycopg.connect(database_url(), row_factory=dict_row, connect_timeout=5)


def ensure_schema():
    if not enabled():
        return False
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS organizations (
                    id BIGSERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL UNIQUE,
                    category TEXT,
                    description TEXT,
                    logo_url TEXT,
                    links JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS official_sites (
                    id BIGSERIAL PRIMARY KEY,
                    organization_id BIGINT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                    domain TEXT NOT NULL UNIQUE,
                    url TEXT NOT NULL,
                    registry_status TEXT NOT NULL DEFAULT 'active',
                    confirmation_level TEXT NOT NULL DEFAULT 'NOVA',
                    source TEXT NOT NULL DEFAULT 'NOVA curated registry',
                    source_url TEXT,
                    notes TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS site_checks (
                    id BIGSERIAL PRIMARY KEY,
                    site_id BIGINT NOT NULL REFERENCES official_sites(id) ON DELETE CASCADE,
                    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    technical_status TEXT,
                    officiality_status TEXT,
                    officiality_method TEXT,
                    http_status INTEGER,
                    dns_resolved BOOLEAN,
                    https BOOLEAN,
                    final_domain TEXT,
                    verification_id TEXT,
                    evidence JSONB NOT NULL DEFAULT '[]'::jsonb
                );
                CREATE TABLE IF NOT EXISTS ownership_claims (
                    id BIGSERIAL PRIMARY KEY,
                    domain TEXT NOT NULL,
                    challenge_hash TEXT NOT NULL,
                    proof_method TEXT NOT NULL DEFAULT 'http-well-known',
                    status TEXT NOT NULL DEFAULT 'pending',
                    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    expires_at TIMESTAMPTZ NOT NULL,
                    verified_at TIMESTAMPTZ
                );
            """)
            cur.execute("ALTER TABLE ownership_claims ADD COLUMN IF NOT EXISTS owner_token_hash TEXT")
            cur.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS tagline TEXT")
            cur.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS profile_tier TEXT NOT NULL DEFAULT 'standard'")
            cur.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS profile_badge TEXT")
            cur.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS profile_accent TEXT")
            cur.execute("ALTER TABLE official_sites ADD COLUMN IF NOT EXISTS owner_verification TEXT NOT NULL DEFAULT 'unverified'")
            cur.execute("ALTER TABLE official_sites ADD COLUMN IF NOT EXISTS ownership_verified_at TIMESTAMPTZ")
            cur.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT")
            cur.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT")
            cur.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS billing_status TEXT NOT NULL DEFAULT 'inactive'")
            cur.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS billing_period_end TIMESTAMPTZ")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_official_sites_domain ON official_sites(domain)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_site_checks_site_time ON site_checks(site_id, checked_at DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ownership_claims_domain_time ON ownership_claims(domain, requested_at DESC)")
        conn.commit()
    return True


def _slug(name):
    value = "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-")
    return value or "organization"


def seed_registry(registry):
    if not enabled():
        return False
    ensure_schema()
    with _connect() as conn:
        with conn.cursor() as cur:
            for domain, item in registry.items():
                name = item["organization"]
                slug = _slug(name)
                links = json.dumps(item.get("links") or {}, ensure_ascii=False)
                cur.execute("""
                    INSERT INTO organizations
                        (name, slug, category, description, logo_url, links, tagline,
                         profile_tier, profile_badge, profile_accent, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,NOW())
                    ON CONFLICT (slug) DO UPDATE SET
                        name=EXCLUDED.name,
                        category=CASE WHEN organizations.profile_tier='premium' THEN organizations.category ELSE EXCLUDED.category END,
                        description=CASE WHEN organizations.profile_tier='premium' THEN organizations.description ELSE EXCLUDED.description END,
                        logo_url=CASE WHEN organizations.profile_tier='premium' THEN organizations.logo_url ELSE EXCLUDED.logo_url END,
                        links=CASE WHEN organizations.profile_tier='premium' THEN organizations.links ELSE EXCLUDED.links END,
                        tagline=CASE WHEN organizations.profile_tier='premium' THEN organizations.tagline ELSE EXCLUDED.tagline END,
                        profile_tier=CASE WHEN organizations.profile_tier='premium' THEN organizations.profile_tier ELSE EXCLUDED.profile_tier END,
                        profile_badge=CASE WHEN organizations.profile_tier='premium' THEN organizations.profile_badge ELSE EXCLUDED.profile_badge END,
                        profile_accent=CASE WHEN organizations.profile_tier='premium' THEN organizations.profile_accent ELSE EXCLUDED.profile_accent END,
                        updated_at=NOW()
                    RETURNING id
                """, (
                    name, slug, item.get("category"), item.get("description"),
                    item.get("logo_url"), links, item.get("tagline"),
                    item.get("profile_tier", "standard"), item.get("profile_badge"),
                    item.get("profile_accent")
                ))
                org_id = cur.fetchone()["id"]
                cur.execute("""
                    INSERT INTO official_sites
                        (organization_id, domain, url, confirmation_level, source, source_url, notes, updated_at)
                    VALUES (%s,%s,%s,'NOVA','NOVA curated registry',%s,%s,NOW())
                    ON CONFLICT (domain) DO UPDATE SET
                        organization_id=EXCLUDED.organization_id,
                        url=EXCLUDED.url,
                        confirmation_level=EXCLUDED.confirmation_level,
                        source=EXCLUDED.source,
                        source_url=EXCLUDED.source_url,
                        notes=EXCLUDED.notes,
                        updated_at=NOW()
                """, (
                    org_id, domain, "https://" + domain,
                    item.get("source_url"), item.get("notes")
                ))
        conn.commit()
    return True


def normalize_domain(value):
    raw = value if "://" in str(value) else "https://" + str(value)
    return (urlsplit(raw).hostname or "").lower().strip().rstrip(".").removeprefix("www.")


def get_site(domain):
    host = normalize_domain(domain)
    if not enabled():
        return None
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.*, o.name AS organization, o.category, o.description,
                       o.logo_url, o.links, o.tagline, o.profile_tier,
                       o.profile_badge, o.profile_accent, o.stripe_customer_id,
                       o.stripe_subscription_id, o.billing_status, o.billing_period_end
                FROM official_sites s
                JOIN organizations o ON o.id=s.organization_id
                WHERE s.domain=%s AND s.registry_status='active'
                LIMIT 1
            """, (host,))
            row = cur.fetchone()
            if not row:
                return None
            cur.execute("""
                SELECT checked_at, technical_status, officiality_status, officiality_method,
                       http_status, dns_resolved, https, final_domain, verification_id, evidence
                FROM site_checks
                WHERE site_id=%s
                ORDER BY checked_at DESC
                LIMIT 1
            """, (row["id"],))
            row["last_check"] = cur.fetchone()
            return row


def save_check(domain, verification):
    if not enabled():
        return False
    site = get_site(domain)
    if not site:
        return False
    technical = verification.get("technical") or {}
    officiality = verification.get("officiality") or {}
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO site_checks
                    (site_id, checked_at, technical_status, officiality_status, officiality_method,
                     http_status, dns_resolved, https, final_domain, verification_id, evidence)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
            """, (
                site["id"], verification.get("checked_at") or datetime.now(timezone.utc),
                verification.get("status"), officiality.get("status"), officiality.get("method"),
                technical.get("http_status"), technical.get("dns_resolved"),
                technical.get("final_https", technical.get("https")), technical.get("final_host"),
                verification.get("verification_id"),
                json.dumps(officiality.get("evidence") or [], ensure_ascii=False),
            ))
        conn.commit()
    return True


def create_ownership_claim(domain, challenge_hash, expires_at, owner_token_hash):
    host = normalize_domain(domain)
    if not enabled() or not host:
        return None
    ensure_schema()
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ownership_claims (domain, challenge_hash, expires_at, owner_token_hash)
                VALUES (%s,%s,%s,%s)
                RETURNING id, domain, proof_method, status, requested_at, expires_at
            """, (host, challenge_hash, expires_at, owner_token_hash))
            row = cur.fetchone()
        conn.commit()
    return row


def get_ownership_claim(domain, challenge_hash=None):
    host = normalize_domain(domain)
    if not enabled() or not host:
        return None
    with _connect() as conn:
        with conn.cursor() as cur:
            if challenge_hash:
                cur.execute("""
                    SELECT id, domain, proof_method, status, requested_at, expires_at, verified_at, owner_token_hash
                    FROM ownership_claims
                    WHERE domain=%s AND challenge_hash=%s
                    ORDER BY requested_at DESC
                    LIMIT 1
                """, (host, challenge_hash))
            else:
                cur.execute("""
                    SELECT id, domain, proof_method, status, requested_at, expires_at, verified_at, owner_token_hash
                    FROM ownership_claims
                    WHERE domain=%s
                    ORDER BY requested_at DESC
                    LIMIT 1
                """, (host,))
            return cur.fetchone()


def owner_token_authorized(domain, owner_token_hash):
    host = normalize_domain(domain)
    if not enabled() or not host:
        return False
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1 FROM ownership_claims
                WHERE domain=%s AND owner_token_hash=%s
                  AND status='verified' AND expires_at>NOW()
                LIMIT 1
            """, (host, owner_token_hash))
            return cur.fetchone() is not None


def mark_ownership_verified(domain, challenge_hash):
    host = normalize_domain(domain)
    if not enabled() or not host:
        return None
    now = datetime.now(timezone.utc)
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE ownership_claims
                SET status='verified', verified_at=%s
                WHERE id=(
                    SELECT id FROM ownership_claims
                    WHERE domain=%s AND challenge_hash=%s
                      AND status='pending' AND expires_at>%s
                    ORDER BY requested_at DESC
                    LIMIT 1
                )
                RETURNING id, domain, proof_method, status, requested_at, expires_at, verified_at
            """, (now, host, challenge_hash, now))
            claim = cur.fetchone()
            if claim:
                cur.execute("""
                    UPDATE official_sites
                    SET owner_verification='DOMAIN_CONTROL',
                        ownership_verified_at=%s,
                        updated_at=NOW()
                    WHERE domain=%s
                """, (now, host))
        conn.commit()
    return claim


def get_claim_status(domain):
    host = normalize_domain(domain)
    if not enabled() or not host:
        return {"domain": host, "status": "unavailable"}
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, domain, proof_method, status, requested_at, expires_at, verified_at
                FROM ownership_claims
                WHERE domain=%s AND status='verified'
                ORDER BY verified_at DESC
                LIMIT 1
            """, (host,))
            verified = cur.fetchone()
            if verified:
                return verified
            cur.execute("""
                SELECT id, domain, proof_method, status, requested_at, expires_at, verified_at
                FROM ownership_claims
                WHERE domain=%s
                ORDER BY requested_at DESC
                LIMIT 1
            """, (host,))
            pending = cur.fetchone()
            return pending or {"domain": host, "status": "not_started"}


def get_stats():
    if not enabled():
        return {
            "enabled": False,
            "organizations": 0,
            "official_sites": 0,
            "checks": 0,
            "owner_verified": 0,
        }
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM organizations")
            organizations = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM official_sites WHERE registry_status='active'")
            sites = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM site_checks")
            checks = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM official_sites WHERE owner_verification='DOMAIN_CONTROL'")
            owner_verified = cur.fetchone()["n"]
    return {
        "enabled": True,
        "organizations": organizations,
        "official_sites": sites,
        "checks": checks,
        "owner_verified": owner_verified,
    }


def get_billing_profile(domain):
    host = normalize_domain(domain)
    if not enabled() or not host:
        return None
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT o.id AS organization_id, o.name, o.profile_tier, o.stripe_customer_id,
                       o.stripe_subscription_id, o.billing_status, o.billing_period_end,
                       s.domain, s.owner_verification
                FROM official_sites s
                JOIN organizations o ON o.id=s.organization_id
                WHERE s.domain=%s AND s.registry_status='active'
                LIMIT 1
            """, (host,))
            return cur.fetchone()


def set_billing_state(domain, *, customer_id=None, subscription_id=None, status=None, period_end=None):
    host = normalize_domain(domain)
    if not enabled() or not host:
        return None
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE organizations o
                SET stripe_customer_id=COALESCE(%s, o.stripe_customer_id),
                    stripe_subscription_id=COALESCE(%s, o.stripe_subscription_id),
                    billing_status=COALESCE(%s, o.billing_status),
                    billing_period_end=COALESCE(%s, o.billing_period_end),
                    profile_tier=CASE
                        WHEN COALESCE(%s, o.billing_status) IN ('active','trialing') THEN 'premium'
                        WHEN COALESCE(%s, o.billing_status) IN ('canceled','unpaid','incomplete_expired') THEN 'standard'
                        ELSE o.profile_tier
                    END,
                    updated_at=NOW()
                FROM official_sites s
                WHERE s.organization_id=o.id AND s.domain=%s
                RETURNING o.id, o.name, o.profile_tier, o.stripe_customer_id,
                          o.stripe_subscription_id, o.billing_status, o.billing_period_end
            """, (
                customer_id, subscription_id, status, period_end,
                status, status, host
            ))
            row = cur.fetchone()
        conn.commit()
    return row


def find_domain_by_subscription(subscription_id):
    if not enabled() or not subscription_id:
        return None
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.domain
                FROM organizations o
                JOIN official_sites s ON s.organization_id=o.id
                WHERE o.stripe_subscription_id=%s
                LIMIT 1
            """, (subscription_id,))
            row = cur.fetchone()
            return row["domain"] if row else None


def find_domain_by_customer(customer_id):
    if not enabled() or not customer_id:
        return None
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.domain
                FROM organizations o
                JOIN official_sites s ON s.organization_id=o.id
                WHERE o.stripe_customer_id=%s
                LIMIT 1
            """, (customer_id,))
            row = cur.fetchone()
            return row["domain"] if row else None
