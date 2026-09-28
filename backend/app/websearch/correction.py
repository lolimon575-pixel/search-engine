import re
import httpx

def _distance(a,b):
    prev=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        cur=[i]
        for j,cb in enumerate(b,1):
            cur.append(min(cur[-1]+1,prev[j]+1,prev[j-1]+(ca!=cb)))
        prev=cur
    return prev[-1]

def _plausible(original,candidate):
    a=re.sub(r"\s+"," ",original.lower().strip())
    b=re.sub(r"\s+"," ",candidate.lower().strip())
    if not b or a==b or len(a)>100 or len(b)>100:return False
    return _distance(a,b)<=max(1,round(min(len(a),len(b))*.2))

def _suggestions(q):
    endpoints=[
        ("https://suggestqueries.google.com/complete/search",{"client":"firefox","hl":"ru","q":q}),
        ("https://duckduckgo.com/ac/",{"q":q,"kl":"ru-ru","type":"list"}),
    ]
    headers={"User-Agent":"Mozilla/5.0 (compatible; NOVA Search/1.6)"}
    with httpx.Client(timeout=2.5,follow_redirects=True,headers=headers) as client:
        for url,params in endpoints:
            try:
                data=client.get(url,params=params).json()
                if not isinstance(data,list): continue
                if len(data)>1 and isinstance(data[1],list):
                    for item in data[1][:10]:
                        if isinstance(item,str) and item.strip(): yield item.strip()
                else:
                    for item in data[:10]:
                        if isinstance(item,dict):
                            value=str(item.get("phrase","")).strip()
                            if value: yield value
            except Exception:
                continue

def suggest_correction(query, timeout=2.5):
    q=query.strip()
    if len(q)<3 or len(q)>120:return None
    seen=set()
    try:
        for candidate in _suggestions(q):
            key=candidate.lower()
            if key in seen: continue
            seen.add(key)
            if _plausible(q,candidate):
                return candidate
    except Exception:
        pass
    return None
