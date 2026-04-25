from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from aion.auth_middleware import verify_api_key
from aion.pg_storage import (
    pg_get_authority,
    pg_insert_authority,
    pg_mark_consumed,
    pg_revoke_authority
)
from aion.audit import log
from aion.redis_lock import acquire_redis_lock as acquire_lock, release_redis_lock as release_lock
from aion.token_signing import sign_token, verify_token_signature
import uuid
import logging
import re
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="AION Protocol",
    version="3.0.0",
    description="Immutable Authority Infrastructure for Autonomous AI Agents"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

TTL_SECONDS = 300
SCOPE_REGEX = re.compile(r'^[a-zA-Z0-9._\-]+$')
MAX_SCOPE_LENGTH = 100
MAX_ISSUER_LENGTH = 100

class IssueRequest(BaseModel):
    scope: str
    issuer: str = "root.system"

class EnforceRequest(BaseModel):
    jti: str
    scope: str

def validate_scope(scope: str):
    if not scope or len(scope.strip()) == 0:
        return {"error": "INVALID_SCOPE", "detail": "Scope cannot be empty"}
    if len(scope) > MAX_SCOPE_LENGTH:
        return {"error": "INVALID_SCOPE", "detail": f"Scope too long — max {MAX_SCOPE_LENGTH} characters"}
    if not SCOPE_REGEX.match(scope):
        return {"error": "INVALID_SCOPE", "detail": "Scope contains invalid characters — only alphanumeric, dots, dashes, underscores allowed"}
    return None

def validate_issuer(issuer: str):
    if len(issuer) > MAX_ISSUER_LENGTH:
        return {"error": "INVALID_ISSUER", "detail": f"Issuer too long — max {MAX_ISSUER_LENGTH} characters"}
    return None

@app.post("/issue")
@limiter.limit("30/minute")
def issue_authority(request: Request, req: IssueRequest, api_key: str = Depends(verify_api_key)):
    try:
        scope_error = validate_scope(req.scope)
        if scope_error:
            return scope_error

        issuer_error = validate_issuer(req.issuer)
        if issuer_error:
            return issuer_error

        now = datetime.now(timezone.utc)
        auth = {
            "jti": str(uuid.uuid4()),
            "issuer": req.issuer,
            "scope": req.scope,
            "parent": None,
            "policy": {},
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=TTL_SECONDS)).isoformat(),
            "consumed": False,
            "revoked": False,
        }
        auth["signature"] = sign_token(auth)
        pg_insert_authority(auth)
        log("ISSUE", auth)
        return auth
    except Exception as e:
        logger.error(f"Issue failed: {str(e)}")
        return {"error": "ISSUE_FAILED", "detail": str(e)}

@app.post("/enforce")
@limiter.limit("60/minute")
def enforce_authority(request: Request, req: EnforceRequest, api_key: str = Depends(verify_api_key)):
    try:
        if not acquire_lock(req.jti):
            return {"error": "ENFORCEMENT_DENIED", "reason": "TOKEN_LOCKED"}

        auth = pg_get_authority(req.jti)
        if not auth:
            release_lock(req.jti)
            return {"error": "NOT_FOUND"}
        if auth["revoked"]:
            release_lock(req.jti)
            return {"error": "ENFORCEMENT_DENIED", "reason": "REVOKED"}
        if auth["consumed"]:
            release_lock(req.jti)
            return {"error": "ENFORCEMENT_DENIED", "reason": "CONSUMED"}
        if auth["scope"] != req.scope:
            release_lock(req.jti)
            return {"error": "ENFORCEMENT_DENIED", "reason": "SCOPE_MISMATCH"}
        if datetime.fromisoformat(str(auth["expires_at"])) < datetime.now(timezone.utc):
            release_lock(req.jti)
            return {"error": "ENFORCEMENT_DENIED", "reason": "EXPIRED"}

        signature = auth.get("signature")
        if signature and not verify_token_signature(auth, signature):
            release_lock(req.jti)
            return {"error": "ENFORCEMENT_DENIED", "reason": "INVALID_SIGNATURE"}

        pg_mark_consumed(req.jti)
        release_lock(req.jti)
        log("ENFORCE_ALLOW", {"jti": req.jti, "scope": req.scope})
        return {"status": "ENFORCED", "jti": req.jti, "scope": req.scope}
    except Exception as e:
        release_lock(req.jti)
        logger.error(f"Enforce failed: {str(e)}")
        return {"error": "ENFORCE_FAILED", "detail": str(e)}

@app.get("/verify/{jti}")
@limiter.limit("60/minute")
def verify_authority(request: Request, jti: str, scope: str, api_key: str = Depends(verify_api_key)):
    try:
        auth = pg_get_authority(jti)
        if not auth:
            return {"error": "NOT_FOUND"}
        if auth["revoked"]:
            return {"error": "REVOKED"}
        if auth["consumed"]:
            return {"error": "CONSUMED"}
        if auth["scope"] != scope:
            return {"error": "SCOPE_MISMATCH"}
        if datetime.fromisoformat(str(auth["expires_at"])) < datetime.now(timezone.utc):
            return {"error": "EXPIRED"}
        signature = auth.get("signature")
        if signature and not verify_token_signature(auth, signature):
            return {"error": "INVALID_SIGNATURE"}
        return {"status": "VALID", "jti": jti, "scope": scope}
    except Exception as e:
        return {"error": "VERIFY_FAILED", "detail": str(e)}

@app.post("/revoke/{jti}")
@limiter.limit("30/minute")
def revoke_authority(request: Request, jti: str, api_key: str = Depends(verify_api_key)):
    try:
        auth = pg_get_authority(jti)
        if not auth:
            return {"error": "NOT_FOUND"}
        pg_revoke_authority(jti)
        log("REVOKE", {"jti": jti})
        return {"status": "REVOKED", "jti": jti}
    except Exception as e:
        return {"error": "REVOKE_FAILED", "detail": str(e)}

@app.get("/health")
def health():
    return {"status": "AION is running", "version": "3.0.0"}