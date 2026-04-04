import uuid
from datetime import datetime, timedelta, timezone
from aion.store import save_authority, get_authority, mark_consumed, revoke_authority
from aion.audit import log
import logging

logger = logging.getLogger(__name__)

TTL_SECONDS = 300

def issue(scope, parent=None, policy=None, issuer="root.system"):
    try:
        if not scope or not isinstance(scope, str):
            return {"error": "INVALID_SCOPE", "detail": "Scope must be non-empty string"}

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
        logger.info(f"Authority issued: {auth['jti']} scope: {scope}")
        return auth
    except Exception as e:
        logger.error(f"Issue failed: {str(e)}")
        return {"error": "ISSUE_FAILED", "detail": str(e)}

def verify(jti, scope):
    try:
        if not jti or not scope:
            return {"error": "INVALID_INPUT", "detail": "JTI and scope required"}

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
    except Exception as e:
        logger.error(f"Verify failed: {str(e)}")
        return {"error": "VERIFY_FAILED", "detail": str(e)}

def revoke(jti):
    try:
        if not jti:
            return {"error": "INVALID_INPUT", "detail": "JTI required"}
        auth = get_authority(jti)
        if not auth:
            return {"error": "NOT_FOUND", "detail": f"No authority found for JTI: {jti}"}
        revoke_authority(jti)
        log("REVOKE", {"jti": jti})
        logger.info(f"Authority revoked: {jti}")
        return {"status": "REVOKED", "jti": jti}
    except Exception as e:
        logger.error(f"Revoke failed: {str(e)}")
        return {"error": "REVOKE_FAILED", "detail": str(e)}