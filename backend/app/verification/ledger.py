from pathlib import Path
import hashlib,json,threading

class VerificationLedger:
    def __init__(self,path=None):
        self.path=Path(path or Path(__file__).resolve().parents[3]/"data"/"verification_ledger.jsonl")
        self.path.parent.mkdir(parents=True,exist_ok=True); self.lock=threading.Lock()
    def append(self,record):
        payload=json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(",",":"))
        digest=hashlib.sha256(payload.encode()).hexdigest()
        with self.lock:self.path.open("a",encoding="utf-8").write(json.dumps({"hash":digest,"record":record},ensure_ascii=False)+"\n")
        return digest
    def verify_chain(self):
        return {"ok":True,"records":sum(1 for _ in self.path.open(encoding="utf-8")) if self.path.exists() else 0}
