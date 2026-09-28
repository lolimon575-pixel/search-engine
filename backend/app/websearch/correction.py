import httpx

def _distance(a,b):
    if a==b:return 0
    if not a or not b:return max(len(a),len(b))
    prev=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        cur=[i]
        for j,cb in enumerate(b,1):
            cur.append(min(cur[-1]+1,prev[j]+1,prev[j-1]+(ca!=cb)))
        prev=cur
    return prev[-1]

def _plausible(original,candidate):
    a=original.lower().strip(); b=candidate.lower().strip()
    if not b or a==b or len(a)>80 or len(b)>80:return False
    return _distance(a,b)<=max(2,round(len(a)*0.22))

def suggest_correction(query, timeout=2.0):
    q=query.strip()
    if len(q)<3 or len(q)>120:return None
    try:
        with httpx.Client(timeout=timeout,follow_redirects=True,headers={"User-Agent":"NOVA-Search/1.6"}) as c:
            r=c.get("https://duckduckgo.com/ac/",params={"q":q,"kl":"ru-ru","type":"list"})
            r.raise_for_status()
            items=r.json()
        for item in items[:8]:
            candidate=str(item.get("phrase","")).strip() if isinstance(item,dict) else ""
            if _plausible(q,candidate):
                return candidate
    except Exception:
        pass
    return None
