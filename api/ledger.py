import json
import os

STORE = "authority_store.json"


def load_ledger():
    if not os.path.exists(STORE):
        return []
    with open(STORE, "r") as f:
        return json.load(f)


def save_ledger(entries):
    with open(STORE, "w") as f:
        json.dump(entries, f, indent=2)


def append_entry(entry):
    ledger = load_ledger()
    ledger.append(entry)
    save_ledger(ledger)


def find_by_jti(jti):
    ledger = load_ledger()
    for entry in ledger:
        if entry["jti"] == jti:
            return entry
    return None
