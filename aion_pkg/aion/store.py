import json
from pathlib import Path

STORE_FILE = Path(__file__).parent.parent / "storage" / "authority_store.json"

def _load():
    if STORE_FILE.exists():
        return json.loads(STORE_FILE.read_text())
    return {}

def _save(data):
    STORE_FILE.parent.mkdir(exist_ok=True)
    STORE_FILE.write_text(json.dumps(data, indent=2))

def save_authority(auth):
    data = _load()
    data[auth["jti"]] = auth
    _save(data)

def get_authority(jti):
    return _load().get(jti)

def mark_consumed(jti):
    data = _load()
    if jti in data:
        data[jti]["consumed"] = True
        _save(data)

def revoke_authority(jti):
    data = _load()
    if jti in data:
        data[jti]["revoked"] = True
        _save(data)