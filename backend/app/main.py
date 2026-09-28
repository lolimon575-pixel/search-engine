from pathlib import Path
from urllib.parse import urlsplit
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.websearch.service import WebSearchService
from app.verification.ledger import VerificationLedger
from app.verification.officiality import get_organization_profile, find_entity_profile
from app.registry_catalog import REGISTRY
from app.registry_db import ensure_schema, seed_registry, get_stats, get_site, create_claim, get_claim
from app.websearch.correction import suggest_correction
from app.websearch.query_features import resolve_bang
from app.company_claims import challenge_url, expected_value, verify_claim_challenge

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend" / "index.html"
app = FastAPI(title="NOVA Search", version="1.8.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET","POST"], allow_headers=["*"])
web_search = WebSearchService()
ledger = VerificationLedger()

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
        "status":"ok",
        "service":"nova-search",
        "version":app.version,
        "frontend":FRONTEND.is_file(),
        "provider":"duckduckgo-html",
        "verification":True,
        "ledger":ledger.verify_chain(),
        "registry":get_stats(),
    }

@app.get("/api/search")
async def search(
    q: str = Query("", max_length=300),
    limit: int = Query(10, ge=1, le=30),
    mode: str = Query("web", pattern="^(web|official|discussions)$"),
):
    query=q.strip()
    if not query:
        return {"query":q,"count":0,"results":[],"errors":[],"mode":mode}

    bang_url = resolve_bang(query)
    if bang_url:
        return {
            "query": query,
            "count": 0,
            "results": [],
            "errors": [],
            "mode": mode,
            "bang_url": bang_url,
        }

    corrected = suggest_correction(query)
    search_query = corrected or query
    results,errors=web_search.search(search_query,limit,mode=mode)
    entity = find_entity_profile(search_query)
    return {
        "query":query,
        "corrected_query":corrected,
        "searched_query":search_query,
        "count":len(results),
        "results":[r.model_dump() for r in results],
        "errors":errors,
        "mode":mode,
        "entity":entity,
    }

@app.get("/api/verification")
async def verification(url: str = Query(..., min_length=8, max_length=2048)):
    return web_search.verifier.verify(url)

@app.get("/api/verification/ledger/health")
async def ledger_health():
    return ledger.verify_chain()

@app.get("/api/registry/site")
async def registry_site(domain: str = Query("", max_length=253)):
    raw=domain if "://" in domain else "https://"+domain
    host=(urlsplit(raw).hostname or "").lower().strip().rstrip(".")
    row=get_site(host)
    if not row:
        return {"found":False,"domain":host}
    return {"found":True,"site":row}

@app.get("/api/registry/stats")
async def registry_stats():
    return get_stats()

@app.get("/api/organization")
async def organization_profile(domain: str = Query("", max_length=253)):
    raw=domain if "://" in domain else "https://"+domain
    host=(urlsplit(raw).hostname or "").lower().strip().rstrip(".")
    profile=get_organization_profile(host)
    return {"found":bool(profile),"domain":host,"profile":profile}


@app.get("/api/entity")
async def entity(q: str = Query("", max_length=253)):
    profile = find_entity_profile(q)
    return {"found": bool(profile), "profile": profile}

@app.post("/api/company/claim/start")
async def company_claim_start(
    domain: str = Query(..., min_length=3, max_length=253),
    organization: str = Query("", max_length=160),
    plan: str = Query("standard", pattern="^(standard|profile_plus)$"),
):
    claim = create_claim(domain, organization, plan)
    if not claim:
        raise HTTPException(status_code=400, detail="Не удалось создать challenge для домена.")
    return {
        "claim_id": claim["id"],
        "domain": claim["domain"],
        "status": claim["status"],
        "challenge_method": claim["challenge_method"],
        "challenge_url": challenge_url(claim["domain"]),
        "challenge_value": expected_value(claim["challenge_token"]),
        "requested_plan": claim["requested_plan"],
        "ranking_policy": "Оплата и тариф карточки не влияют на NOVA Rank.",
    }

@app.post("/api/company/claim/verify")
async def company_claim_verify(claim_id: int = Query(..., ge=1)):
    result = verify_claim_challenge(claim_id)
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Claim не найден.")
    return result

@app.get("/api/company/claim/status")
async def company_claim_status(claim_id: int = Query(..., ge=1)):
    claim = get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim не найден.")
    return {
        "claim_id": claim["id"],
        "domain": claim["domain"],
        "status": claim["status"],
        "payment_status": claim["payment_status"],
        "requested_plan": claim["requested_plan"],
        "verified_at": claim["verified_at"],
    }
