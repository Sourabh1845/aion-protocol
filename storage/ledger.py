import json
from pathlib import Path

LEDGER_PATH = Path("storage/authority_ledger.json")


def _load():
    if not LEDGER_PATH.exists():
        return []
    with open(LEDGER_PATH, "r") as f:
        return json.load(f)


def _save(data):
    with open(LEDGER_PATH, "w") as f:
        json.dump(data, f, indent=2)


def append_entry(entry):
    data = _load()
    data.append(entry)
    _save(data)


def find_by_jti(jti):
    for entry in _load():
        if entry["jti"] == jti:
            return entry
    return None


def mark_consumed(jti):
    data = _load()
    for entry in data:
        if entry["jti"] == jti:
            entry["consumed"] = True
            _save(data)
            return
    raise RuntimeError("AUTH_NOT_FOUND")


def mark_revoked(jti):
    data = _load()
    for entry in data:
        if entry["jti"] == jti:
            entry["revoked"] = True
            _save(data)
            return
    raise RuntimeError("AUTH_NOT_FOUND")
