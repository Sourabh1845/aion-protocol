import json
import os
import time

AUDIT_FILE = "storage/audit_log.json"


def _load():
    if not os.path.exists(AUDIT_FILE):
        return []
    with open(AUDIT_FILE, "r") as f:
        return json.load(f)


def _save(data):
    with open(AUDIT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def log_event(event_type, payload):
    data = _load()
    data.append({
        "event": event_type,
        "timestamp": int(time.time()),
        "payload": payload,
    })
    _save(data)
