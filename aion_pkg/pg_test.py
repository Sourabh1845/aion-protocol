from aion.pg_storage import (
    pg_insert_authority,
    pg_get_authority,
    pg_mark_consumed,
    pg_revoke_authority
)
import uuid
from datetime import datetime, timezone, timedelta

print("=" * 60)
print("AION PostgreSQL Storage Test")
print("=" * 60)

# Test 1 — Insert authority
print("\nTest 1: Insert authority...")
now = datetime.now(timezone.utc)
auth = {
    "jti": str(uuid.uuid4()),
    "issuer": "root.system",
    "scope": "ops.read",
    "parent": None,
    "policy": {},
    "issued_at": now.isoformat(),
    "expires_at": (now + timedelta(seconds=300)).isoformat(),
    "consumed": False,
    "revoked": False,
}
pg_insert_authority(auth)
print(f"Inserted: {auth['jti']}")

# Test 2 — Get authority
print("\nTest 2: Get authority...")
fetched = pg_get_authority(auth["jti"])
assert fetched is not None
assert fetched["scope"] == "ops.read"
print(f"Fetched: {fetched['jti']} scope={fetched['scope']}")

# Test 3 — Mark consumed
print("\nTest 3: Mark consumed...")
pg_mark_consumed(auth["jti"])
fetched2 = pg_get_authority(auth["jti"])
assert fetched2["consumed"] == True
print(f"Consumed: {fetched2['consumed']}")

# Test 4 — Revoke
print("\nTest 4: Revoke authority...")
auth2 = {
    "jti": str(uuid.uuid4()),
    "issuer": "root.system",
    "scope": "ops.write",
    "parent": None,
    "policy": {},
    "issued_at": now.isoformat(),
    "expires_at": (now + timedelta(seconds=300)).isoformat(),
    "consumed": False,
    "revoked": False,
}
pg_insert_authority(auth2)
pg_revoke_authority(auth2["jti"])
fetched3 = pg_get_authority(auth2["jti"])
assert fetched3["revoked"] == True
print(f"Revoked: {fetched3['revoked']}")

print("\n" + "=" * 60)
print("ALL PostgreSQL TESTS PASSED")
print("=" * 60)