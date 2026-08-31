import sqlite3
import json
from pathlib import Path

DB_FILE = Path(__file__).parent.parent / "storage" / "aion.db"


def get_conn():
    DB_FILE.parent.mkdir(exist_ok=True)
    return sqlite3.connect(str(DB_FILE), timeout=30)


def _init_payments():
    db_file = DB_FILE
    db_file.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(db_file))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mandates (
            mandate_id TEXT PRIMARY KEY,
            principal TEXT,
            agent TEXT,
            scope TEXT,
            currency TEXT,
            max_per_payment INTEGER,
            max_total INTEGER,
            payees TEXT,
            issued_at TEXT,
            expires_at TEXT,
            spent INTEGER DEFAULT 0,
            payments_count INTEGER DEFAULT 0,
            revoked INTEGER DEFAULT 0,
            signature TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS payment_auths (
            jti TEXT PRIMARY KEY,
            mandate_id TEXT,
            agent TEXT,
            amount INTEGER,
            payee TEXT,
            currency TEXT,
            binding_hash TEXT,
            issued_at TEXT,
            expires_at TEXT,
            status TEXT DEFAULT 'AUTHORIZED',
            settlement_ref TEXT,
            settled_at TEXT,
            signature TEXT,
            chain_hash TEXT
        )
    """)
    conn.commit()
    conn.close()


# ---- MANDATES ----

def save_mandate(mandate):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO mandates VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        mandate["mandate_id"], mandate["principal"], mandate["agent"],
        mandate["scope"], mandate["currency"],
        mandate["max_per_payment"], mandate["max_total"],
        json.dumps(mandate.get("payees") or []),
        mandate["issued_at"], mandate["expires_at"],
        mandate.get("spent", 0), mandate.get("payments_count", 0),
        int(mandate.get("revoked", False)), mandate.get("signature"),
    ))
    conn.commit()
    conn.close()


def get_mandate(mandate_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM mandates WHERE mandate_id=?", (mandate_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "mandate_id": row[0], "principal": row[1], "agent": row[2],
        "scope": row[3], "currency": row[4],
        "max_per_payment": row[5], "max_total": row[6],
        "payees": json.loads(row[7]),
        "issued_at": row[8], "expires_at": row[9],
        "spent": row[10], "payments_count": row[11],
        "revoked": bool(row[12]), "signature": row[13],
    }


def set_mandate_revoked(mandate_id):
    conn = get_conn()
    conn.execute(
        "UPDATE mandates SET revoked=1 WHERE mandate_id=?", (mandate_id,)
    )
    conn.commit()
    conn.close()


def increment_mandate_spend(mandate_id, amount):
    """Atomic budget guard: increments only if within max_total and not revoked.

    Returns the fresh mandate row on success, None when the guard rejected it
    (race-safe — the WHERE clause re-checks the budget inside the UPDATE).
    """
    conn = get_conn()
    cur = conn.execute("""
        UPDATE mandates
        SET spent = spent + ?, payments_count = payments_count + 1
        WHERE mandate_id = ? AND revoked = 0 AND spent + ? <= max_total
    """, (amount, mandate_id, amount))
    conn.commit()
    row = None
    if cur.rowcount == 1:
        row = conn.execute(
            "SELECT * FROM mandates WHERE mandate_id=?", (mandate_id,)
        ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "mandate_id": row[0], "principal": row[1], "agent": row[2],
        "scope": row[3], "currency": row[4],
        "max_per_payment": row[5], "max_total": row[6],
        "payees": json.loads(row[7]),
        "issued_at": row[8], "expires_at": row[9],
        "spent": row[10], "payments_count": row[11],
        "revoked": bool(row[12]), "signature": row[13],
    }


# ---- PAYMENT AUTHS ----

def save_payment_auth(auth):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO payment_auths VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        auth["jti"], auth["mandate_id"], auth["agent"],
        auth["amount"], auth["payee"], auth["currency"],
        auth["binding_hash"], auth["issued_at"], auth["expires_at"],
        auth.get("status", "AUTHORIZED"),
        auth.get("settlement_ref"), auth.get("settled_at"),
        auth.get("signature"), auth.get("chain_hash"),
    ))
    conn.commit()
    conn.close()


def get_payment_auth(jti):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM payment_auths WHERE jti=?", (jti,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "jti": row[0], "mandate_id": row[1], "agent": row[2],
        "amount": row[3], "payee": row[4], "currency": row[5],
        "binding_hash": row[6], "issued_at": row[7], "expires_at": row[8],
        "status": row[9], "settlement_ref": row[10], "settled_at": row[11],
        "signature": row[12], "chain_hash": row[13],
    }


def update_payment_auth(jti, fields):
    conn = get_conn()
    for key, value in fields.items():
        conn.execute(
            f"UPDATE payment_auths SET {key}=? WHERE jti=?", (value, jti)
        )
    conn.commit()
    conn.close()


def list_payment_auths(mandate_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM payment_auths WHERE mandate_id=?
        ORDER BY issued_at ASC, jti ASC
    """, (mandate_id,)).fetchall()
    conn.close()
    auths = []
    for row in rows:
        auths.append({
            "jti": row[0], "mandate_id": row[1], "agent": row[2],
            "amount": row[3], "payee": row[4], "currency": row[5],
            "binding_hash": row[6], "issued_at": row[7], "expires_at": row[8],
            "status": row[9], "settlement_ref": row[10], "settled_at": row[11],
            "signature": row[12], "chain_hash": row[13],
        })
    return auths


_init_payments()