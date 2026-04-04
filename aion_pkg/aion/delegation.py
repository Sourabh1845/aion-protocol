import uuid
from datetime import datetime, timezone, timedelta
from aion.storage import insert_authority, get_authority
from aion.audit import log

TTL_SECONDS = 300

def delegate(parent_jti: str, new_scope: str, delegated_by: str):
    parent = get_authority(parent_jti)

    if not parent:
        return {"error": "PARENT_NOT_FOUND"}

    if parent["consumed"]:
        return {"error": "PARENT_CONSUMED"}

    if parent["revoked"]:
        return {"error": "PARENT_REVOKED"}

    if datetime.fromisoformat(parent["expires_at"]) < datetime.now(timezone.utc):
        return {"error": "PARENT_EXPIRED"}

    # Strict scope check — child scope must exactly match or be narrower
    parent_scope = parent["scope"]
    
    if new_scope != parent_scope and not new_scope.startswith(parent_scope + "."):
        return {"error": f"SCOPE_VIOLATION — cannot delegate '{new_scope}' from '{parent_scope}'"}

    now = datetime.now(timezone.utc)
    delegated_auth = {
        "jti": str(uuid.uuid4()),
        "issuer": delegated_by,
        "scope": new_scope,
        "parent": parent_jti,
        "policy": {},
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=TTL_SECONDS)).isoformat(),
        "consumed": False,
        "revoked": False,
    }

    insert_authority(delegated_auth)
    log("DELEGATE", delegated_auth)
    return delegated_auth