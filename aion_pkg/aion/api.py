from fastapi import FastAPI, Depends
from pydantic import BaseModel
from aion.authority import issue, verify, revoke
from aion.enforce import enforce
from aion.auth_middleware import verify_api_key
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AION Protocol",
    version="2.0.0",
    description="Immutable Authority Infrastructure for Autonomous AI Agents"
)

class IssueRequest(BaseModel):
    scope: str
    issuer: str = "root.system"

class EnforceRequest(BaseModel):
    jti: str
    scope: str

@app.post("/issue")
def issue_authority(req: IssueRequest, api_key: str = Depends(verify_api_key)):
    return issue(req.scope, issuer=req.issuer)

@app.post("/enforce")
def enforce_authority(req: EnforceRequest, api_key: str = Depends(verify_api_key)):
    return enforce(req.jti, req.scope)

@app.get("/verify/{jti}")
def verify_authority(jti: str, scope: str, api_key: str = Depends(verify_api_key)):
    return verify(jti, scope)

@app.post("/revoke/{jti}")
def revoke_authority(jti: str, api_key: str = Depends(verify_api_key)):
    return revoke(jti)

@app.get("/health")
def health():
    return {"status": "AION is running", "version": "2.0.0"}