import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

AUDIT_FILE = Path(__file__).parent.parent / "storage" / "audit_log.json"

def _hash_record(record):
    payload = json.dumps(record, sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()

def log(event_type, payload):
    AUDIT_FILE.parent.mkdir(exist_ok=True)

    if AUDIT_FILE.exists():
        data = json.loads(AUDIT_FILE.read_text())
    else:
        data = []

    prev_hash = data[-1]["hash"] if data else "GENESIS"

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        "payload": payload,
        "prev_hash": prev_hash,
    }
    record["hash"] = _hash_record(record)
    data.append(record)
    AUDIT_FILE.write_text(json.dumps(data, indent=2))