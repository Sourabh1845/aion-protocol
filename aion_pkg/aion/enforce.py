from aion.authority import verify
from aion.audit import log
import logging

logger = logging.getLogger(__name__)

def enforce(jti, scope):
    try:
        if not jti or not scope:
            return {"error": "INVALID_INPUT", "detail": "JTI and scope required"}

        result = verify(jti, scope)

        if "error" in result:
            log("ENFORCE_DENY", result)
            logger.warning(f"Enforcement denied: {jti} — {result['error']}")
            return {"error": "ENFORCEMENT_DENIED", "reason": result}

        log("ENFORCE_ALLOW", result)
        logger.info(f"Enforcement allowed: {jti} scope: {scope}")
        return {"status": "ENFORCED", "jti": jti, "scope": scope}

    except Exception as e:
        logger.error(f"Enforce failed: {str(e)}")
        return {"error": "ENFORCE_FAILED", "detail": str(e)}