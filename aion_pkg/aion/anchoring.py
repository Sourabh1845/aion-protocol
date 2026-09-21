"""External anchoring for AION receipt chains.

A locally hash-chained payment history is tamper-EVIDENT, but the operator
still holds the store — a determined insider could rewrite the whole chain.
External anchoring closes that gap: periodically publish a compact chain
ROOT (the final chain hash + length) to a location the operator does not
control — a git commit, a gist, a cloud endpoint, a shared drive.

Later, anyone can independently confirm:
  - the chain was intact at anchor time  (root matched then)
  - nothing changed since anchor        (recompute + compare)
  - or exactly that it DID change       (MODIFIED_SINCE_ANCHOR — audit signal)

Records are JSONL so a git diff of the anchor file doubles as an
append-only, human-reviewable compliance ledger.
"""

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from aion.payment_storage import get_mandate, list_payment_auths
from aion.payments import _auth_chain_hash

ANCHOR_FILE = Path(
    os.getenv("AION_ANCHOR_FILE", ".aion/anchors/roots.jsonl")
)
_LOCK = threading.Lock()

GENESIS = "GENESIS"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, default=str)


def compute_mandate_root(mandate_id):
    """Recompute the payment chain and return its root (final chain hash)."""
    mandate = get_mandate(mandate_id)
    if not mandate:
        return {"error": "MANDATE_NOT_FOUND"}
    auths = list_payment_auths(mandate_id)
    prev = GENESIS
    for auth in auths:
        computed = _auth_chain_hash(auth, prev)
        if computed != auth.get("chain_hash"):
            return {
                "error": "CHAIN_BROKEN",
                "detail": f"chain hash mismatch at jti {auth.get('jti')}",
            }
        prev = auth.get("chain_hash")
    return {
        "mandate_id": mandate_id,
        "length": len(auths),
        "root": prev if auths else GENESIS,
        "chain_intact": True,
        "computed_at": _now(),
    }


def publish_root(mandate_id, anchor_file=None):
    """Append the current chain root to the anchor ledger (JSONL)."""
    if anchor_file is None:
        anchor_file = ANCHOR_FILE
    anchor_file = Path(anchor_file)

    root = compute_mandate_root(mandate_id)
    if "error" in root:
        return root

    record = {
        "record_type": "aion_mandate_chain_root",
        "mandate_id": mandate_id,
        "root": root["root"],
        "length": root["length"],
        "anchored_at": _now(),
    }
    record["anchor_hash"] = hashlib.sha256(
        _canonical(record).encode("utf-8")
    ).hexdigest()

    anchor_file.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        with anchor_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True, default=str) + "\n")
            f.flush()
            os.fsync(f.fileno())

    return {
        "status": "ANCHORED",
        "mandate_id": mandate_id,
        "root": record["root"],
        "length": record["length"],
        "anchor_hash": record["anchor_hash"],
        "anchor_file": str(anchor_file),
    }


def _latest_anchor(mandate_id, anchor_file):
    if not anchor_file.exists():
        return None
    latest = None
    with anchor_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue  # skip corrupt lines; earlier anchors stay readable
            if (record.get("mandate_id") == mandate_id
                    and record.get("record_type") == "aion_mandate_chain_root"):
                latest = record
    return latest


def verify_against_published_root(mandate_id, anchor_file=None):
    """Independently recompute the chain and compare with the published root."""
    if anchor_file is None:
        anchor_file = ANCHOR_FILE
    anchor_file = Path(anchor_file)

    anchor = _latest_anchor(mandate_id, anchor_file)
    if not anchor:
        return {
            "error": "NO_ANCHOR",
            "detail": f"no published root for {mandate_id} in {anchor_file}",
        }

    current = compute_mandate_root(mandate_id)

    if current.get("error") == "CHAIN_BROKEN":
        return {
            "status": "CHAIN_BROKEN",
            "mandate_id": mandate_id,
            "anchored_root": anchor["root"],
            "anchored_at": anchor["anchored_at"],
            "detail": current.get("detail"),
        }

    if (current["root"] == anchor["root"]
            and current["length"] == anchor["length"]):
        return {
            "status": "VERIFIED",
            "mandate_id": mandate_id,
            "root": anchor["root"],
            "length": anchor["length"],
            "anchored_at": anchor["anchored_at"],
            "detail": "current chain matches the externally published root",
        }

    return {
        "status": "MODIFIED_SINCE_ANCHOR",
        "mandate_id": mandate_id,
        "anchored_root": anchor["root"],
        "anchored_length": anchor["length"],
        "current_root": current["root"],
        "current_length": current["length"],
        "anchored_at": anchor["anchored_at"],
        "detail": "chain changed after the last published root — re-anchor or audit the delta",
    }


def list_anchors(anchor_file=None):
    """Return every published root, oldest first (the anchor ledger)."""
    if anchor_file is None:
        anchor_file = ANCHOR_FILE
    anchor_file = Path(anchor_file)
    if not anchor_file.exists():
        return []
    anchors = []
    with anchor_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("record_type") == "aion_mandate_chain_root":
                anchors.append(record)
    return anchors


__all__ = [
    "ANCHOR_FILE",
    "compute_mandate_root",
    "publish_root",
    "verify_against_published_root",
    "list_anchors",
]

