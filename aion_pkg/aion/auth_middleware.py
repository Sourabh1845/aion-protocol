from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
import os
import secrets

API_KEY_NAME = "X-AION-API-Key"
DEV_KEY = "aion-dev-key-local"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key():
    """Resolve the expected API key, failing closed when unconfigured.

    `AION_API_KEY` is required. The local development key is only used when
    `AION_ALLOW_DEV_KEY=1` is explicitly set - it is public knowledge (it lives
    in this repo), so it must never be an implicit fallback on a real server.
    """
    key = os.environ.get("AION_API_KEY")
    if key:
        return key
    if os.environ.get("AION_ALLOW_DEV_KEY") == "1":
        return DEV_KEY
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Server misconfigured: AION_API_KEY is not set",
    )

async def verify_api_key(api_key: str = Security(api_key_header)):
    expected_key = get_api_key()
    if not api_key or not secrets.compare_digest(api_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key