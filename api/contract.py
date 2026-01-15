from core.authority import (
    issue_authority,
    verify_authority,
    revoke_authority,
)


def issue(scope="issue", ttl=600):
    return issue_authority(scope=scope, ttl_seconds=ttl)


def verify(jti, scope=None):
    return verify_authority(jti, scope=scope)


def revoke(jti):
    revoke_authority(jti)
    return {"status": "REVOKED", "jti": jti}
