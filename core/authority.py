from datetime import datetime, timedelta, timezone
import uuid

CLOCK_SKEW_SECONDS = 30  # OPTION A LOCKED

def issue_authority(scope="default", ttl_seconds=300):
    now = datetime.now(timezone.utc)
    auth = {
        "jti": str(uuid.uuid4()),
        "scope": scope,
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
        "consumed": False,
        "revoked": False,
    }
    return auth


def verify_authority(auth):
    now = datetime.now(timezone.utc)

    issued_at = datetime.fromisoformat(auth["issued_at"])
    expires_at = datetime.fromisoformat(auth["expires_at"])

    if auth.get("revoked"):
        return {"error": "AUTH_REVOKED"}

    if auth.get("consumed"):
        return {"error": "AUTH_CONSUMED"}

    if issued_at - timedelta(seconds=CLOCK_SKEW_SECONDS) > now:
        return {"error": "CLOCK_SKEW_FUTURE"}

    if now > expires_at + timedelta(seconds=CLOCK_SKEW_SECONDS):
        return {"error": "AUTH_EXPIRED"}

    auth["consumed"] = True
    return {"status": "OK", "jti": auth["jti"], "scope": auth["scope"]}
