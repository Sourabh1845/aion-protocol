import aiosqlite
import json
from pathlib import Path
from datetime import datetime, timezone
import sqlite3

DB_FILE = Path(__file__).parent.parent / "storage" / "aion.db"

def _init():
    DB_FILE.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_FILE))
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
    conn.commit()
    conn.close()

_init()

async def async_get_authority(jti):
    async with aiosqlite.connect(str(DB_FILE)) as db:
        async with db.execute(
            "SELECT * FROM authorities WHERE jti=?", (jti,)
        ) as cursor:
            row = await cursor.fetchone()
    if not row:
        return None
    return {
        "jti": row[0], "issuer": row[1], "scope": row[2],
        "parent": row[3], "policy": json.loads(row[4]),
        "issued_at": row[5], "expires_at": row[6],
        "consumed": bool(row[7]), "revoked": bool(row[8])
    }

async def async_insert_authority(auth):
    async with aiosqlite.connect(str(DB_FILE)) as db:
        await db.execute("""
            INSERT OR REPLACE INTO authorities 
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            auth["jti"], auth["issuer"], auth["scope"],
            auth.get("parent"), json.dumps(auth.get("policy", {})),
            auth["issued_at"], auth["expires_at"],
            int(auth["consumed"]), int(auth["revoked"])
        ))
        await db.commit()

async def async_mark_consumed(jti):
    async with aiosqlite.connect(str(DB_FILE)) as db:
        await db.execute(
            "UPDATE authorities SET consumed=1 WHERE jti=?", (jti,)
        )
        await db.commit()

async def async_revoke_authority(jti):
    async with aiosqlite.connect(str(DB_FILE)) as db:
        await db.execute(
            "UPDATE authorities SET revoked=1 WHERE jti=?", (jti,)
        )
        await db.commit()