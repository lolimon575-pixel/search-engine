from pathlib import Path
import asyncio
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.ownership import create_challenge, ownership_status, verify_challenge
from app.billing import billing_status, create_checkout, create_portal, handle_webhook
from app.profile_settings import ProfileSettingsRequest, save_profile_settings
from app.registry_db import ensure_schema, get_site, get_stats, seed_registry
from app.verification.ledger import VerificationLedger
from app.verification.officiality import REGISTRY, get_organization_profile
from app.websearch.brief import build_brief
from app.websearch.service import WebSearchService


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend" / "index.html"
app = FastAPI(title="NOVA Search", version="1.14.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
web_search = WebSearchService()
get_suggestions = web_search.index.suggest
ledger = VerificationLedger()


class OwnershipChallengeRequest(BaseModel):
    domain: str


class OwnershipVerifyRequest(BaseModel):
    domain: str
    token: str


class BillingActionRequest(BaseModel):
    domain: str
    ownership_token: str


@app.on_event("startup")
def init_registry():
    try:
        if ensure_schema():
            seed_registry(REGISTRY)
    except Exception as exc:
        print("NOVA registry init:", type(exc).__name__, str(exc))
    web_search.warm_index()


@app.get("/", include_in_schema=False)
async def home():
    return FileResponse(FRONTEND) if FRONTEND.is_file() else {"error": "frontend/index.html not found"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "nova-search",
        "version": app.version,
        "frontend": FRONTEND.is_file(),
        "provider": "nova-index+duckduckgo-html",
        "index": web_search.index.stats(),
        "verification": True,
        "ledger": ledger.verify_chain(),
        "registry": get_stats(),
    }


@app.get("/api/search")
def search(
    q: str = Query("", max_length=300),
    limit: int = Query(10, ge=1, le=30),
    mode: str = Query("web", pattern="^(web|verified|exact|discussions)$"),
    freshness: str = Query("", pattern="^(|d|w|m|y)$"),
    autocorrect: bool = Query(True),
    engine: str = Query("auto", pattern="^(auto|index|web)$"),
):
    query = q.strip()
    if not query:
        return {
            "query": q,
            "mode": mode,
            "freshness": freshness,
            "engine": engine,
            "count": 0,
            "results": [],
            "errors": [],
        }
    batch = web_search.search(query, limit, mode=mode, freshness=freshness, engine=engine, autocorrect=autocorrect)
    results, errors = batch
    corrected = getattr(batch, "corrected_query", None)
    search_query = getattr(batch, "searched_query", query)
    search_pending = getattr(batch, "search_pending", False)
    if not results and errors and not search_pending:
        raise HTTPException(status_code=503, detail="Поиск временно недоступен. Попробуйте ещё раз.")
    brief = build_brief(search_query, results)
    return {
        "query": query,
        "corrected_query": corrected,
        "searched_query": search_query,
        "mode": mode,
        "freshness": freshness,
        "engine": engine,
        "source": getattr(batch, "source", "web"),
        "search_pending": search_pending,
        "verification_pending": getattr(batch, "verification_pending", False),
        "server_time_ms": getattr(batch, "elapsed_ms", None),
        "index": web_search.index.stats(),
        "count": len(results),
        "results": [r.model_dump() for r in results],
        "brief": brief,
        "errors": errors,
    }


@app.get("/api/suggest")
def suggest(q: str = Query("", max_length=120), limit: int = Query(6, ge=1, le=10)):
    return {"query": q, "suggestions": get_suggestions(q, limit=limit)}


@app.get("/api/index/stats")
def index_stats():
    return web_search.index.stats()


@app.get("/api/verification")
def verification(url: str = Query(..., min_length=8, max_length=2048)):
    try:
        return web_search.verifier.verify(url)
    except ValueError:
        raise HTTPException(status_code=400, detail="Укажите корректный адрес сайта.")


@app.get("/api/verification/ledger/health")
def ledger_health():
    return ledger.verify_chain()


def domain_host(domain):
    raw = domain if "://" in domain else "https://" + domain
    try:
        return (urlsplit(raw).hostname or "").lower().strip().rstrip(".")
    except ValueError:
        raise HTTPException(status_code=400, detail="Укажите корректный домен.")


@app.get("/api/registry/site")
def registry_site(domain: str = Query("", max_length=253)):
    host = domain_host(domain)
    row = get_site(host)
    if not row:
        return {"found": False, "domain": host}
    public_fields = (
        "id", "organization_id", "organization", "domain", "url", "category", "description",
        "logo_url", "links", "tagline", "registry_status", "confirmation_level", "source", "source_url",
        "created_at", "updated_at", "last_check", "owner_verification", "ownership_verified_at",
        "profile_tier", "profile_badge", "profile_accent", "billing_status", "billing_period_end",
    )
    return {"found": True, "site": {key: row[key] for key in public_fields if key in row}}


@app.get("/api/registry/stats")
def registry_stats():
    return get_stats()


@app.get("/api/organization")
def organization_profile(domain: str = Query("", max_length=253)):
    host = domain_host(domain)
    profile = get_organization_profile(host)
    return {"found": bool(profile), "domain": host, "profile": profile}


@app.post("/api/organization/profile")
async def organization_update(body: ProfileSettingsRequest):
    try:
        return await asyncio.to_thread(save_profile_settings, body)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=503, detail="Не удалось сохранить карточку. Попробуйте позже.")


@app.post("/api/ownership/challenge")
def ownership_challenge(body: OwnershipChallengeRequest):
    try:
        return create_challenge(body.domain)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Ownership challenge unavailable: {type(exc).__name__}")


@app.post("/api/ownership/verify")
def ownership_verify(body: OwnershipVerifyRequest):
    try:
        return verify_challenge(body.domain, body.token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Ownership verification unavailable: {type(exc).__name__}")


@app.get("/api/ownership/status")
def ownership_get_status(domain: str = Query("", max_length=253)):
    return ownership_status(domain)


@app.get("/api/billing/status")
def profile_plus_status(domain: str = Query("", max_length=253)):
    return billing_status(domain)


@app.post("/api/billing/checkout")
async def profile_plus_checkout(body: BillingActionRequest):
    try:
        return create_checkout(body.domain, body.ownership_token)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/api/billing/portal")
async def profile_plus_portal(body: BillingActionRequest):
    try:
        return create_portal(body.domain, body.ownership_token)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/api/billing/webhook")
async def stripe_billing_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        return handle_webhook(payload, signature)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid webhook payload")
    except Exception as exc:
        if exc.__class__.__name__ == "SignatureVerificationError":
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
        raise HTTPException(status_code=503, detail=f"Billing webhook unavailable: {type(exc).__name__}")
