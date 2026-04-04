import sqlite3
import time
from pathlib import Path

DB_FILE = Path(__file__).parent.parent / "storage" / "aion.db"

def _get_conn():
    return sqlite3.connect(str(DB_FILE))

def init_lock_table():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS token_locks (
            jti TEXT PRIMARY KEY,
            locked_at REAL,
            expires_at REAL
        )
    """)
    conn.commit()
    conn.close()

def acquire_lock(jti: str, ttl_seconds: float = 5.0) -> bool:
    conn = _get_conn()
    now = time.time()
    expires = now + ttl_seconds
    try:
        # Clean expired locks first
        conn.execute(
            "DELETE FROM token_locks WHERE expires_at < ?", (now,)
        )
        # Try to insert lock
        conn.execute(
            "INSERT INTO token_locks (jti, locked_at, expires_at) VALUES (?, ?, ?)",
            (jti, now, expires)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def release_lock(jti: str):
    conn = _get_conn()
    conn.execute("DELETE FROM token_locks WHERE jti=?", (jti,))
    conn.commit()
    conn.close()

init_lock_table()