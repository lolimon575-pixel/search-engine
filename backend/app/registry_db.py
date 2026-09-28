import os
import secrets
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
                    tagline TEXT,
                    description TEXT,
                    logo_url TEXT,
                    links JSONB NOT NULL DEFAULT '{}'::jsonb,
                    profile JSONB NOT NULL DEFAULT '{}'::jsonb,
                    profile_tier TEXT NOT NULL DEFAULT 'standard',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS official_sites (
                    id BIGSERIAL PRIMARY KEY,
                    organization_id BIGINT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                    domain TEXT NOT NULL UNIQUE,
                    url TEXT NOT NULL,
                    registry_status TEXT NOT NULL DEFAULT 'active',
                    confirmation_level TEXT NOT NULL DEFAULT 'CURATED',
                    ownership_status TEXT NOT NULL DEFAULT 'unclaimed',
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
                CREATE TABLE IF NOT EXISTS company_claims (
                    id BIGSERIAL PRIMARY KEY,
                    domain TEXT NOT NULL,
                    challenge_token TEXT NOT NULL UNIQUE,
                    challenge_method TEXT NOT NULL DEFAULT 'well-known-file',
                    status TEXT NOT NULL DEFAULT 'pending',
                    payment_status TEXT NOT NULL DEFAULT 'not_required',
                    requested_plan TEXT NOT NULL DEFAULT 'standard',
                    organization_name TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    verified_at TIMESTAMPTZ,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_official_sites_domain ON official_sites(domain);
                CREATE INDEX IF NOT EXISTS idx_site_checks_site_time ON site_checks(site_id, checked_at DESC);
                CREATE INDEX IF NOT EXISTS idx_company_claims_domain_time ON company_claims(domain, created_at DESC);

                ALTER TABLE organizations ADD COLUMN IF NOT EXISTS tagline TEXT;
                ALTER TABLE organizations ADD COLUMN IF NOT EXISTS profile JSONB NOT NULL DEFAULT '{}'::jsonb;
                ALTER TABLE organizations ADD COLUMN IF NOT EXISTS profile_tier TEXT NOT NULL DEFAULT 'standard';
                ALTER TABLE official_sites ADD COLUMN IF NOT EXISTS ownership_status TEXT NOT NULL DEFAULT 'unclaimed';
                ALTER TABLE official_sites ALTER COLUMN confirmation_level SET DEFAULT 'CURATED';
            """)
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
                cur.execute("""
                    INSERT INTO organizations
                        (name, slug, category, tagline, description, links, profile, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,NOW())
                    ON CONFLICT (slug) DO UPDATE SET
                        name=EXCLUDED.name,
                        category=EXCLUDED.category,
                        tagline=EXCLUDED.tagline,
                        description=EXCLUDED.description,
                        links=EXCLUDED.links,
                        updated_at=NOW()
                    RETURNING id
                """, (
                    name,
                    slug,
                    item.get("category"),
                    item.get("tagline"),
                    item.get("description"),
                    item.get("links") or {},
                    item.get("profile") or {},
                ))
                org_id = cur.fetchone()["id"]
                cur.execute("""
                    INSERT INTO official_sites
                        (organization_id, domain, url, confirmation_level, source, source_url, notes, updated_at)
                    VALUES (%s,%s,%s,'CURATED','NOVA curated registry',%s,%s,NOW())
                    ON CONFLICT (domain) DO UPDATE SET
                        organization_id=EXCLUDED.organization_id,
                        url=EXCLUDED.url,
                        source=EXCLUDED.source,
                        source_url=EXCLUDED.source_url,
                        notes=EXCLUDED.notes,
                        updated_at=NOW()
                """, (
                    org_id,
                    domain,
                    "https://" + domain,
                    item.get("source_url"),
                    item.get("notes"),
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
                SELECT s.*, o.name AS organization, o.category, o.tagline, o.description,
                       o.logo_url, o.links, o.profile, o.profile_tier
                FROM official_sites s JOIN organizations o ON o.id=s.organization_id
                WHERE s.domain=%s AND s.registry_status='active' LIMIT 1
            """, (host,))
            row = cur.fetchone()
            if not row:
                return None
            cur.execute("""
                SELECT checked_at, technical_status, officiality_status, officiality_method,
                       http_status, dns_resolved, https, final_domain, verification_id, evidence
                FROM site_checks WHERE site_id=%s ORDER BY checked_at DESC LIMIT 1
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
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                site["id"], verification.get("checked_at") or datetime.now(timezone.utc),
                verification.get("status"), officiality.get("status"), officiality.get("method"),
                technical.get("http_status"), technical.get("dns_resolved"),
                technical.get("final_https", technical.get("https")), technical.get("final_host"),
                verification.get("verification_id"), officiality.get("evidence") or []
            ))
        conn.commit()
    return True


def create_claim(domain, organization_name="", requested_plan="standard"):
    if not enabled():
        return None
    ensure_schema()
    host = normalize_domain(domain)
    if not host or "." not in host:
        return None
    token = secrets.token_urlsafe(24)
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO company_claims
                    (domain, challenge_token, organization_name, requested_plan)
                VALUES (%s,%s,%s,%s)
                RETURNING id, domain, challenge_token, challenge_method, status,
                          payment_status, requested_plan, organization_name, created_at
            """, (host, token, organization_name.strip() or None, requested_plan))
            row = cur.fetchone()
        conn.commit()
    return row


def get_claim(claim_id):
    if not enabled():
        return None
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM company_claims WHERE id=%s LIMIT 1", (claim_id,))
            return cur.fetchone()


def mark_claim_verified(claim_id):
    if not enabled():
        return None
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE company_claims
                SET status='verified', verified_at=NOW(), updated_at=NOW()
                WHERE id=%s AND status<>'verified'
                RETURNING *
            """, (claim_id,))
            claim = cur.fetchone()
            if not claim:
                cur.execute("SELECT * FROM company_claims WHERE id=%s LIMIT 1", (claim_id,))
                claim = cur.fetchone()
            if claim:
                cur.execute("""
                    SELECT id FROM official_sites WHERE domain=%s LIMIT 1
                """, (claim["domain"],))
                site = cur.fetchone()
                if not site:
                    name = claim["domain"]
                    slug = _slug(name)
                    cur.execute("""
                        INSERT INTO organizations
                            (name, slug, category, tagline, description, updated_at)
                        VALUES (%s,%s,'Company','Owner verified domain',
                                'Профиль создан после подтверждения контроля домена владельцем.',NOW())
                        ON CONFLICT (slug) DO UPDATE SET updated_at=NOW()
                        RETURNING id
                    """, (name, slug))
                    org_id = cur.fetchone()["id"]
                    cur.execute("""
                        INSERT INTO official_sites
                            (organization_id, domain, url, confirmation_level, ownership_status,
                             source, notes, updated_at)
                        VALUES (%s,%s,%s,'OWNER_VERIFIED','owner_verified',
                                'Owner domain-control verification',
                                'Created automatically after successful ownership challenge.',NOW())
                        ON CONFLICT (domain) DO NOTHING
                    """, (org_id, claim["domain"], "https://" + claim["domain"]))
                cur.execute("""
                    UPDATE official_sites
                    SET ownership_status='owner_verified',
                        confirmation_level='OWNER_VERIFIED',
                        updated_at=NOW()
                    WHERE domain=%s
                """, (claim["domain"],))
        conn.commit()
    return claim


def get_latest_verified_claim(domain):
    if not enabled():
        return None
    host = normalize_domain(domain)
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM company_claims
                WHERE domain=%s AND status='verified'
                ORDER BY verified_at DESC NULLS LAST, created_at DESC
                LIMIT 1
            """, (host,))
            return cur.fetchone()


def get_stats():
    if not enabled():
        return {"enabled": False, "organizations": 0, "official_sites": 0, "checks": 0, "owner_verified": 0}
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM organizations")
            organizations = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM official_sites WHERE registry_status='active'")
            sites = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM site_checks")
            checks = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM official_sites WHERE ownership_status='owner_verified'")
            owner_verified = cur.fetchone()["n"]
    return {
        "enabled": True,
        "organizations": organizations,
        "official_sites": sites,
        "checks": checks,
        "owner_verified": owner_verified,
    }
