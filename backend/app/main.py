from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.ownership import create_challenge, ownership_status, verify_challenge
from app.registry_db import ensure_schema, get_site, get_stats, seed_registry
from app.verification.ledger import VerificationLedger
from app.verification.officiality import REGISTRY, get_organization_profile
from app.websearch.correction import get_suggestions, suggest_correction
from app.websearch.brief import build_brief
from app.websearch.service import WebSearchService


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend" / "index.html"
app = FastAPI(title="NOVA Search", version="1.8.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
web_search = WebSearchService()
ledger = VerificationLedger()


class OwnershipChallengeRequest(BaseModel):
    domain: str


class OwnershipVerifyRequest(BaseModel):
    domain: str
    token: str


@app.on_event("startup")
def init_registry():
    try:
        if ensure_schema():
            seed_registry(REGISTRY)
    except Exception as exc:
        print("NOVA registry init:", type(exc).__name__, str(exc))


@app.get("/", include_in_schema=False)
async def home():
    return FileResponse(FRONTEND) if FRONTEND.is_file() else {"error": "frontend/index.html not found"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "nova-search",
        "version": app.version,
        "frontend": FRONTEND.is_file(),
        "provider": "duckduckgo-html",
        "verification": True,
        "ledger": ledger.verify_chain(),
        "registry": get_stats(),
    }


@app.get("/api/search")
async def search(
    q: str = Query("", max_length=300),
    limit: int = Query(10, ge=1, le=30),
    mode: str = Query("web", pattern="^(web|verified|exact|discussions)$"),
    freshness: str = Query("", pattern="^(|d|w|m|y)$"),
):
    query = q.strip()
    if not query:
        return {
            "query": q,
            "mode": mode,
            "freshness": freshness,
            "count": 0,
            "results": [],
            "errors": [],
        }
    corrected = None if mode == "exact" else suggest_correction(query)
    search_query = corrected or query
    results, errors = web_search.search(search_query, limit, mode=mode, freshness=freshness)
    brief = build_brief(search_query, results)
    return {
        "query": query,
        "corrected_query": corrected,
        "searched_query": search_query,
        "mode": mode,
        "freshness": freshness,
        "count": len(results),
        "results": [r.model_dump() for r in results],
        "brief": brief,
        "errors": errors,
    }


@app.get("/api/suggest")
async def suggest(q: str = Query("", max_length=120), limit: int = Query(6, ge=1, le=10)):
    return {"query": q, "suggestions": get_suggestions(q, limit=limit)}


@app.get("/api/verification")
async def verification(url: str = Query(..., min_length=8, max_length=2048)):
    return web_search.verifier.verify(url)


@app.get("/api/verification/ledger/health")
async def ledger_health():
    return ledger.verify_chain()


@app.get("/api/registry/site")
async def registry_site(domain: str = Query("", max_length=253)):
    raw = domain if "://" in domain else "https://" + domain
    host = (urlsplit(raw).hostname or "").lower().strip().rstrip(".")
    row = get_site(host)
    if not row:
        return {"found": False, "domain": host}
    return {"found": True, "site": row}


@app.get("/api/registry/stats")
async def registry_stats():
    return get_stats()


@app.get("/api/organization")
async def organization_profile(domain: str = Query("", max_length=253)):
    raw = domain if "://" in domain else "https://" + domain
    host = (urlsplit(raw).hostname or "").lower().strip().rstrip(".")
    profile = get_organization_profile(host)
    return {"found": bool(profile), "domain": host, "profile": profile}


@app.post("/api/ownership/challenge")
async def ownership_challenge(body: OwnershipChallengeRequest):
    try:
        return create_challenge(body.domain)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Ownership challenge unavailable: {type(exc).__name__}")


@app.post("/api/ownership/verify")
async def ownership_verify(body: OwnershipVerifyRequest):
    try:
        return verify_challenge(body.domain, body.token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Ownership verification unavailable: {type(exc).__name__}")


@app.get("/api/ownership/status")
async def ownership_get_status(domain: str = Query("", max_length=253)):
    return ownership_status(domain)
