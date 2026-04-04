import uuid
from datetime import datetime, timezone, timedelta
from aion.storage import insert_authority, get_authority
from aion.audit import log

TTL_SECONDS = 300
MAX_DELEGATION_DEPTH = 3

def get_delegation_depth(jti: str) -> int:
    depth = 0
    current_jti = jti
    visited = set()
    while True:
        if current_jti in visited:
            break
        visited.add(current_jti)
        auth = get_authority(current_jti)
        if not auth or not auth.get("parent"):
            break
        depth += 1
        current_jti = auth["parent"]
    return depth

def delegate(parent_jti: str, new_scope: str, delegated_by: str):
    try:
        parent = get_authority(parent_jti)

        if not parent:
            return {"error": "PARENT_NOT_FOUND"}
        if parent["consumed"]:
            return {"error": "PARENT_CONSUMED"}
        if parent["revoked"]:
            return {"error": "PARENT_REVOKED"}
        if datetime.fromisoformat(parent["expires_at"]) < datetime.now(timezone.utc):
            return {"error": "PARENT_EXPIRED"}

        # Max depth check — count from parent
        depth = get_delegation_depth(parent_jti)
        if depth >= MAX_DELEGATION_DEPTH - 1:
            return {"error": f"MAX_DEPTH_EXCEEDED — max {MAX_DELEGATION_DEPTH} levels allowed"}

        # Strict scope check
        parent_scope = parent["scope"]
        if new_scope != parent_scope and not new_scope.startswith(parent_scope + "."):
            return {"error": f"SCOPE_VIOLATION — cannot delegate '{new_scope}' from '{parent_scope}'"}

        now = datetime.now(timezone.utc)
        parent_expiry = datetime.fromisoformat(parent["expires_at"])
        child_expiry = min(now + timedelta(seconds=TTL_SECONDS), parent_expiry)

        delegated_auth = {
            "jti": str(uuid.uuid4()),
            "issuer": delegated_by,
            "scope": new_scope,
            "parent": parent_jti,
            "policy": {},
            "issued_at": now.isoformat(),
            "expires_at": child_expiry.isoformat(),
            "consumed": False,
            "revoked": False,
        }

        insert_authority(delegated_auth)
        log("DELEGATE", delegated_auth)
        return delegated_auth

    except Exception as e:
        return {"error": "DELEGATION_FAILED", "detail": str(e)}