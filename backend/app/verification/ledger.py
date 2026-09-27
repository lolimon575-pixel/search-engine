from pathlib import Path
import hashlib
import json
import threading


class VerificationLedger:
    def __init__(self, path=None):
        self.path = Path(path or Path(__file__).resolve().parents[3] / "data" / "verification_ledger.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def append(self, record):
        with self.lock:
            previous = ""
            if self.path.exists():
                lines = self.path.read_text(encoding="utf-8").splitlines()
                if lines:
                    try:
                        previous = json.loads(lines[-1]).get("hash", "")
                    except Exception:
                        previous = ""

            envelope = {
                "previous_hash": previous,
                "record": record,
            }
            payload = json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "hash": digest,
                    "previous_hash": previous,
                    "record": record,
                }, ensure_ascii=False) + "\n")
            return digest

    def verify_chain(self):
        if not self.path.exists():
            return {"ok": True, "records": 0}

        previous = ""
        records = 0
        with self.path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                record = item.get("record", {})
                prev = item.get("previous_hash", "")
                if prev != previous:
                    return {"ok": False, "records": records, "error": "previous_hash mismatch"}
                envelope = {"previous_hash": prev, "record": record}
                payload = json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
                if item.get("hash") != expected:
                    return {"ok": False, "records": records, "error": "hash mismatch"}
                previous = item["hash"]
                records += 1
        return {"ok": True, "records": records, "last_hash": previous}
