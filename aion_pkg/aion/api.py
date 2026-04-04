from fastapi import FastAPI
from pydantic import BaseModel
from aion.authority import issue, verify, revoke
from aion.enforce import enforce

app = FastAPI(title="AION Protocol", version="2.0.0")

class IssueRequest(BaseModel):
    scope: str
    issuer: str = "root.system"

class EnforceRequest(BaseModel):
    jti: str
    scope: str

@app.post("/issue")
def issue_authority(req: IssueRequest):
    return issue(req.scope, issuer=req.issuer)

@app.post("/enforce")
def enforce_authority(req: EnforceRequest):
    return enforce(req.jti, req.scope)

@app.get("/verify/{jti}")
def verify_authority(jti: str, scope: str):
    return verify(jti, scope)

@app.post("/revoke/{jti}")
def revoke_authority(jti: str):
    return revoke(jti)

@app.get("/health")
def health():
    return {"status": "AION is running"}