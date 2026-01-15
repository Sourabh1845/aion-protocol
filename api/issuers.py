import json
from pathlib import Path

ISSUER_FILE = Path("storage/issuers.json")

def _load():
    if not ISSUER_FILE.exists():
        return {}
    return json.loads(ISSUER_FILE.read_text())

def _save(data):
    ISSUER_FILE.parent.mkdir(parents=True, exist_ok=True)
    ISSUER_FILE.write_text(json.dumps(data, indent=2))

def ensure_issuer(name):
    data = _load()
    if name not in data:
        data[name] = {"revoked": False}
        _save(data)

def revoke_issuer(name):
    data = _load()
    if name in data:
        data[name]["revoked"] = True
        _save(data)

def is_active(name):
    data = _load()
    return name in data and not data[name]["revoked"]
