from fastapi import FastAPI, Depends, Request
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from aion.auth_middleware import verify_api_key
from aion.async_storage import (
    async_get_authority,
    async_insert_authority,
    async_mark_consumed,
    async_revoke_authority
)
from aion.audit import log
from aion.lock import acquire_lock, release_lock
import uuid
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="AION Protocol",
    version="2.0.0",
    description="Immutable Authority Infrastructure for Autonomous AI Agents"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

TTL_SECONDS = 300

class IssueRequest(BaseModel):
    scope: str
    issuer: str = "root.system"

class EnforceRequest(BaseModel):
    jti: str
    scope: str

@app.post("/issue")
@limiter.limit("30/minute")
async def issue_authority(request: Request, req: IssueRequest, api_key: str = Depends(verify_api_key)):
    try:
        if not req.scope:
            return {"error": "INVALID_SCOPE"}
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
        await async_insert_authority(auth)
        log("ISSUE", auth)
        return auth
    except Exception as e:
        logger.error(f"Issue failed: {str(e)}")
        return {"error": "ISSUE_FAILED", "detail": str(e)}

@app.post("/enforce")
@limiter.limit("60/minute")
async def enforce_authority(request: Request, req: EnforceRequest, api_key: str = Depends(verify_api_key)):
    try:
        if not acquire_lock(req.jti):
            return {"error": "ENFORCEMENT_DENIED", "reason": "TOKEN_LOCKED"}

        auth = await async_get_authority(req.jti)
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
        if datetime.fromisoformat(auth["expires_at"]) < datetime.now(timezone.utc):
            release_lock(req.jti)
            return {"error": "ENFORCEMENT_DENIED", "reason": "EXPIRED"}

        await async_mark_consumed(req.jti)
        release_lock(req.jti)
        log("ENFORCE_ALLOW", {"jti": req.jti, "scope": req.scope})
        return {"status": "ENFORCED", "jti": req.jti, "scope": req.scope}
    except Exception as e:
        release_lock(req.jti)
        logger.error(f"Enforce failed: {str(e)}")
        return {"error": "ENFORCE_FAILED", "detail": str(e)}

@app.get("/verify/{jti}")
@limiter.limit("60/minute")
async def verify_authority(request: Request, jti: str, scope: str, api_key: str = Depends(verify_api_key)):
    try:
        auth = await async_get_authority(jti)
        if not auth:
            return {"error": "NOT_FOUND"}
        if auth["revoked"]:
            return {"error": "REVOKED"}
        if auth["consumed"]:
            return {"error": "CONSUMED"}
        if auth["scope"] != scope:
            return {"error": "SCOPE_MISMATCH"}
        if datetime.fromisoformat(auth["expires_at"]) < datetime.now(timezone.utc):
            return {"error": "EXPIRED"}
        return {"status": "VALID", "jti": jti, "scope": scope}
    except Exception as e:
        return {"error": "VERIFY_FAILED", "detail": str(e)}

@app.post("/revoke/{jti}")
@limiter.limit("30/minute")
async def revoke_authority(request: Request, jti: str, api_key: str = Depends(verify_api_key)):
    try:
        auth = await async_get_authority(jti)
        if not auth:
            return {"error": "NOT_FOUND"}
        await async_revoke_authority(jti)
        log("REVOKE", {"jti": jti})
        return {"status": "REVOKED", "jti": jti}
    except Exception as e:
        return {"error": "REVOKE_FAILED", "detail": str(e)}

@app.get("/health")
async def health():
    return {"status": "AION is running", "version": "2.0.0"}