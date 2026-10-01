from concurrent.futures import ThreadPoolExecutor

import pytest

from app.verification.ledger import VerificationLedger


def test_separate_ledger_instances_preserve_chain_during_parallel_reads_and_writes(tmp_path):
    path = tmp_path / "ledger.jsonl"
    ledgers = [VerificationLedger(path), VerificationLedger(path)]

    def append_and_check(index):
        ledgers[index % 2].append({"index": index})
        assert ledgers[(index + 1) % 2].verify_chain()["ok"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(append_and_check, range(64)))
    health = ledgers[0].verify_chain()
    assert health["ok"]
    assert health["records"] == 64


@pytest.mark.parametrize("invalid", ["{broken", "[]", "null"])
def test_damaged_ledger_reports_failed_health_without_crashing(tmp_path, invalid):
    ledger = VerificationLedger(tmp_path / "ledger.jsonl")
    ledger.append({"index": 0})
    with ledger.path.open("a", encoding="utf-8") as file:
        file.write(invalid + "\n")
    assert ledger.verify_chain() == {"ok": False, "records": 1, "error": "invalid record"}
