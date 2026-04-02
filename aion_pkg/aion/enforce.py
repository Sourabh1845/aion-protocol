from aion.authority import verify
from aion.audit import log

def enforce(jti, scope):
    result = verify(jti, scope)

    if "error" in result:
        log("ENFORCE_DENY", result)
        return {"error": "ENFORCEMENT_DENIED", "reason": result}

    log("ENFORCE_ALLOW", result)
    return {"status": "ENFORCED", "jti": jti, "scope": scope}