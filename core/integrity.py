import hashlib
import json
from storage.ledger import _load


def verify_ledger_integrity():
    ledger = _load()

    prev_hash = "GENESIS"

    for entry in ledger:
        stored_hash = entry.get("hash")
        entry_copy = dict(entry)
        entry_copy.pop("hash", None)

        canonical = json.dumps(entry_copy, sort_keys=True)
        computed = hashlib.sha256((canonical + prev_hash).encode()).hexdigest()

        if computed != stored_hash:
            return False

        prev_hash = stored_hash

    return True
