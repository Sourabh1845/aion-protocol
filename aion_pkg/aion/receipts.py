import hashlib
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

RECEIPT_DIR = Path(os.getenv("AION_RECEIPT_DIR", ".aion")) / "receipts"
_LOCK = threading.Lock()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _hash_payload(payload):
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _safe_metadata(metadata):
    if metadata is None:
        return {}

    if isinstance(metadata, dict):
        redacted = {}
        for key, value in metadata.items():
            lower_key = str(key).lower()
            if any(word in lower_key for word in ("secret", "token", "password", "api_key", "apikey", "private")):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = value
        return redacted

    return {"value": str(metadata)}


def create_receipt(
    scope,
    decision,
    risk,
    reason,
    status,
    agent="unknown-agent",
    metadata=None,
):
    receipt = {
        "receipt_id": str(uuid.uuid4()),
        "timestamp": _now(),
        "agent": agent,
        "scope": scope,
        "decision": decision,
        "risk": risk,
        "reason": reason,
        "status": status,
        "metadata": _safe_metadata(metadata),
    }
    receipt["receipt_hash"] = _hash_payload(receipt)
    return receipt


def save_receipt(receipt):
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    path = RECEIPT_DIR / f"{receipt['receipt_id']}.json"

    with _LOCK:
        with path.open("w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2, sort_keys=True, default=str)

    return str(path)


def record_receipt(
    scope,
    decision,
    risk,
    reason,
    status,
    agent="unknown-agent",
    metadata=None,
    async_write=True,
):
    receipt = create_receipt(
        scope=scope,
        decision=decision,
        risk=risk,
        reason=reason,
        status=status,
        agent=agent,
        metadata=metadata,
    )

    if async_write:
        thread = threading.Thread(target=save_receipt, args=(receipt,), daemon=True)
        thread.start()
    else:
        save_receipt(receipt)

    return receipt
