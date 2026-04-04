import sqlite3
from pathlib import Path
from datetime import datetime

DB_FILE = Path(__file__).parent.parent / "storage" / "aion.db"

def get_conn():
    DB_FILE.parent.mkdir(exist_ok=True)
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS authorities (
            jti TEXT PRIMARY KEY,
            issuer TEXT,
            scope TEXT,
            parent TEXT,
            policy TEXT,
            issued_at TEXT,
            expires_at TEXT,
            consumed INTEGER DEFAULT 0,
            revoked INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event TEXT,
            jti TEXT,
            scope TEXT,
            timestamp TEXT,
            prev_hash TEXT,
            hash TEXT
        )
    """)
    conn.commit()
    conn.close()

def insert_authority(auth):
    import json
    conn = get_conn()
    conn.execute("""
        INSERT INTO authorities VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        auth["jti"], auth["issuer"], auth["scope"],
        auth.get("parent"), json.dumps(auth.get("policy", {})),
        auth["issued_at"], auth["expires_at"],
        int(auth["consumed"]), int(auth["revoked"])
    ))
    conn.commit()
    conn.close()

def get_authority(jti):
    import json
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM authorities WHERE jti=?", (jti,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "jti": row[0], "issuer": row[1], "scope": row[2],
        "parent": row[3], "policy": json.loads(row[4]),
        "issued_at": row[5], "expires_at": row[6],
        "consumed": bool(row[7]), "revoked": bool(row[8])
    }

def mark_consumed(jti):
    conn = get_conn()
    conn.execute(
        "UPDATE authorities SET consumed=1 WHERE jti=?", (jti,)
    )
    conn.commit()
    conn.close()

def revoke_authority(jti):
    conn = get_conn()
    conn.execute(
        "UPDATE authorities SET revoked=1 WHERE jti=?", (jti,)
    )
    conn.commit()
    conn.close()

init_db()