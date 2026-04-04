from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
import os
import secrets

API_KEY_NAME = "X-AION-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key():
    key = os.environ.get("AION_API_KEY")
    if not key:
        key = "aion-dev-key-local"
    return key

async def verify_api_key(api_key: str = Security(api_key_header)):
    expected_key = get_api_key()
    if not api_key or not secrets.compare_digest(api_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key