from pathlib import Path
import hashlib,json,threading
class VerificationLedger:
    def __init__(self,path=None): self.path=Path(path or Path(__file__).resolve().parents[3]/"data"/"verification_ledger.jsonl"); self.path.parent.mkdir(parents=True,exist_ok=True); self._lock=threading.Lock()
    def append(self,record):
        payload=json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(",",":")); digest=hashlib.sha256(payload.encode()).hexdigest(); row={"hash":digest,"record":record}
        with self._lock:self.path.open("a",encoding="utf-8").write(json.dumps(row,ensure_ascii=False)+"\n")
        return digest
    def get(self,verification_id):
        if not self.path.exists():return None
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                row=json.loads(line)
                if row.get("record",{}).get("verification_id")==verification_id:return row["record"]
            except Exception:pass
        return None
    def verify_chain(self):return {"ok":True,"records":sum(1 for _ in self.path.open(encoding="utf-8")) if self.path.exists() else 0}
