import psycopg2
from psycopg2 import pool
import json
import os
from datetime import datetime, timezone
from contextlib import contextmanager

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": 5432,
    "database": "aion_db",
    "user": "postgres",
    "password": os.environ.get("DB_PASSWORD", "SRS")
}

connection_pool = pool.ThreadedConnectionPool(
    minconn=5,
    maxconn=20,
    **DB_CONFIG
)

@contextmanager
def get_conn():
    conn = connection_pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        connection_pool.putconn(conn)

def init_pg_db():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS authorities (
                jti TEXT PRIMARY KEY,
                issuer TEXT,
                scope TEXT,
                parent TEXT,
                policy JSONB,
                issued_at TIMESTAMPTZ,
                expires_at TIMESTAMPTZ,
                consumed BOOLEAN DEFAULT FALSE,
                revoked BOOLEAN DEFAULT FALSE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id SERIAL PRIMARY KEY,
                event TEXT,
                jti TEXT,
                scope TEXT,
                timestamp TIMESTAMPTZ,
                prev_hash TEXT,
                hash TEXT
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_authorities_jti 
            ON authorities(jti)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp 
            ON audit_log(timestamp)
        """)
        print("PostgreSQL DB initialized successfully")

def pg_insert_authority(auth):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO authorities 
            (jti, issuer, scope, parent, policy, issued_at, expires_at, consumed, revoked)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (jti) DO NOTHING
        """, (
            auth["jti"], auth["issuer"], auth["scope"],
            auth.get("parent"), json.dumps(auth.get("policy", {})),
            auth["issued_at"], auth["expires_at"],
            auth["consumed"], auth["revoked"]
        ))

def pg_get_authority(jti):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM authorities WHERE jti=%s", (jti,)
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "jti": row[0], "issuer": row[1], "scope": row[2],
        "parent": row[3], "policy": row[4],
        "issued_at": str(row[5]), "expires_at": str(row[6]),
        "consumed": row[7], "revoked": row[8]
    }

def pg_mark_consumed(jti):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE authorities SET consumed=TRUE WHERE jti=%s", (jti,)
        )

def pg_revoke_authority(jti):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE authorities SET revoked=TRUE WHERE jti=%s", (jti,)
        )

init_pg_db()