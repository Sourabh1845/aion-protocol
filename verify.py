import sys
from datetime import datetime, timezone

from storage.ledger import find_by_jti, mark_consumed


def verify(jti):
    record = find_by_jti(jti)

    if record is None:
        print("❌ VERIFY FAIL: Authority ID not found")
        sys.exit(1)

    if record.get("revoked") is True:
        print("❌ VERIFY FAIL: Authority revoked")
        sys.exit(1)

    expires_at = datetime.fromisoformat(record["expires_at"])
    if expires_at < datetime.now(timezone.utc):
        print("❌ VERIFY FAIL: Authority expired")
        sys.exit(1)

    try:
        mark_consumed(jti)
    except RuntimeError as e:
        print(f"❌ VERIFY FAIL: {e}")
        sys.exit(1)

    print("✅ Authority verified & consumed")
    print(record)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python verify.py <JTI>")
        sys.exit(1)

    verify(sys.argv[1])
