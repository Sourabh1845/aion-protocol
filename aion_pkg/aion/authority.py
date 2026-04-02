import uuid
from datetime import datetime, timedelta, timezone
from aion.store import save_authority, get_authority, mark_consumed, revoke_authority
from aion.audit import log

TTL_SECONDS = 300

def issue(scope, parent=None, policy=None, issuer="root.system"):
    now = datetime.now(timezone.utc)
    auth = {
        "jti": str(uuid.uuid4()),
        "issuer": issuer,
        "scope": scope,
        "parent": parent,
        "policy": policy or {},
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=TTL_SECONDS)).isoformat(),
        "consumed": False,
        "revoked": False,
    }
    save_authority(auth)
    log("ISSUE", auth)
    return auth

def verify(jti, scope):
    auth = get_authority(jti)

    if not auth:
        return {"error": "NOT_FOUND"}
    if auth["revoked"]:
        log("VERIFY_FAIL", {"jti": jti, "reason": "REVOKED"})
        return {"error": "REVOKED"}
    if auth["consumed"]:
        log("VERIFY_FAIL", {"jti": jti, "reason": "CONSUMED"})
        return {"error": "CONSUMED"}
    if auth["scope"] != scope:
        log("VERIFY_FAIL", {"jti": jti, "reason": "SCOPE_MISMATCH"})
        return {"error": "SCOPE_MISMATCH"}
    if datetime.fromisoformat(auth["expires_at"]) < datetime.now(timezone.utc):
        log("VERIFY_FAIL", {"jti": jti, "reason": "EXPIRED"})
        return {"error": "EXPIRED"}

    mark_consumed(jti)
    log("VERIFY_OK", {"jti": jti, "scope": scope})
    return {"status": "OK", "jti": jti, "scope": scope}

def revoke(jti):
    revoke_authority(jti)
    log("REVOKE", {"jti": jti})
    return {"status": "REVOKED", "jti": jti}