import json
import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_FILE = Path(__file__).parent.parent / "storage" / "aion.db"

def _hash_record(record):
    payload = json.dumps(record, sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()

def log(event_type, payload):
    try:
        conn = sqlite3.connect(str(DB_FILE))
        cursor = conn.execute(
            "SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        prev_hash = row[0] if row else "GENESIS"

        timestamp = datetime.now(timezone.utc).isoformat()
        
        record = {
            "timestamp": timestamp,
            "event": event_type,
            "payload": str(payload),
            "prev_hash": prev_hash,
        }
        record["hash"] = _hash_record(record)

        conn.execute("""
            INSERT INTO audit_log (event, jti, scope, timestamp, prev_hash, hash)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            event_type,
            payload.get("jti", "") if isinstance(payload, dict) else "",
            payload.get("scope", "") if isinstance(payload, dict) else "",
            timestamp,
            prev_hash,
            record["hash"]
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Audit log error: {e}")