from pathlib import Path
from urllib.parse import urlsplit
from fastapi import FastAPI,Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.websearch.service import WebSearchService
from app.verification.ledger import VerificationLedger
from app.verification.officiality import get_organization_profile
ROOT=Path(__file__).resolve().parents[2]; FRONTEND=ROOT/"frontend"/"index.html"
app=FastAPI(title="NOVA Search",version="1.1.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=False,allow_methods=["GET"],allow_headers=["*"])
web_search=WebSearchService(); ledger=VerificationLedger()
@app.get("/",include_in_schema=False)
async def home():return FileResponse(FRONTEND) if FRONTEND.is_file() else {"error":"frontend/index.html not found"}
@app.get("/health")
async def health():return {"status":"ok","service":"nova-search","version":app.version,"frontend":FRONTEND.is_file(),"provider":"duckduckgo-html","verification":True,"ledger":ledger.verify_chain()}
@app.get("/api/search")
async def search(q:str=Query("",max_length=300),limit:int=Query(10,ge=1,le=30)):
    query=q.strip()
    if not query:return {"query":q,"count":0,"mode":"web","results":[],"errors":[]}
    results,errors=web_search.search(query,limit); return {"query":query,"count":len(results),"mode":"web","results":[r.model_dump() for r in results],"errors":errors}
@app.get("/api/verification/ledger/health")
async def ledger_health():return ledger.verify_chain()
@app.get("/api/organization")
async def organization_profile(domain:str=Query("",max_length=253)):
    host=(urlsplit(domain if "://" in domain else "https://"+domain).hostname or domain).lower().strip().rstrip("."); profile=get_organization_profile(host); return {"found":bool(profile),"domain":host,"profile":profile}
