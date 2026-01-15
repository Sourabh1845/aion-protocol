import sys
from storage.ledger import mark_revoked


def revoke(jti):
    try:
        mark_revoked(jti)
        print(f"🚫 Authority revoked: {jti}")
    except RuntimeError as e:
        print(f"❌ REVOKE FAIL: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python revoke.py <JTI>")
        sys.exit(1)

    revoke(sys.argv[1])
