"""Optional persistence in the existing PostgreSQL registry, off the request path."""
from app.registry_db import _connect, enabled


def load_documents():
    if not enabled():
        return []
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""CREATE TABLE IF NOT EXISTS nova_index_documents (
            url TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
            seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
        cur.execute("SELECT url, title, description, EXTRACT(EPOCH FROM seen_at) AS seen_at FROM nova_index_documents WHERE seen_at > NOW() - INTERVAL '14 days' ORDER BY seen_at DESC LIMIT 5000")
        return cur.fetchall()


def save_documents(documents):
    if not documents or not enabled():
        return
    with _connect() as conn, conn.cursor() as cur:
        cur.executemany("""INSERT INTO nova_index_documents (url, title, description) VALUES (%s, %s, %s)
            ON CONFLICT (url) DO UPDATE SET title=EXCLUDED.title, description=EXCLUDED.description, seen_at=NOW()""",
            [(d["url"], d["title"], d["description"]) for d in documents])
        cur.execute("DELETE FROM nova_index_documents WHERE seen_at < NOW() - INTERVAL '14 days' OR url IN (SELECT url FROM nova_index_documents ORDER BY seen_at DESC OFFSET 5000)")
