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
                CREATE INDEX IF NOT EXISTS idx_official_sites_domain ON official_sites(domain);
                CREATE INDEX IF NOT EXISTS idx_site_checks_site_time ON site_checks(site_id, checked_at DESC);
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
                    INSERT INTO organizations (name, slug, category, description, updated_at)
                    VALUES (%s,%s,%s,%s,NOW())
                    ON CONFLICT (slug) DO UPDATE SET
                        name=EXCLUDED.name, category=EXCLUDED.category, updated_at=NOW()
                    RETURNING id
                """, (name, slug, item.get("category"), item.get("description")))
                org_id = cur.fetchone()["id"]
                cur.execute("""
                    INSERT INTO official_sites
                        (organization_id, domain, url, confirmation_level, source, source_url, notes, updated_at)
                    VALUES (%s,%s,%s,'NOVA','NOVA curated registry',%s,%s,NOW())
                    ON CONFLICT (domain) DO UPDATE SET
                        organization_id=EXCLUDED.organization_id, url=EXCLUDED.url,
                        confirmation_level=EXCLUDED.confirmation_level, source=EXCLUDED.source,
                        source_url=EXCLUDED.source_url, notes=EXCLUDED.notes, updated_at=NOW()
                """, (org_id, domain, "https://" + domain, item.get("source_url"), item.get("notes")))
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
                       o.logo_url, o.links
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

def get_stats():
    if not enabled():
        return {"enabled": False, "organizations": 0, "official_sites": 0, "checks": 0}
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM organizations")
            organizations = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM official_sites WHERE registry_status='active'")
            sites = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM site_checks")
            checks = cur.fetchone()["n"]
    return {"enabled": True, "organizations": organizations, "official_sites": sites, "checks": checks}
